"""A printable model of the Phase 3 Hybrid Development Environment.

This is a descriptive model, not a live security assessment. It documents the
delivery stack that Task 3.10 depends on and is rendered by the CLI and the
demonstrator web page.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Resource:
    name: str
    category: str
    location: str
    security_controls: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Subclasses may pass None explicitly; always store an owned list.
        if self.security_controls is None:
            self.security_controls = []

    def describe(self) -> None:
        print(f"- {self.name} ({self.category}) in {self.location}")
        if self.security_controls:
            print(f"  Security: {', '.join(self.security_controls)}")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "category": self.category,
            "location": self.location,
            "security_controls": list(self.security_controls),
        }


class OnPremResource(Resource):
    def __init__(self, name: str, category: str, security_controls: list[str] | None = None):
        super().__init__(name, category, location="On-Premises", security_controls=security_controls)


class CloudResource(Resource):
    def __init__(self, name: str, category: str, security_controls: list[str] | None = None):
        super().__init__(name, category, location="Cloud", security_controls=security_controls)


class SecureHybridEnvironment:
    """Collects the resources, connectivity and policies of the HDE model."""

    def __init__(self) -> None:
        self.onprem_resources: list[Resource] = []
        self.cloud_resources: list[Resource] = []
        self.connectivity: list[str] = []
        self.policies: list[str] = []

    def add_onprem(self, resource: Resource) -> None:
        self.onprem_resources.append(resource)

    def add_cloud(self, resource: Resource) -> None:
        self.cloud_resources.append(resource)

    def add_connectivity(self, description: str) -> None:
        self.connectivity.append(description)

    def add_policy(self, policy: str) -> None:
        self.policies.append(policy)

    def display(self) -> None:
        print("=== Secure Hybrid Development Environment ===")
        print("\nOn-Premises Resources:")
        for resource in self.onprem_resources:
            resource.describe()

        print("\nCloud Resources:")
        for resource in self.cloud_resources:
            resource.describe()

        print("\nSecure Connectivity:")
        for item in self.connectivity:
            print(f"- {item}")

        print("\nSecurity Policies and Controls:")
        for policy in self.policies:
            print(f"- {policy}")

    def audit_security(self) -> None:
        print("\n=== Security Audit Summary ===")
        if not self.connectivity:
            print("WARNING: No secure connectivity configured")
        if not self.policies:
            print("WARNING: No security policies defined")
        if self.connectivity and self.policies:
            print("Configured connectivity and policies are present in the model.")
            print("This model output is not a live security assessment.")

    def as_dict(self) -> dict[str, object]:
        return {
            "onprem": [resource.as_dict() for resource in self.onprem_resources],
            "cloud": [resource.as_dict() for resource in self.cloud_resources],
            "connectivity": list(self.connectivity),
            "policies": list(self.policies),
        }


def default_environment() -> SecureHybridEnvironment:
    """Return the Phase 3 HDE model shown by the CLI and the web page."""

    env = SecureHybridEnvironment()

    env.add_onprem(OnPremResource(
        name="Managed developer endpoint",
        category="Endpoint",
        security_controls=["Device posture checks", "Zero-Data-on-Laptops policy"],
    ))
    env.add_cloud(CloudResource(
        name="AWS non-production Kubernetes",
        category="Demonstrator runtime",
        security_controls=["Environment separation", "Least-privilege workload access"],
    ))
    env.add_cloud(CloudResource(
        name="GitHub authoritative repository",
        category="Source control",
        security_controls=["Protected branch", "Independent pull-request review"],
    ))
    env.add_cloud(CloudResource(
        name="Tekton and Trivy",
        category="Build, test, and scan",
        security_controls=["Test gate", "High and critical vulnerability gate"],
    ))
    env.add_cloud(CloudResource(
        name="Vault and Argo CD",
        category="Secrets and controlled delivery",
        security_controls=["Workload-scoped secret access", "Approved GitOps deployment"],
    ))
    env.add_cloud(CloudResource(
        name="Prometheus, Grafana, Loki, and Velero",
        category="Operations and recovery",
        security_controls=["Central observability", "Encrypted backup and restore"],
    ))

    env.add_connectivity("SSO, MFA, and role-based access control")
    env.add_connectivity("OpenZiti private access after device posture checks")

    env.add_policy("Protected branches and independent review before delivery")
    env.add_policy("Trivy scan gate before the image is published")
    env.add_policy("Secrets are retrieved from Vault and are not stored in source")
    env.add_policy("Audit logs, monitoring, encrypted backups, and tested recovery")

    return env
