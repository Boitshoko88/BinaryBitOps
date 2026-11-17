# Vault integration (WBS 3.8 dependency)

The demonstrator consumes one non-production secret and proves that the value is
injected at runtime rather than stored in code, manifests or container images.

## Design

- **Vault KV v2 path:** `secret/hde/nonprod/binarybitops-demo`
- **Vault role:** `binarybitops-demo`, bound to ServiceAccount
  `binarybitops-demo` in namespace `binarybitops-demo`.
- **Policy:** `policy.hcl` grants read-only access to that one path.
- **Delivery:** Vault Agent Injector renders `/vault/secrets/demo.json` from
  `deploy/overlays/nonprod/patch-vault.yaml`. No Vault token reaches the app.
- **Disclosure:** the app reports only `injected`, `source` and key names.
  `tests/test_secrets.py` and `tests/test_server.py` assert the value never
  appears in JSON, HTML, metrics, `repr` or logs.

## Setup

```sh
export VAULT_ADDR=https://<approved-vault-endpoint>
vault login                       # SSO/MFA, never a shared token
sh vault/configure-demo.sh

vault kv put secret/hde/nonprod/binarybitops-demo \
  demo_api_key="$(openssl rand -base64 32)" rotation_epoch=1
```

Then, after the injector and policy are verified:

1. Set `REQUIRE_VAULT_INJECTION: "true"` in the environment overlay.
2. Sync the Argo CD application.
3. Confirm `GET /api/status` returns `"vault": {"injected": true, ...}` and
   `/metrics` exposes `binarybitops_vault_secret_injected 1`.
4. Store the request/response (with the value redacted) as evidence.

## Rotation

1. Write a new `demo_api_key` with `rotation_epoch` incremented.
2. The injector refreshes the rendered file within its template interval
   (`agent-inject-status: update`). The workload reads the file only at startup,
   so restart the pods during an approved change window to pick up the value.
3. Confirm `rotation_epoch` changed via the secret owner's Vault audit record.
   The workload intentionally does not expose it.
4. Revoke the previous credential at the provider.

## Verification that no reusable secret is in code

```sh
trivy fs --scanners secret .
python -m unittest tests.test_secrets tests.test_server -v
git grep -nE '(api[_-]?key|password|token)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"']+' -- . ':!tests' || true
```

The intentional placeholder in `secret.example.json` is not a usable credential.
If a real secret is ever committed, treat it as compromised, rotate it first,
then remove it from history.
