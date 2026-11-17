# Dependency gates before Task 3.10 delivery

The WBS sequencing rules are strict: no developer workspace is enabled before
the identity, device and OpenZiti gates pass, and no UAT begins before testing
and remediation complete. For 3.10 specifically: 3.6 must have started and 3.9
must be usable before deployment.

Run these checks from an approved, compliant device over the approved access path.
Record the output; do not paste credentials or tokens.

## Gate table

| Gate | Check | Command (example) | Pass condition | Current state |
| --- | --- | --- | --- | --- |
| 3.2 | Non-production cluster reachable and namespace permitted | `kubectl config current-context`; `kubectl auth can-i create deployments -n binarybitops-demo` | Expected context, `yes` | Unknown — no cluster in this workspace |
| 3.3 | Operator identity, MFA and RBAC | `kubectl auth whoami`; `argocd account get --account <user>`; IdP sign-in record | Named identity, MFA satisfied, least-privilege role | Unknown |
| 3.4 | Device compliant | MDM console posture record for the device serial | Compliant, encrypted, screen lock, no local persistence exception | Unknown |
| 3.5 | Private access through OpenZiti | `ziti edge list identities`; attempt an unapproved path | Approved identity present; unapproved path denied | Unknown |
| 3.6 | Authoritative repository and protection | `curl -s -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/repos/<org>/<repo>/branches/main/protection` | Required review ≥1, status checks required, force-push disabled | **Not met** — demo branch not yet protected/approved |
| 3.8 | Vault available and workload-scoped | `vault status`; `vault policy read binarybitops-demo-policy`; `vault read auth/kubernetes/role/binarybitops-demo` | Initialised, policy limited to one path, role bound to the demo ServiceAccount | Unknown |
| 3.9 | Tekton, Trivy and Argo CD usable | `tkn pipeline list -n binarybitops-ci`; `tkn task list -n binarybitops-ci`; `argocd app list`; `trivy --version` | Pipeline and scan tasks installed; Argo CD reachable; Trivy version recorded | **Not met** — HDE repos contain scaffold files only |
| 3.9 | Registry credentials | `crane ls <registry>/binarybitops-demo` with the approved config | Authorised pull/push; digest support | Unknown |
| 3.9 | Ingress path | Approved URL or OpenZiti service responds | `/healthz` returns 200 from an approved device | Unknown |

## Stop conditions

Do not proceed to deployment if any of the following is true:

- the cluster context is production or is not the approved non-production target;
- the repository does not require an independent review;
- Tekton or Trivy tasks referenced by `ci/pipeline.yaml` do not exist;
- Vault is unavailable and the plan relies on a secret in Git or in a PipelineRun;
- the image would be deployed by tag rather than digest;
- the device is non-compliant or the access path is not through OpenZiti.

## Recording

Copy the command output (redacted) into `evidence/wbs-3.10-record.md` under
"Entry gate evidence". Where a gate is owned by another work package, link to
that package's evidence instead of duplicating it.
