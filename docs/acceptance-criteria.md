# Acceptance criteria â€” WBS 3.10 demonstrator

Each criterion is testable. "Local" means the check can be run in this
repository; "HDE" means it requires the project cluster, registry, Vault or
GitHub and must be recorded from those systems.

| ID | Criterion | Verification | Evidence |
| --- | --- | --- | --- |
| AC-01 | The demonstrator is a separate workload and contains no Nexus/Truehost code, data, credentials or connection | Review `binarybitops/`; `git grep -i nexus`; attestation signed | Source review, attestation |
| AC-02 | Valid operands return correct 16-bit AND/OR/XOR results | `python -m unittest tests.test_bitops -v` | Test output |
| AC-03 | Invalid, missing and out-of-range operands are rejected without echoing input | `tests.test_bitops`, `tests.test_server` | Test output |
| AC-04 | The HTTP service answers liveness, readiness, version, status and metrics correctly | `tests.test_server`; container smoke test | Test output, curl output |
| AC-05 | Secret values are never returned, logged or serialised; only injection status and key names are exposed | `tests.test_secrets`, `tests.test_server`; Trivy secret scan | Test output, scan report |
| AC-06 | Readiness fails when a required Vault secret is absent | `tests.test_server` readiness case | Test output |
| AC-07 | The container runs as non-root with a read-only root filesystem, all capabilities dropped and seccomp RuntimeDefault | Manifest tests; `docker inspect`; cluster pod spec | Test output, `kubectl get pod -o jsonpath` |
| AC-08 | The namespace enforces the restricted Pod Security Standard and network traffic is default-deny | `tests.test_manifests`; `kubectl get ns ... -o yaml`; NetworkPolicy review | Test output, cluster output |
| AC-09 | The Tekton pipeline orders tests â†’ source scan â†’ build â†’ image scan â†’ publish, and fails on HIGH/CRITICAL | Manifest tests; successful and deliberately failing PipelineRun | Pipeline logs, Trivy reports |
| AC-10 | Only an immutable image digest is used for GitOps; tags are not deployed | Overlay shows `@sha256:`; Argo CD diff | GitOps PR, Argo CD revision |
| AC-11 | Deployment is from an approved GitOps revision and a manual Argo CD sync â€” no direct `kubectl apply` | Approved PR, Argo CD sync history, audit log | PR URL, Argo CD screenshot/JSON |
| AC-12 | The running workload reports the merged commit SHA and environment | `GET /version`, `GET /api/status` | Captured response |
| AC-13 | An independent reviewer approved the change and confirmed the scope boundary | PR approval record | PR URL |
| AC-14 | Observability receives workload metrics and logs | Prometheus target UP; Grafana query; Loki log line | Screenshots/queries |
| AC-15 | Owners reviewed the evidence and recorded a completion decision | Signed evidence record | `evidence/wbs-3.10-record.md` |

## Negative tests to evidence

1. **Scan gate:** a PipelineRun against a commit with a known HIGH finding must
   stop before publish (record the failed task and the finding ID).
2. **Secret gate:** a branch that adds a dummy credential pattern must fail the
   Trivy secret scan (use a synthetic, non-usable value; delete the branch after).
3. **Readiness:** with `REQUIRE_VAULT_INJECTION=true` and no injected file, the pod
   must stay `0/1 Ready` while `/healthz` remains healthy.
4. **NetworkPolicy:** a pod in an unapproved namespace cannot reach port 8080.
5. **Argo CD authority:** a manual `kubectl edit` of the Deployment is reverted
   by Argo CD at the next sync or shown as OutOfSync, proving Git is the source
   of truth.

## Out of scope

- Load, soak and disaster-recovery testing (owned by the Phase 3 performance and
  recovery work packages).
- Penetration testing of the ingress path (security testing work package).
- Any change to the Truehost Nexus application, database or DNS.
