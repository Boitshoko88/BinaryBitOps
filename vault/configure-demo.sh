#!/bin/sh
# Configure the Vault side of the WBS 3.10 demonstrator.
#
# Run only from an approved administrative workstation with an authenticated
# Vault CLI. This script contains no secret values: the demo secret itself is
# written separately by the secret owner, and the value must never be committed.
set -eu

: "${VAULT_ADDR:?set VAULT_ADDR to the approved Vault endpoint}"
: "${K8S_AUTH_ROLE:=binarybitops-demo}"

vault policy write binarybitops-demo-policy ./policy.hcl

# Bind the policy to the workload ServiceAccount. A dedicated Kubernetes auth
# mount is used by the platform; change the mount path if required.
vault write "auth/kubernetes/role/${K8S_AUTH_ROLE}" \
  bound_service_account_names=binarybitops-demo \
  bound_service_account_namespaces=binarybitops-demo \
  policies=binarybitops-demo-policy \
  ttl=1h

# The secret owner writes the value interactively; it is never passed on the
# command line here.
cat <<'EOF'
Next, the secret owner writes the value:

  vault kv put secret/hde/nonprod/binarybitops-demo \
    demo_api_key="$(openssl rand -base64 32)" rotation_epoch=1

Then enable REQUIRE_VAULT_INJECTION=true in the non-production overlay after the
injector is installed, and confirm /api/status reports "injected": true.
EOF
