"""HTTP workload for the Phase 3 Task 3.10 demonstrator.

Routes
------
``/``             HTML demonstrator page (bit calculator and delivery identity)
``/api/bitops``   JSON bitwise result for ``left`` and ``right`` query values
``/api/status``   Non-sensitive runtime, build and control-dependency status
``/healthz``      Liveness: process is serving requests
``/readyz``       Readiness: required configuration (including Vault) is present
``/metrics``      Prometheus text exposition
``/version``      Build identity

The service is read-only, has no database, no Nexus code and no write path.
"""

from __future__ import annotations

import html
import json
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from .bitops import BitOpsError, compute_from_strings
from .hde_model import default_environment
from .metrics import Metrics
from .secrets import SecretStatus, inspect_secret_file, require_secret_from_env, secret_path_from_env
from .version import BuildInfo, load_build_info

SERVICE_NAME = "binarybitops-demo"
SCOPE_STATEMENT = (
    "Demonstrator workload only. This is not the Binary Bit Ops/Nexus application, "
    "does not contain its code or data, and does not authorise a migration away "
    "from the existing Truehost PHP/MySQL deployment."
)
MAX_PATH_LENGTH = 2048
MAX_QUERY_FIELDS = 8


@dataclass(frozen=True)
class DemoConfig:
    environment: str = "nonprod"
    release: str = "wbs-3.10"
    host: str = "0.0.0.0"
    port: int = 8080
    secret_path: str = "/vault/secrets/demo.json"
    require_secret: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DemoConfig":
        source = os.environ if env is None else env
        try:
            port = int(source.get("PORT", "8080"))
        except ValueError:
            port = 8080
        return cls(
            environment=_safe_label(source.get("DEMO_ENV", "nonprod")),
            release=_safe_label(source.get("DEMO_RELEASE", "wbs-3.10")),
            host=source.get("HOST", "0.0.0.0"),
            port=port if 1 <= port <= 65535 else 8080,
            secret_path=secret_path_from_env(dict(source)),
            require_secret=require_secret_from_env(dict(source)),
        )


def _safe_label(value: str, fallback: str = "unknown") -> str:
    cleaned = value.strip()[:40]
    return cleaned if cleaned and all(char.isalnum() or char in "._-" for char in cleaned) else fallback


@dataclass
class AppState:
    config: DemoConfig
    build: BuildInfo
    secret: SecretStatus
    metrics: Metrics = field(default_factory=Metrics)
    ready: bool = True


CONTROL_DEPENDENCIES = (
    {"wbs": "3.2", "control": "AWS foundation and non-production Kubernetes", "owner": "Kagiso, Thoriso, Liya, Elvis"},
    {"wbs": "3.3", "control": "SSO, MFA, RBAC and access logging", "owner": "Elvis, Tshegofatso, Noxolo"},
    {"wbs": "3.4", "control": "MDM posture and Zero-Data-on-Laptops", "owner": "Sandra, Lerato, Tshegofatso"},
    {"wbs": "3.5", "control": "OpenZiti private access", "owner": "Lungile, Nqubeko, Noxolo"},
    {"wbs": "3.6", "control": "Protected GitHub repository and review", "owner": "Nkosinathi, Primrose, Kgotsho"},
    {"wbs": "3.8", "control": "Vault workload-scoped secrets", "owner": "Elvis, Mahlatse, Boikgantsho"},
    {"wbs": "3.9", "control": "Tekton, Trivy and Argo CD delivery", "owner": "Mahlatse, Boikgantsho, Tsumbo"},
)


class DemoRequestHandler(BaseHTTPRequestHandler):
    """Request handler bound to an :class:`AppState` through ``self.server.app``."""

    server_version = SERVICE_NAME
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ HTTP
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def do_POST(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    # -------------------------------------------------------------- internals
    @property
    def app(self) -> AppState:
        return self.server.app  # type: ignore[attr-defined]

    def _method_not_allowed(self) -> None:
        self._send(
            HTTPStatus.METHOD_NOT_ALLOWED,
            _json_bytes({"error": "method_not_allowed"}),
            "application/json; charset=utf-8",
            head_only=False,
            extra_headers={"Allow": "GET, HEAD"},
        )

    def _dispatch(self, method: str) -> None:
        started = time.perf_counter()
        route = "not_found"
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        head_only = method == "HEAD"

        try:
            if len(self.path) > MAX_PATH_LENGTH:
                status = HTTPStatus.REQUEST_URI_TOO_LONG
                self._send(status, _json_bytes({"error": "request_uri_too_long"}), "application/json; charset=utf-8", head_only)
                return

            parsed = urlsplit(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=MAX_QUERY_FIELDS)

            if path == "/":
                route = "/"
                status = self._index(query, head_only)
            elif path == "/api/bitops":
                route = "/api/bitops"
                status = self._bitops(query, head_only)
            elif path == "/api/status":
                route = "/api/status"
                status = self._status(head_only)
            elif path == "/healthz":
                route = "/healthz"
                status = self._json_ok({"status": "ok", "service": SERVICE_NAME}, head_only)
            elif path == "/readyz":
                route = "/readyz"
                if self.app.ready:
                    status = self._json_ok({"status": "ready", "service": SERVICE_NAME}, head_only)
                else:
                    status = self._json_error(HTTPStatus.SERVICE_UNAVAILABLE, "not_ready", head_only)
            elif path == "/metrics":
                route = "/metrics"
                body = self.app.metrics.render(self.app.build, self.app.secret.injected).encode("utf-8")
                self._send(HTTPStatus.OK, body, "text/plain; version=0.0.4; charset=utf-8", head_only)
                status = HTTPStatus.OK
            elif path == "/version":
                route = "/version"
                status = self._json_ok(self.app.build.as_dict(), head_only)
            else:
                status = self._json_error(HTTPStatus.NOT_FOUND, "not_found", head_only)
        except Exception as exc:  # pragma: no cover - defensive boundary
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            self._log_event("error", route, status, exc.__class__.__name__)
            try:
                self._json_error(status, "internal_error", head_only)
            except Exception:
                pass
        finally:
            duration = time.perf_counter() - started
            self.app.metrics.observe(method, route, int(status), duration)
            self._log_event("info", route, int(status), None, duration, method)

    def _index(self, query: dict[str, list[str]], head_only: bool) -> HTTPStatus:
        left = _first(query, "left", "12")
        right = _first(query, "right", "10")
        result = None
        error = None
        try:
            result = compute_from_strings(left, right)
        except BitOpsError as exc:
            error = str(exc)

        body = _render_index(self.app, left, right, result, error).encode("utf-8")
        self._send(HTTPStatus.OK, body, "text/html; charset=utf-8", head_only)
        return HTTPStatus.OK

    def _bitops(self, query: dict[str, list[str]], head_only: bool) -> HTTPStatus:
        left = _first(query, "left", None)
        right = _first(query, "right", None)
        if left is None or right is None:
            return self._json_error(HTTPStatus.BAD_REQUEST, "left_and_right_required", head_only)
        try:
            result = compute_from_strings(left, right)
        except BitOpsError as exc:
            return self._json_error(HTTPStatus.BAD_REQUEST, str(exc), head_only)
        return self._json_ok(result, head_only)

    def _status(self, head_only: bool) -> HTTPStatus:
        payload = {
            "service": SERVICE_NAME,
            "scope": SCOPE_STATEMENT,
            "environment": self.app.config.environment,
            "release": self.app.config.release,
            "build": self.app.build.as_dict(),
            "vault": self.app.secret.as_dict(),
            "ready": self.app.ready,
            "controls": [
                {**control, "evidence": "verified by the owning work package, not by this workload"}
                for control in CONTROL_DEPENDENCIES
            ],
            "endpoints": ["/", "/api/bitops", "/api/status", "/healthz", "/readyz", "/metrics", "/version"],
        }
        return self._json_ok(payload, head_only)

    def _json_ok(self, payload: dict[str, Any], head_only: bool) -> HTTPStatus:
        self._send(HTTPStatus.OK, _json_bytes(payload), "application/json; charset=utf-8", head_only)
        return HTTPStatus.OK

    def _json_error(self, status: HTTPStatus, message: str, head_only: bool) -> HTTPStatus:
        self._send(status, _json_bytes({"error": message}), "application/json; charset=utf-8", head_only)
        return status

    def _send(
        self,
        status: HTTPStatus,
        body: bytes,
        content_type: str,
        head_only: bool,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        )
        for header, value in (extra_headers or {}).items():
            self.send_header(header, value)
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _log_event(
        self,
        level: str,
        route: str,
        status: int,
        error: str | None = None,
        duration: float | None = None,
        method: str = "GET",
    ) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": level,
            "service": SERVICE_NAME,
            "method": method,
            "route": route,
            "status": status,
            "environment": self.app.config.environment,
        }
        if duration is not None:
            record["duration_ms"] = round(duration * 1000, 3)
        if error:
            record["error"] = error
        print(json.dumps(record, separators=(",", ":")), flush=True)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Silence the default stderr access log; structured JSON is emitted above.
        return


def _first(query: dict[str, list[str]], key: str, default: str | None) -> str | None:
    values = query.get(key)
    if not values:
        return default
    return values[0]


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _render_index(
    app: AppState,
    left: str,
    right: str,
    result: dict[str, Any] | None,
    error: str | None,
) -> str:
    build = app.build
    secret = app.secret
    model = default_environment()

    def escape(value: object) -> str:
        return html.escape(str(value), quote=True)

    if result:
        rows = "".join(
            f"<tr><th>{op.upper()}</th><td class=\"num\">{result[op]}</td>"
            f"<td class=\"bin\">{escape(result['binary'][op])}</td></tr>"
            for op in ("and", "or", "xor")
        )
        operand_row = (
            f"<tr><th>Left</th><td class=\"num\">{result['left']}</td>"
            f"<td class=\"bin\">{escape(result['binary']['left'])}</td></tr>"
            f"<tr><th>Right</th><td class=\"num\">{result['right']}</td>"
            f"<td class=\"bin\">{escape(result['binary']['right'])}</td></tr>"
        )
        result_block = (
            '<table><caption>16-bit result</caption>'
            f"<thead><tr><th>Value</th><th>Decimal</th><th>Binary</th></tr></thead>"
            f"<tbody>{operand_row}{rows}</tbody></table>"
        )
    else:
        result_block = f'<p class="error" role="alert">Invalid input: {escape(error or "unknown error")}</p>'

    resources = "".join(
        f"<li><strong>{escape(resource.name)}</strong> — {escape(resource.category)} "
        f"({escape(resource.location)})<br><span class=\"muted\">Controls: "
        f"{escape(', '.join(resource.security_controls) or 'none listed')}</span></li>"
        for resource in model.onprem_resources + model.cloud_resources
    )
    controls = "".join(
        f"<tr><td class=\"wbs\">{escape(control['wbs'])}</td><td>{escape(control['control'])}</td>"
        f"<td class=\"muted\">{escape(control['owner'])}</td></tr>"
        for control in CONTROL_DEPENDENCIES
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>BinaryBit Ops HDE demonstrator</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; line-height: 1.5; }}
main {{ max-width: 60rem; margin: 0 auto; padding: 1.5rem; }}
header {{ background: #7a1f1f; color: #fff; padding: 1rem 1.5rem; }}
header strong {{ letter-spacing: .04em; }}
h1 {{ font-size: 1.5rem; margin: 0 0 .25rem; }}
h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 1px solid #8884; padding-bottom: .25rem; }}
.badge {{ display: inline-block; padding: .1rem .45rem; border-radius: .25rem; background: #fff3; font-size: .8rem; }}
.scope {{ background: #fff4d6; color: #3a2a00; border-left: .35rem solid #b7791f; padding: .75rem 1rem; margin: 1rem 0; }}
table {{ border-collapse: collapse; width: 100%; margin: .75rem 0; }}
th, td {{ text-align: left; padding: .4rem .55rem; border-bottom: 1px solid #8883; vertical-align: top; }}
th {{ width: 9rem; }}
.num {{ font-variant-numeric: tabular-nums; font-weight: 600; width: 6rem; }}
.bin {{ font-family: ui-monospace, Consolas, monospace; white-space: nowrap; }}
.muted {{ color: #777; font-size: .9rem; }}
.wbs {{ white-space: nowrap; font-family: ui-monospace, Consolas, monospace; }}
form {{ display: flex; gap: .75rem; flex-wrap: wrap; align-items: end; }}
label {{ display: flex; flex-direction: column; font-size: .9rem; }}
input {{ font: inherit; padding: .35rem .5rem; width: 8rem; }}
button {{ font: inherit; padding: .45rem .9rem; cursor: pointer; }}
.error {{ color: #a11; font-weight: 600; }}
ul {{ padding-left: 1.2rem; }}
li {{ margin-bottom: .5rem; }}
code {{ font-family: ui-monospace, Consolas, monospace; }}
footer {{ margin-top: 2.5rem; font-size: .85rem; color: #777; }}
@media (prefers-color-scheme: dark) {{ .scope {{ background: #3a2f12; color: #ffe9b0; }} }}
</style>
</head>
<body>
<header>
  <span class="badge">DEMONSTRATOR ONLY</span>
  <h1>BinaryBit Ops HDE demonstrator</h1>
  <div>Phase 3 · WBS 3.10 · environment <strong>{escape(app.config.environment)}</strong>
  · release <strong>{escape(app.config.release)}</strong></div>
</header>
<main>
<p class="scope"><strong>Scope boundary.</strong> {escape(SCOPE_STATEMENT)}</p>

<h2>What this workload proves</h2>
<p>This page is served by an image that was built, scanned and published by the HDE
Tekton pipeline and deployed from an approved GitOps revision by Argo CD. It is a
delivery-path demonstrator, not a business system.</p>

<h2>Bit Ops calculator</h2>
<form method="get" action="/">
  <label>Left operand (0–65535)<input name="left" inputmode="numeric" value="{escape(left)}" required></label>
  <label>Right operand (0–65535)<input name="right" inputmode="numeric" value="{escape(right)}" required></label>
  <button type="submit">Compute</button>
</form>
{result_block}
<p class="muted">Machine-readable equivalent:
<code>/api/bitops?left={escape(result['left'] if result else left)}&amp;right={escape(result['right'] if result else right)}</code></p>

<h2>Delivery identity</h2>
<table>
<tbody>
<tr><th>Service</th><td>{escape(SERVICE_NAME)}</td></tr>
<tr><th>Version</th><td>{escape(build.version)}</td></tr>
<tr><th>Git commit</th><td><code>{escape(build.git_sha)}</code></td></tr>
<tr><th>Built (UTC)</th><td>{escape(build.build_date)}</td></tr>
<tr><th>Image</th><td><code>{escape(build.image_ref)}</code></td></tr>
<tr><th>Vault secret</th><td>{'injected' if secret.injected else 'not injected'}
  <span class="muted">(values are never displayed; source: {escape(secret.source)})</span></td></tr>
</tbody>
</table>

<h2>HDE control dependencies</h2>
<p class="muted">These controls are provided by the preceding work packages. Their evidence
is held by their owning teams; this workload only declares the dependency.</p>
<table>
<thead><tr><th>WBS</th><th>Control</th><th>Accountable owners</th></tr></thead>
<tbody>{controls}</tbody>
</table>

<h2>Model resources</h2>
<ul>{resources}</ul>

<h2>Operational endpoints</h2>
<ul>
<li><code>/healthz</code> liveness · <code>/readyz</code> readiness</li>
<li><code>/metrics</code> Prometheus exposition · <code>/version</code> build identity</li>
<li><code>/api/status</code> scope, build and dependency status · <code>/api/bitops</code> calculation API</li>
</ul>

<footer>Rendered by {escape(SERVICE_NAME)} {escape(build.version)} at
{escape(datetime.now(timezone.utc).isoformat(timespec="seconds"))} UTC.
No Nexus/Truehost data, credentials or integration is present.</footer>
</main>
</body>
</html>
"""


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], app: AppState):
        self.app = app
        super().__init__(address, DemoRequestHandler)


def build_state(config: DemoConfig, build: BuildInfo | None = None) -> AppState:
    secret = inspect_secret_file(config.secret_path)
    ready = (not config.require_secret) or secret.injected
    return AppState(
        config=config,
        build=build or load_build_info(),
        secret=secret,
        ready=ready,
    )


def create_server(
    config: DemoConfig | None = None,
    app: AppState | None = None,
    build: BuildInfo | None = None,
    host: str = "127.0.0.1",
    port: int | None = None,
) -> DemoServer:
    resolved_config = config or DemoConfig()
    state = app or build_state(resolved_config, build)
    bind_port = resolved_config.port if port is None else port
    return DemoServer((host, bind_port), state)


def _serve(server: DemoServer) -> None:
    def handle_signal(signum: int, _frame: Any) -> None:
        # shutdown() blocks until serve_forever returns, so call it off-thread.
        threading.Thread(target=server.shutdown, daemon=True).start()

    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is not None:
            try:
                signal.signal(sig, handle_signal)
            except (ValueError, OSError):  # pragma: no cover - non-main thread
                pass

    host, port = server.server_address[:2]
    print(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": "info",
        "service": SERVICE_NAME,
        "msg": "listening",
        "host": host,
        "port": port,
        "environment": server.app.config.environment,
        "ready": server.app.ready,
        "vault_secret_injected": server.app.secret.injected,
    }, separators=(",", ":")), flush=True)
    server.serve_forever()


def main(env: Mapping[str, str] | None = None) -> int:
    config = DemoConfig.from_env(env)
    state = build_state(config)

    if config.require_secret and not state.secret.injected:
        print(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": "error",
            "service": SERVICE_NAME,
            "msg": "required Vault secret was not injected",
            "source": state.secret.source,
        }, separators=(",", ":")), flush=True)
        return 1

    server = create_server(config=config, app=state)
    try:
        _serve(server)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover - process entry point
    sys.exit(main())
