import json
import tempfile
import unittest
from pathlib import Path

from binarybitops.secrets import SecretStatus, inspect_secret_file, require_secret_from_env, secret_path_from_env


class SecretStatusTests(unittest.TestCase):
    def test_missing_secret_is_not_injected(self):
        with tempfile.TemporaryDirectory() as directory:
            status = inspect_secret_file(Path(directory) / "absent.json")
        self.assertFalse(status.injected)
        self.assertEqual(status.keys, ())
        self.assertEqual(status.source, "vault-agent-injected")

    def test_not_configured_is_reported(self):
        self.assertFalse(inspect_secret_file(None).injected)
        self.assertEqual(inspect_secret_file("").source, "not-configured")

    def test_secret_value_is_never_returned(self):
        sentinel = "sentinel-value-must-not-escape-9f2a"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.json"
            path.write_text(json.dumps({"demo-api-key": sentinel, "rotation_epoch": 4}), encoding="utf-8")
            status = inspect_secret_file(path)

        self.assertTrue(status.injected)
        self.assertEqual(status.keys, ("demo-api-key", "rotation_epoch"))
        for representation in (repr(status), str(status), json.dumps(status.as_dict())):
            self.assertNotIn(sentinel, representation)

    def test_plain_file_reports_filename_only(self):
        sentinel = "another-secret-value-1c7b"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo-api-key"
            path.write_text(sentinel, encoding="utf-8")
            status = inspect_secret_file(path)
        self.assertTrue(status.injected)
        self.assertEqual(status.keys, ("demo-api-key",))
        self.assertNotIn(sentinel, json.dumps(status.as_dict()))

    def test_invalid_json_is_flagged_without_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.json"
            path.write_text("not-json", encoding="utf-8")
            status = inspect_secret_file(path)
        self.assertTrue(status.injected)
        self.assertEqual(status.keys, ("invalid-secret-document",))

    def test_key_names_are_bounded_and_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.json"
            path.write_text(json.dumps({f"key-{index:02d}": "value" for index in range(30)}), encoding="utf-8")
            status = inspect_secret_file(path)
        self.assertEqual(len(status.keys), 10)
        self.assertEqual(list(status.keys), sorted(status.keys))

    def test_environment_defaults(self):
        self.assertEqual(secret_path_from_env({}), "/vault/secrets/demo.json")
        self.assertFalse(require_secret_from_env({}))
        self.assertTrue(require_secret_from_env({"REQUIRE_VAULT_INJECTION": "TRUE"}))

    def test_constructed_status_has_no_value_field(self):
        status = SecretStatus(injected=True, source="vault-agent-injected", keys=("demo-api-key",))
        self.assertEqual(set(status.as_dict()), {"injected", "source", "keys"})


if __name__ == "__main__":
    unittest.main()
