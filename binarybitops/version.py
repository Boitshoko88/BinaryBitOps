"""Build metadata for the demonstrator workload.

All values come from the build pipeline or the runtime environment. They are
validated and length-limited because they are rendered into HTML, JSON and
Prometheus labels.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_DATE_RE = re.compile(r"^[0-9A-Za-z:.+_-]{4,40}$")
_VERSION_RE = re.compile(r"^[0-9A-Za-z.+_-]{1,32}$")


def _sanitize(value: str | None, fallback: str, pattern: re.Pattern[str]) -> str:
    if not value:
        return fallback
    candidate = value.strip()
    if not pattern.match(candidate):
        return fallback
    return candidate


@dataclass(frozen=True)
class BuildInfo:
    """Immutable build identity exposed by ``/version`` and ``/metrics``."""

    version: str = "0.1.0"
    git_sha: str = "unknown"
    build_date: str = "unknown"
    image_ref: str = "local"

    def as_dict(self) -> dict[str, str]:
        return {
            "service": "binarybitops-demo",
            "version": self.version,
            "git_sha": self.git_sha,
            "build_date": self.build_date,
            "image_ref": self.image_ref,
        }


def load_build_info(env: Mapping[str, str] | None = None) -> BuildInfo:
    """Read build metadata from the environment with safe defaults."""

    source = os.environ if env is None else env
    return BuildInfo(
        version=_sanitize(source.get("APP_VERSION"), "0.1.0", _VERSION_RE),
        git_sha=_sanitize(source.get("GIT_SHA"), "unknown", _SHA_RE),
        build_date=_sanitize(source.get("BUILD_DATE"), "unknown", _DATE_RE),
        image_ref=_sanitize(source.get("IMAGE_REF"), "local", re.compile(r"^[0-9A-Za-z:./@_-]{1,120}$")),
    )
