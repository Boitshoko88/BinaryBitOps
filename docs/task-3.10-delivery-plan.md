# WBS 3.10 delivery plan — Binary Bit Ops demonstrator

**Work package:** 3.10 Create and deliver the Binary Bit Ops demonstrator  
**Dependency:** 3.6 started; 3.9 required for deployment  
**Window:** Days 4–7 of the Phase 3 10-day plan  
**Accountable owners:** Nomhle, Manqoba, Reitumetse  
**Scope:** demonstrator workload only; no migration of the Truehost PHP/MySQL
Nexus application.

## 1. Objective

Deliver a small workload through the approved HDE path — reviewed code, approved
pull request, Tekton build/test, Trivy gates, immutable image, approved GitOps
change, manual Argo CD sync — and retain evidence that the path worked.

The demonstrator deliberately contains no business logic from Nexus. It proves
the delivery system, not the application.

## 2. Entry criteria

| Gate | Requirement | How confirmed | State |
| --- | --- | --- | --- |
| 3.6 started | Repository exists, branch protection and PR review are active | GitHub settings screenshot and a test PR approval | Not verified in this workspace |
| 3.9 available for deployment | Working Tekton pipeline, Trivy tasks, registry, Argo CD | Successful 3.9 PipelineRun and Argo CD application health | **Not met** — `hde-pipelines` and `hde-gitops` currently contain README/scaffold files only |
| 3.8 available for secret proof | Vault policy/role and injector or ESO | Vault audit record and injected pod | Not verified in this workspace |
| 3.2/3.3 | Cluster namespace and identity for operators | `kubectl auth whoami`, Argo CD SSO login | Not verified in this workspace |
| Device/access gates 3.4–3.5 | Only compliant, Ziti-connected devices administer the demo | MDM and OpenZiti evidence owned by 3.4/3.5 | Not verified in this workspace |

**Sequencing rule:** this work package may prepare code in parallel with 3.6, but
no deployment, workspace enablement or UAT begins until the gates above hold.

## 3. Work sequence (Days 4–7)

| Day | Activity | Output | Owner |
| --- | --- | --- | --- |
| 4 | Confirm scope boundary; finalise demo behaviour and acceptance criteria; branch from protected `main` | This plan, acceptance criteria, feature branch | Nomhle |
| 4–5 | Implement demonstrator; add unit/HTTP/manifest/secret-redaction tests; container build | Reviewed code, test suite, image | Manqoba |
| 5 | Raise PR; independent review; PR checks (tests, Trivy, manifest render, image scan) | Approved PR and check results | Reitumetse + reviewer |
| 5–6 | Register `ci/` definitions in `hde-pipelines` (3.9 change); run PipelineRun against the merged commit | PipelineRun logs, Trivy reports, image digest | Manqoba |
| 6 | GitOps digest PR to the approved overlay; independent approval | Approved GitOps PR and pinned digest | Reitumetse + reviewer |
| 6–7 | Manual Argo CD sync; verify pods, `/version`, `/api/status`, `/metrics`, secret injection; capture logs | Sync revision, Kubernetes evidence, screen captures | Nomhle |
| 7 | Owner review against acceptance criteria; record decision | Signed evidence record | Nomhle, Manqoba, Reitumetse |

## 4. Deliverables

1. Reviewed demonstrator source with automated tests.
2. Hardened container image built from a pinned base and non-root runtime.
3. Tekton pipeline and tasks with test and Trivy gates.
4. GitOps overlay pinned to the image digest, plus restricted Argo CD project.
5. Vault policy, role and injector template proving runtime secret delivery.
6. Evidence record containing: PR approval, pipeline run, scan results, digest,
   GitOps approval, Argo CD revision/sync, pod and endpoint output, owner review.
7. Non-migration attestation.

## 5. Exit criteria (definition of done)

- [ ] Code reviewed by a person other than the author; PR approved and merged.
- [ ] Tekton PipelineRun succeeded for the merged commit; tests and Trivy source
      and image gates passed; reports retained.
- [ ] Published image referenced by immutable digest.
- [ ] GitOps change approved and merged; no direct cluster mutation was used.
- [ ] Argo CD synced that revision manually; application Healthy.
- [ ] Deployment running in `binarybitops-demo`; `/version` returns the merged
      commit; `/metrics` scraped; logs visible in Loki.
- [ ] Vault-injected secret confirmed without disclosing its value (or a written
      exception if 3.8 is not available).
- [ ] Owner review recorded; no open HIGH/CRITICAL findings without an approved
      risk acceptance.
- [ ] Non-migration attestation signed.

## 6. RACI

| Activity | Nomhle | Manqoba | Reitumetse | Independent reviewer | Platform/security |
| --- | --- | --- | --- | --- | --- |
| Scope and acceptance | A/R | C | C | I | C |
| Implementation and tests | C | A/R | C | I | C |
| PR approval | C | C | R | A | I |
| Pipeline run | I | A/R | C | I | C |
| GitOps change | C | R | A | A (approval) | C |
| Argo CD sync | A/R | C | C | I | C (access) |
| Vault policy | I | C | C | I | A/R |
| Evidence and sign-off | A/R | R | R | C | C |

## 7. Risks and controls

| Risk | Control |
| --- | --- |
| Demo mistaken for a Nexus migration | Scope banner in UI and README; attestation; separate repo/namespace; no Nexus data |
| Pipeline unavailable (3.9 not delivered) | Code and tests can be prepared; deployment is explicitly blocked and recorded as outstanding |
| Mutable tag deployed | Publish task records digest; GitOps patch is rewritten to `@sha256:`; Argo CD diff review |
| Secret leakage | No runtime dependency on secret value; Trivy secret gate; redaction tests; Vault-injected file only |
| Self-approval | Reviewer independence checked in PR template; CODEOWNERS to be enabled by the repo owner |
| Demo left running | Runbook step to scale to zero or delete the Argo CD application after evidence capture |

## 8. Evidence references

- `evidence/wbs-3.10-record.md` — authoritative record, filled from project systems.
- `docs/acceptance-criteria.md` — testable acceptance items and methods.
- `docs/dependency-gates.md` — commands to verify entry criteria.
- `docs/runbook.md` — deployment, verification, rollback and capture commands.
