import contextlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from binarybitops import server as server_module
from binarybitops.server import DemoConfig, build_state, create_server
from binarybitops.version import BuildInfo

BUILD = BuildInfo(
    version="0.1.0-test",
    git_sha="1ab7ca0",
    build_date="2026-11-17T00:00:00Z",
    image_ref="registry.example/binarybitops-demo:test",
)


@contextlib.contextmanager
def running_server(app):
    server = create_server(config=app.config, app=app, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.config = DemoConfig(
            environment="test",
            release="wbs-3.10",
            secret_path=str(Path(cls.tempdir.name) / "demo.json"),
        )
        cls.app = build_state(cls.config, BUILD)
        cls.server = create_server(config=cls.config, app=cls.app, host="127.0.0.1", port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tempdir.cleanup()

    def request(self, method, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            body = response.read()
            return response.status, dict(response.getheaders()), body
        finally:
            connection.close()

    def test_healthz(self):
        status, headers, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")

    def test_security_headers(self):
        _, headers, _ = self.request("GET", "/")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("Python", headers.get("Server", ""))

    def test_head_has_headers_but_no_body(self):
        status, headers, body = self.request("HEAD", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertGreater(int(headers["Content-Length"]), 0)

    def test_readyz(self):
        status, _, body = self.request("GET", "/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ready")

    def test_index_states_scope_and_renders_example(self):
        status, headers, body = self.request("GET", "/")
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("DEMONSTRATOR ONLY", text)
        self.assertIn("not the Binary Bit Ops/Nexus application", text)
        self.assertIn("0000 0000 0000 1100", text)
        self.assertIn("1ab7ca0", text)

    def test_index_calculates_supplied_values(self):
        status, _, body = self.request("GET", "/?left=255&right=15")
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn(">15<", text)   # AND
        self.assertIn(">255<", text)  # OR
        self.assertIn(">240<", text)  # XOR

    def test_index_escapes_invalid_input(self):
        status, _, body = self.request("GET", "/?left=%3Cscript%3Ealert(1)%3C/script%3E&right=1")
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("Invalid input", text)

    def test_bitops_api(self):
        status, _, body = self.request("GET", "/api/bitops?left=12&right=10")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual((payload["and"], payload["or"], payload["xor"]), (8, 14, 6))

    def test_bitops_api_rejects_bad_and_missing_input(self):
        for path in ("/api/bitops?left=70000&right=1", "/api/bitops?left=x&right=1", "/api/bitops?left=1"):
            with self.subTest(path=path):
                status, _, body = self.request("GET", path)
                self.assertEqual(status, 400)
                self.assertIn("error", json.loads(body))

    def test_status_api(self):
        status, _, body = self.request("GET", "/api/status")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["service"], "binarybitops-demo")
        self.assertFalse(payload["vault"]["injected"])
        self.assertIn("not the Binary Bit Ops/Nexus application", payload["scope"])
        self.assertEqual(payload["build"]["git_sha"], "1ab7ca0")
        wbs_ids = {control["wbs"] for control in payload["controls"]}
        self.assertTrue({"3.3", "3.6", "3.8", "3.9"}.issubset(wbs_ids))

    def test_version_api(self):
        status, _, body = self.request("GET", "/version")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["image_ref"], "registry.example/binarybitops-demo:test")

    def test_metrics_exposition(self):
        self.request("GET", "/api/bitops?left=1&right=2")
        status, headers, body = self.request("GET", "/metrics")
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/plain"))
        self.assertIn("binarybitops_build_info{", text)
        self.assertIn('git_sha="1ab7ca0"', text)
        self.assertIn("binarybitops_http_requests_total{", text)
        self.assertIn('route="/api/bitops"', text)
        self.assertIn("binarybitops_vault_secret_injected 0", text)

    def test_unknown_route(self):
        status, _, body = self.request("GET", "/no-such-page")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["error"], "not_found")

    def test_write_methods_are_rejected(self):
        status, headers, _ = self.request("POST", "/api/bitops")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET, HEAD")

    def test_overlong_uri_is_rejected(self):
        status, _, _ = self.request("GET", "/" + "a" * 3000)
        self.assertEqual(status, 414)

    def test_secret_value_never_appears_in_responses(self):
        sentinel = "response-sentinel-4f8c1d"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.json"
            path.write_text(json.dumps({"demo-api-key": sentinel}), encoding="utf-8")
            config = DemoConfig(secret_path=str(path), require_secret=True)
            app = build_state(config, BUILD)
            with running_server(app) as port:
                for route in ("/", "/api/status", "/metrics", "/version", "/healthz", "/readyz"):
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                    connection.request("GET", route)
                    response = connection.getresponse()
                    body = response.read().decode("utf-8")
                    connection.close()
                    self.assertNotIn(sentinel, body, route)
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                connection.request("GET", "/api/status")
                payload = json.loads(connection.getresponse().read())
                connection.close()
                self.assertTrue(payload["vault"]["injected"])

    def test_required_secret_controls_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            config = DemoConfig(secret_path=str(Path(directory) / "absent.json"), require_secret=True)
            app = build_state(config, BUILD)
            self.assertFalse(app.ready)
            with running_server(app) as port:
                for route, expected in (("/healthz", 200), ("/readyz", 503)):
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                    connection.request("GET", route)
                    self.assertEqual(connection.getresponse().status, expected)
                    connection.close()

    def test_main_binds_the_configured_host(self):
        captured = {}

        def fake_create(config=None, app=None, build=None, host="127.0.0.1", port=None):
            captured["host"] = host
            return mock.MagicMock()

        with mock.patch.object(server_module, "create_server", fake_create), \
                mock.patch.object(server_module, "_serve", lambda srv: None):
            self.assertEqual(server_module.main({"HOST": "0.0.0.0", "DEMO_ENV": "test"}), 0)
        self.assertEqual(captured["host"], "0.0.0.0")

    def test_main_defaults_to_all_interfaces(self):
        captured = {}

        def fake_create(config=None, app=None, build=None, host="127.0.0.1", port=None):
            captured["host"] = host
            return mock.MagicMock()

        with mock.patch.object(server_module, "create_server", fake_create), \
                mock.patch.object(server_module, "_serve", lambda srv: None):
            self.assertEqual(server_module.main({"DEMO_ENV": "test"}), 0)
        self.assertEqual(captured["host"], "0.0.0.0")


if __name__ == "__main__":
    unittest.main()
