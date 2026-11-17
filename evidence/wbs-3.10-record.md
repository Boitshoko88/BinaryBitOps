# WBS 3.10 evidence record

Fill from project systems only. Do not paste secret values. Link raw artefacts
stored under `evidence/run-<date>/`.

## 1. Identity chain

| Field | Value |
| --- | --- |
| Repository | |
| Feature branch | |
| Demonstrator commit SHA | |
| Merge commit SHA | |
| Pull request URL | |
| Independent reviewer (handle) | |
| Approval timestamp (UTC) | |
| Merge timestamp (UTC) | |

## 2. Entry gates

| Gate | Result | Evidence reference |
| --- | --- | --- |
| 3.2 cluster and namespace | | |
| 3.3 identity, MFA, RBAC | | |
| 3.4 device posture | | |
| 3.5 OpenZiti access | | |
| 3.6 repository protection | | |
| 3.8 Vault policy and role | | |
| 3.9 Tekton, Trivy, Argo CD | | |

## 3. Pipeline and scans

| Field | Value |
| --- | --- |
| Tekton PipelineRun name | |
| Namespace | |
| Revision built | |
| Unit test result | |
| Source scan result (secret) | |
| Source scan result (vuln/misconfig) | |
| Image build result | |
| Image scan result and finding counts | |
| Gate failure evidence (negative test) | |
| Report locations | |
| Published image reference | |
| Immutable digest | |

## 4. GitOps and deployment

| Field | Value |
| --- | --- |
| GitOps PR URL | |
| GitOps approval | |
| GitOps commit with digest | |
| Argo CD application | |
| Sync revision | |
| Sync result and timestamp | |
| Manual sync by (identity) | |
| Namespace / Deployment / Pods | |
| `/version` output | |
| `/api/status` output (redacted) | |
| `/metrics` sample | |
| Vault injection status | |
| Prometheus target | |
| Loki log reference | |

## 5. Security verification

| Check | Result | Reference |
| --- | --- | --- |
| Non-root UID 10001 | | |
| Read-only root filesystem | | |
| Capabilities dropped | | |
| Restricted PSA namespace | | |
| Default-deny NetworkPolicy | | |
| Unauthorised namespace cannot reach the service | | |
| No secret in Git or image | | |
| HIGH/CRITICAL findings | | |
| Approved exceptions (EX-01…EX-06) | | |

## 6. Owner review

| Reviewer | Role | Decision | Date | Reference |
| --- | --- | --- | --- | --- |
| Nomhle | Work package lead | | | |
| Manqoba | Delivery engineer | | | |
| Reitumetse | Delivery engineer | | | |
| Independent reviewer | Code review | | | |
| Lelo | Project manager | | | |

## 7. Scope confirmation

- [ ] Confirmed separate from the Truehost PHP/MySQL Nexus application.
- [ ] No Nexus code, data, credentials, DNS or database connection introduced.
- [ ] Attestation signed and linked.

Open defects, limitations or risk acceptances:

## 8. Completion decision

| Field | Value |
| --- | --- |
| Decision | Complete / Not complete |
| Decided by | |
| Date (UTC) | |
| Conditions or follow-ups | |
