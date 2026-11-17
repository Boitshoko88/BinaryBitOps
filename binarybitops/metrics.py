"""Minimal Prometheus metrics for the demonstrator.

No third-party client library is used: the workload has zero runtime
dependencies, which keeps the Trivy dependency scan meaningful and the image
small. Route labels are fixed names, never raw request paths, so cardinality
and label injection are bounded.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from .version import BuildInfo


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Metrics:
    def __init__(self, started_at: float | None = None) -> None:
        self._lock = threading.Lock()
        self._started_at = time.time() if started_at is None else started_at
        self._requests: dict[tuple[str, str, str], int] = defaultdict(int)
        self._duration_sum: dict[str, float] = defaultdict(float)
        self._duration_count: dict[str, int] = defaultdict(int)

    def observe(self, method: str, route: str, status: int, seconds: float) -> None:
        with self._lock:
            self._requests[(method, route, str(status))] += 1
            self._duration_sum[route] += seconds
            self._duration_count[route] += 1

    def render(self, build: BuildInfo, secret_injected: bool) -> str:
        lines = [
            "# HELP binarybitops_build_info Build identity of the demonstrator.",
            "# TYPE binarybitops_build_info gauge",
            (
                "binarybitops_build_info"
                f'{{version="{_escape_label(build.version)}",'
                f'git_sha="{_escape_label(build.git_sha)}"}} 1'
            ),
            "# HELP binarybitops_vault_secret_injected Whether a Vault-rendered secret file is present.",
            "# TYPE binarybitops_vault_secret_injected gauge",
            f"binarybitops_vault_secret_injected {1 if secret_injected else 0}",
            "# HELP binarybitops_uptime_seconds Seconds since process start.",
            "# TYPE binarybitops_uptime_seconds gauge",
            f"binarybitops_uptime_seconds {max(0.0, time.time() - self._started_at):.3f}",
            "# HELP binarybitops_http_requests_total HTTP requests by method, route and status.",
            "# TYPE binarybitops_http_requests_total counter",
        ]

        with self._lock:
            for (method, route, status), count in sorted(self._requests.items()):
                lines.append(
                    "binarybitops_http_requests_total"
                    f'{{method="{_escape_label(method)}",route="{_escape_label(route)}",'
                    f'status="{status}"}} {count}'
                )
            lines.extend([
                "# HELP binarybitops_http_request_duration_seconds HTTP request duration by route.",
                "# TYPE binarybitops_http_request_duration_seconds summary",
            ])
            for route, total in sorted(self._duration_sum.items()):
                count = self._duration_count[route]
                lines.append(
                    f'binarybitops_http_request_duration_seconds_sum{{route="{_escape_label(route)}"}} {total:.6f}'
                )
                lines.append(
                    f'binarybitops_http_request_duration_seconds_count{{route="{_escape_label(route)}"}} {count}'
                )

        return "\n".join(lines) + "\n"
