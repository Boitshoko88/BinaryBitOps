# path: secret/data/hde/nonprod/binarybitops-demo
#
# Read-only policy for the demonstrator's Vault Agent Injector role. The
# application never holds a Vault token; the injector renders the file.

path "secret/data/hde/nonprod/binarybitops-demo" {
  capabilities = ["read"]
}

path "secret/metadata/hde/nonprod/binarybitops-demo" {
  capabilities = ["read"]
}
