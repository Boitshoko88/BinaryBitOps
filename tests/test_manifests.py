"""Security and structure assertions over the delivery manifests.

These tests are intentionally strict: they fail if a future change removes a
delivery gate, weakens the pod security context, commits a credential-shaped
string, or lets Argo CD deploy automatically without approval.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "evidence", "__pycache__", ".venv"}
# Partial Deployment documents used as kustomize patches, not standalone objects.
PATCH_FILES = {"patch-image.yaml", "patch-vault.yaml", "patch-pull-secret.yaml", "external-secret.yaml"}


def yaml_paths() -> list[Path]:
    paths = []
    for pattern in ("*.yaml", "*.yml"):
        paths.extend(ROOT.rglob(pattern))
    return sorted(
        path for path in paths
        if not any(part in SKIP_PARTS for part in path.parts)
    )


def load_documents(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [document for document in yaml.safe_load_all(handle) if document]


def all_documents() -> list[tuple[Path, dict]]:
    documents: list[tuple[Path, dict]] = []
    for path in yaml_paths():
        for document in load_documents(path):
            documents.append((path, document))
    return documents


ALL_DOCUMENTS = all_documents()
DOCUMENTS = [
    (path, document) for path, document in ALL_DOCUMENTS
    if path.name not in PATCH_FILES
]


def find(kind: str, name: str | None = None) -> list[tuple[Path, dict]]:
    matches = [(path, document) for path, document in DOCUMENTS if document.get("kind") == kind]
    if name is not None:
        matches = [
            (path, document) for path, document in matches
            if document.get("metadata", {}).get("name") == name
        ]
    return matches


def one(kind: str, name: str | None = None) -> dict:
    matches = find(kind, name)
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one {kind}/{name}, found {len(matches)}")
    return matches[0][1]


class YamlStructureTests(unittest.TestCase):
    def test_all_delivery_yaml_parses(self):
        self.assertGreater(len(ALL_DOCUMENTS), 15)
        for path, document in ALL_DOCUMENTS:
            self.assertIsInstance(document, dict, path)

    def test_expected_workloads_exist(self):
        for kind, name in (
            ("Namespace", "binarybitops-demo"),
            ("Deployment", "binarybitops-demo"),
            ("Service", "binarybitops-demo"),
            ("PodDisruptionBudget", "binarybitops-demo"),
            ("ServiceAccount", "binarybitops-demo"),
            ("Application", "binarybitops-demo"),
            ("AppProject", "binarybitops-demo"),
            ("Pipeline", "binarybitops-demo-delivery"),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(len(find(kind, name)), 1)


class NamespaceAndNetworkTests(unittest.TestCase):
    def test_namespace_enforces_restricted_pod_security(self):
        labels = one("Namespace", "binarybitops-demo")["metadata"]["labels"]
        for key in ("enforce", "audit", "warn"):
            self.assertEqual(labels[f"pod-security.kubernetes.io/{key}"], "restricted")

    def test_default_deny_network_policy(self):
        policies = [document for _, document in find("NetworkPolicy")]
        deny = [
            policy for policy in policies
            if policy["spec"].get("podSelector") == {}
            and {"Ingress", "Egress"}.issubset(set(policy["spec"].get("policyTypes", [])))
        ]
        self.assertTrue(deny, "a default-deny NetworkPolicy is required")

    def test_ingress_is_limited_to_named_namespaces_and_port(self):
        policies = [document for _, document in find("NetworkPolicy")]
        allow = next(
            policy for policy in policies
            if policy["metadata"]["name"] == "binarybitops-demo-allow"
        )
        ingress = allow["spec"]["ingress"]
        self.assertEqual(len(ingress), 1)
        ports = ingress[0]["ports"]
        self.assertEqual(ports, [{"protocol": "TCP", "port": 8080}])
        for source in ingress[0]["from"]:
            self.assertIn("namespaceSelector", source)

    def test_egress_is_dns_only(self):
        allow = one("NetworkPolicy", "binarybitops-demo-allow")
        egress = allow["spec"]["egress"]
        self.assertEqual(len(egress), 1)
        ports = {(port["protocol"], port["port"]) for port in egress[0]["ports"]}
        self.assertEqual(ports, {("UDP", 53), ("TCP", 53)})

    def test_workload_has_no_host_access(self):
        spec = one("Deployment", "binarybitops-demo")["spec"]["template"]["spec"]
        self.assertNotIn("hostNetwork", spec)
        self.assertNotIn("hostPID", spec)
        self.assertNotIn("hostIPC", spec)
        for volume in spec.get("volumes", []):
            self.assertNotIn("hostPath", volume)

    def test_pdb_protects_availability(self):
        self.assertGreaterEqual(one("PodDisruptionBudget", "binarybitops-demo")["spec"]["minAvailable"], 1)


class DeploymentSecurityTests(unittest.TestCase):
    def setUp(self):
        self.deployment = one("Deployment", "binarybitops-demo")
        self.pod_spec = self.deployment["spec"]["template"]["spec"]
        self.container = self.pod_spec["containers"][0]

    def test_two_replicas_and_rolling_update(self):
        self.assertGreaterEqual(self.deployment["spec"]["replicas"], 2)
        strategy = self.deployment["spec"]["strategy"]
        self.assertEqual(strategy["rollingUpdate"]["maxUnavailable"], 0)

    def test_pod_level_security_context(self):
        context = self.pod_spec["securityContext"]
        self.assertTrue(context["runAsNonRoot"])
        self.assertEqual(context["runAsUser"], 10001)
        self.assertEqual(context["seccompProfile"]["type"], "RuntimeDefault")

    def test_container_security_context(self):
        context = self.container["securityContext"]
        self.assertFalse(context["allowPrivilegeEscalation"])
        self.assertTrue(context["readOnlyRootFilesystem"])
        self.assertFalse(context["privileged"])
        self.assertEqual(context["capabilities"]["drop"], ["ALL"])
        self.assertEqual(context["runAsUser"], 10001)

    def test_service_account_token_is_not_mounted(self):
        self.assertFalse(self.pod_spec["automountServiceAccountToken"])
        self.assertFalse(one("ServiceAccount", "binarybitops-demo")["automountServiceAccountToken"])

    def test_probes_resources_and_limits(self):
        for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
            self.assertIn(probe, self.container)
            self.assertEqual(self.container[probe]["httpGet"]["port"], "http")
        resources = self.container["resources"]
        for section in ("requests", "limits"):
            self.assertIn("cpu", resources[section])
            self.assertIn("memory", resources[section])
        self.assertIn("ephemeral-storage", resources["limits"])

    def test_image_is_not_latest(self):
        image = self.container["image"]
        self.assertNotRegex(image, r":latest$")

    def test_read_only_root_filesystem_has_tmp_mount(self):
        mounts = {mount["mountPath"] for mount in self.container.get("volumeMounts", [])}
        self.assertIn("/tmp", mounts)

    def test_environment_comes_from_configmap(self):
        self.assertEqual(
            self.container["envFrom"],
            [{"configMapRef": {"name": "binarybitops-demo-config"}}],
        )


class DeliveryGateTests(unittest.TestCase):
    def test_argocd_sync_is_manual(self):
        application = one("Application", "binarybitops-demo")
        automated = application["spec"].get("syncPolicy", {}).get("automated")
        self.assertIsNone(automated, "automated sync bypasses the deployment approval")

    def test_argocd_is_scoped_to_one_namespace(self):
        application = one("Application", "binarybitops-demo")
        self.assertEqual(application["spec"]["destination"]["namespace"], "binarybitops-demo")
        project = one("AppProject", "binarybitops-demo")
        destinations = project["spec"]["destinations"]
        self.assertEqual([entry["namespace"] for entry in destinations], ["binarybitops-demo"])
        self.assertEqual(project["spec"]["sourceRepos"], [
            "https://github.com/Boitshoko88/BinaryBitOps.git",
            "https://github.com/Hybrid-Envionment-Project/binarybit-ops.git",
        ])

    def test_pipeline_orders_tests_scans_and_publish(self):
        pipeline = one("Pipeline", "binarybitops-demo-delivery")
        tasks = {task["name"]: task for task in pipeline["spec"]["tasks"]}
        self.assertEqual(tasks["unit-tests"]["runAfter"], ["fetch-source"])
        self.assertEqual(tasks["trivy-source"]["runAfter"], ["unit-tests"])
        self.assertEqual(tasks["build-image"]["runAfter"], ["trivy-source"])
        self.assertEqual(tasks["scan-image"]["runAfter"], ["build-image"])
        self.assertEqual(tasks["publish-image"]["runAfter"], ["scan-image"])
        self.assertEqual(tasks["pin-gitops"]["runAfter"], ["publish-image"])
        self.assertEqual(tasks["pin-gitops"]["when"][0]["values"], ["true"])

    def test_trivy_gates_fail_on_high_or_critical(self):
        for name in ("demo-trivy-source", "demo-scan-image"):
            task = one("Task", name)
            script = "\n".join(step.get("script", "") for step in task["spec"]["steps"])
            self.assertIn("--exit-code 1", script, name)
            self.assertIn("HIGH,CRITICAL", script, name)

    def test_publish_records_an_immutable_digest(self):
        task = one("Task", "demo-publish-image")
        names = [result["name"] for result in task["spec"]["results"]]
        self.assertIn("digest", names)
        script = "\n".join(step.get("script", "") for step in task["spec"]["steps"])
        self.assertIn("crane digest", script)
        self.assertIn("sha256:", script)

    def test_gitops_task_refuses_tag_only_input(self):
        task = one("Task", "demo-pin-gitops")
        script = "\n".join(step.get("script", "") for step in task["spec"]["steps"])
        self.assertIn("refusing non-digest reference", script)
        self.assertIn("git -C repo push origin", script)
        self.assertNotIn("push origin main", script)
        self.assertNotIn("git merge", script)

    def test_overlay_pins_registry_image(self):
        path = ROOT / "deploy/overlays/nonprod/patch-image.yaml"
        document = load_documents(path)[0]
        image = document["spec"]["template"]["spec"]["containers"][0]["image"]
        self.assertIn("445137568300.dkr.ecr.eu-north-1.amazonaws.com/binarybitops-demo", image)
        self.assertNotRegex(image, r":latest$")
        digest_match = re.search(r"@sha256:([0-9a-f]{64})$", image)
        if "@sha256:" in image:
            self.assertIsNotNone(digest_match, "digest must be a full sha256")

    def test_vault_policy_is_read_only_and_path_scoped(self):
        policy = (ROOT / "vault/policy.hcl").read_text(encoding="utf-8")
        capabilities = re.findall(r'capabilities\s*=\s*\[(.*?)\]', policy)
        self.assertTrue(capabilities)
        for entry in capabilities:
            self.assertEqual(entry.replace('"', "").strip(), "read")
        self.assertIn('path "secret/data/hde/nonprod/binarybitops-demo"', policy)
        self.assertNotIn('path "secret/*"', policy)

    def test_service_monitor_targets_named_port(self):
        service = one("Service", "binarybitops-demo")
        monitor = one("ServiceMonitor", "binarybitops-demo")
        service_ports = {port["name"] for port in service["spec"]["ports"]}
        self.assertIn(monitor["spec"]["endpoints"][0]["port"], service_ports)


class ContainerAndSupplyChainTests(unittest.TestCase):
    def test_dockerfile_runs_as_fixed_non_root_user(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("USER 10001:10001", dockerfile)
        self.assertNotRegex(dockerfile, r"(?mi)^USER\s+root")
        self.assertNotRegex(dockerfile, r"(?mi)^FROM\s+\S+:latest")
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("--chown=10001:10001", dockerfile)

    def test_runtime_has_no_third_party_dependencies(self):
        self.assertFalse((ROOT / "requirements.txt").exists())
        self.assertFalse((ROOT / "pyproject.toml").exists())
        package_files = list((ROOT / "binarybitops").glob("*.py"))
        self.assertTrue(package_files)
        for path in package_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^import (requests|flask|django|sqlalchemy)\b")

    def test_pr_workflow_has_test_scan_and_container_jobs(self):
        workflow_path = ROOT / ".github/workflows/pr-check.yml"
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        jobs = workflow["jobs"]
        self.assertIn("tests-and-manifests", jobs)
        self.assertIn("container", jobs)
        serialised = str(workflow)
        self.assertIn("aquasecurity/trivy-action", serialised)
        self.assertIn("kubeconform", serialised)

    def test_no_credential_shaped_strings_in_delivery_paths(self):
        patterns = [
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----"),
            re.compile(r"ghp_[A-Za-z0-9]{20,}"),
            re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
            re.compile(r"(?i)(?:password|api[_-]?key|secret)\s*[:=]\s*['\"][A-Za-z0-9/+_-]{16,}['\"]"),
        ]
        scan_roots = ["binarybitops", "deploy", "ci", "argocd", "vault", "docs", "scripts"]
        files = [ROOT / "README.md", ROOT / "Dockerfile", ROOT / "binarybitops.py"]
        for directory in scan_roots:
            files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
        for path in files:
            if path.suffix in {".png", ".jpg", ".pyc"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                self.assertIsNone(pattern.search(text), f"possible secret in {path.relative_to(ROOT)}")

    def test_scope_boundary_is_documented(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        attestation = (ROOT / "docs/non-migration-attestation.md").read_text(encoding="utf-8")
        for text in (readme, attestation):
            self.assertIn("Truehost", text)
            self.assertIn("Nexus", text)
        self.assertIn("does **not** authorise", readme)
        self.assertIn("remains the live PHP/MySQL application", attestation)


if __name__ == "__main__":
    unittest.main()
