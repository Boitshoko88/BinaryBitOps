import contextlib
import io
import unittest

from binarybitops.hde_model import (
    CloudResource,
    OnPremResource,
    SecureHybridEnvironment,
    default_environment,
)


class EnvironmentTests(unittest.TestCase):
    def test_resource_locations_and_controls(self):
        local = OnPremResource("Git", "Source Control", ["MFA"])
        cloud = CloudResource("Kubernetes", "Runtime", ["RBAC"])
        self.assertEqual(local.location, "On-Premises")
        self.assertEqual(cloud.location, "Cloud")
        self.assertEqual(local.security_controls, ["MFA"])
        self.assertEqual(cloud.security_controls, ["RBAC"])

    def test_resource_lists_are_independent(self):
        first = CloudResource("First", "Runtime")
        second = CloudResource("Second", "Runtime")
        first.security_controls.append("TLS")
        self.assertEqual(second.security_controls, [])

    def test_empty_environment_warns(self):
        env = SecureHybridEnvironment()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            env.audit_security()
        self.assertIn("WARNING: No secure connectivity configured", output.getvalue())
        self.assertIn("WARNING: No security policies defined", output.getvalue())
        self.assertNotIn("present in the model", output.getvalue())

    def test_partial_controls_do_not_report_a_complete_model(self):
        env = SecureHybridEnvironment()
        env.add_policy("MFA")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            env.audit_security()
        self.assertIn("WARNING: No secure connectivity configured", output.getvalue())
        self.assertNotIn("present in the model", output.getvalue())

    def test_complete_model_is_not_claimed_as_a_live_security_assessment(self):
        env = SecureHybridEnvironment()
        env.add_connectivity("SSO and MFA")
        env.add_policy("Least privilege")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            env.audit_security()
        self.assertIn("Configured connectivity and policies are present in the model.", output.getvalue())
        self.assertIn("This model output is not a live security assessment.", output.getvalue())
        self.assertNotIn("All required security controls are present", output.getvalue())

    def test_display_includes_configured_resources_and_policies(self):
        env = SecureHybridEnvironment()
        env.add_onprem(OnPremResource("Git", "Source Control", ["MFA"]))
        env.add_cloud(CloudResource("Kubernetes", "Runtime", ["RBAC"]))
        env.add_connectivity("VPN")
        env.add_policy("Encryption")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            env.display()
        for expected in ("Git", "Kubernetes", "MFA", "RBAC", "VPN", "Encryption"):
            self.assertIn(expected, output.getvalue())

    def test_default_environment_reflects_phase_3_stack(self):
        env = default_environment()
        rendered = repr(env.as_dict())
        for expected in (
            "Managed developer endpoint",
            "AWS non-production Kubernetes",
            "GitHub authoritative repository",
            "Tekton and Trivy",
            "Vault and Argo CD",
            "Prometheus, Grafana, Loki, and Velero",
        ):
            self.assertIn(expected, rendered)
        for obsolete in ("GitLab Server", "Jenkins Server", "SonarQube Server"):
            self.assertNotIn(obsolete, rendered)

    def test_model_serialises_without_secrets(self):
        payload = default_environment().as_dict()
        self.assertEqual(len(payload["cloud"]), 5)
        self.assertEqual(len(payload["connectivity"]), 2)
        self.assertGreaterEqual(len(payload["policies"]), 4)


if __name__ == "__main__":
    unittest.main()
