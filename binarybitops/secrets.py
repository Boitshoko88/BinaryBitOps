"""Runtime secret status without secret disclosure.

The workload never needs the secret value to prove that Vault injection works.
It reports only whether the rendered file exists, where it came from and which
key names are present. Values are never read into the status object, logged,
serialised or returned over HTTP.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SecretStatus:
    """Non-sensitive description of the injected secret file."""

    injected: bool
    source: str
    keys: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"injected": self.injected, "source": self.source, "keys": list(self.keys)}

    def __repr__(self) -> str:  # pragma: no cover - defensive clarity
        return f"SecretStatus(injected={self.injected!r}, source={self.source!r}, keys={self.keys!r})"


def inspect_secret_file(path: str | os.PathLike[str] | None) -> SecretStatus:
    """Inspect a Vault-rendered secret file without returning its contents."""

    if not path:
        return SecretStatus(injected=False, source="not-configured")

    secret_path = Path(path)
    # Source is a fixed label, never the caller-supplied path, so that an
    # unexpected path cannot leak into logs or responses.
    source = "vault-agent-injected"
    try:
        if not secret_path.is_file():
            return SecretStatus(injected=False, source=source)
        raw = secret_path.read_text(encoding="utf-8")
    except OSError:
        return SecretStatus(injected=False, source=source)

    keys: tuple[str, ...] = ()
    if secret_path.suffix == ".json":
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            keys = tuple(sorted(str(key) for key in parsed)[:10])
        else:
            keys = ("invalid-secret-document",)
    else:
        keys = (secret_path.name,)

    # Drop the raw text before returning; only key names survive.
    del raw
    return SecretStatus(injected=True, source=source, keys=keys)


def secret_path_from_env(env: dict[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    return source.get("VAULT_INJECTED_FILE", "/vault/secrets/demo.json")


def require_secret_from_env(env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return source.get("REQUIRE_VAULT_INJECTION", "false").strip().lower() in {"1", "true", "yes"}
