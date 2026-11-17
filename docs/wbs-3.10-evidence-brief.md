# WBS 3.10 evidence brief — presentation pack

**Binary Bit Ops demonstrator (Phase 3, Hybrid Development Environment)**

| | |
| --- | --- |
| Prepared | 2026-11-17 |
| Audience | Nomhle (work package lead), Manqoba, Reitumetse, Lelo (project manager) |
| Repository | `Boitshoko88/BinaryBitOps`, branch `feature/task-3.10-demonstrator` |
| Pull request | [#1](https://github.com/Boitshoko88/BinaryBitOps/pull/1) |
| Head commit | `5bb1d6b` (at preparation; the PR shows the current head) |
| Slide deck | [`docs/wbs-3.10-evidence-deck.pptx`](wbs-3.10-evidence-deck.pptx) — 14 slides, speaker notes on every slide |
| Status | **AMBER — deliverable ready, HDE evidence incomplete.** Not "complete" on the WBS record. |

> One-line summary: the demonstrator is built, reviewed by automation, containerised
> and scanned in CI; the approved PR, Tekton run, published digest, Argo CD sync
> and Vault proof are still outstanding and cannot be produced from this workspace.

How to use this pack: each numbered section is one slide. "Say" is the spoken
line, "Show" is what to open on screen. Nothing here claims more than the
evidence supports.

---

## 1. Title and status

**Say:** "Task 3.10 asked for a demonstrator delivered through the HDE path:
reviewed code, an approved PR, and a pipeline-delivered workload. The workload
and the review automation are done. The HDE half of the evidence is not, and I
am not going to present it as if it were."

**Show:** this table, and the status banner in
[`docs/task-3.10-status.md`](task-3.10-status.md).

| Dimension | State |
| --- | --- |
| Code and tests | Complete (77 tests) |
| Container image | Builds; scanned clean in CI |
| PR automation | Green |
| Independent approval | **Outstanding** |
| Tekton delivery | **Outstanding** (3.9 not usable) |
| Registry digest | **Outstanding** |
| Argo CD sync | **Outstanding** |
| Vault injection | **Outstanding** |
| Owner sign-off | **Outstanding** |

---

## 2. Scope boundary

**Say:** "This is a demonstrator. It is not the live Binary Bit Ops/Nexus
application and it does not move it. No Nexus code, data, credentials, DNS or
database connection is in this branch."

**Show:** [`docs/non-migration-attestation.md`](non-migration-attestation.md),
and the banner in the running service (`GET /`).

- Live estate stays on Truehost, PHP/MySQL, untouched.
- Demonstrator runs in its own namespace, `binarybitops-demo`, non-production.
- The service states the boundary on its own index page and in `/api/status`.
- No credentials are stored: Vault injects at runtime, and the app reports only
  injection status, never values.

---

## 3. What was built

**Say:** "A dependency-free Python 3.12 HTTP service, because the point is to
prove the delivery path, not to add a framework to maintain. It has real
liveness and readiness, build metadata, metrics, and a 16-bit bitwise API."

**Show:** `binarybitops/server.py`, `Dockerfile`, or run it locally:
`python -m binarybitops.server` then open `http://127.0.0.1:8080`.

| Endpoint | Purpose |
| --- | --- |
| `/healthz` | Liveness, always cheap |
| `/readyz` | Readiness, includes Vault requirement when enabled |
| `/version` | Version, commit, build date, image reference |
| `/api/bitops?left=12&right=10` | `and=8, or=14, xor=6`, fixed 16-bit width |
| `/api/status` | Environment, controls, secret key names only |
| `/metrics` | Prometheus text format, build info and request counters |
| `/` | HTML index with the scope banner and a live example |

Design choices worth stating: standard library only, fixed non-root UID 10001,
read-only root filesystem compatible, no service account token, structured JSON
logs, and input bounds that return errors without echoing untrusted input.

---

## 4. Delivery chain

**Say:** "Code goes through tests, a source scan, a build, an image scan, a digest
publish and a GitOps pull request. Argo CD syncs manually. Nothing deploys
straight from the pipeline."

**Show:** `ci/pipeline.yaml` and `argocd/application.yaml`.

```text
commit → unit tests → Trivy source/secret/misconfig → build image
      → Trivy image → publish by digest → GitOps PR (digest patch)
      → independent approval → Argo CD manual sync → cluster
```

Controls in the chain:

- The pipeline fails on HIGH or CRITICAL findings, both at source and image.
- Only an immutable `@sha256:` digest reaches the overlay; tags are rejected by
  the pin task and by a manifest test.
- Argo CD has automated sync explicitly disabled, so a human performs the sync
  and is recorded.
- The Argo CD project is namespace-scoped, not cluster-wide.

---

## 5. Evidence at a glance

**Say:** "These are the numbers from the current head commit. Local run first,
then the same checks in CI, then the image-specific checks that CI can do and
this laptop cannot."

**Show:** `evidence/local/local-verification.md` (regenerate with
`pwsh ./scripts/verify.ps1`), and the CI run
[44072141405](https://github.com/Boitshoko88/BinaryBitOps/actions/runs/44072141405).

| Check | Result | Where |
| --- | --- | --- |
| Unit, HTTP, secret and manifest tests | **77 passed**, 0 failed | local + CI |
| Kustomize render (nonprod overlay) | **9 resources** | local + CI |
| kubeconform strict | **8 valid**, 0 invalid, 1 skipped (ServiceMonitor CRD) | local + CI |
| Trivy filesystem (vuln, secret, misconfig) | **0 HIGH/CRITICAL, 0 secrets** | local + CI |
| HTTP smoke tests | **15 checks passed** | local |
| Container build | **Success** | CI |
| Container smoke test | **Passed** (health, bitwise, banner, metrics) | CI |
| Trivy image gate | **Passed** (0 HIGH/CRITICAL) | CI |
| Local verification summary | **15 of 16 passed**, 1 skipped (no Docker daemon) | local |

---

## 6. Requirement traceability

**Say:** "Every WBS 3.10 expectation maps to a file and a proof. Where the proof
does not exist yet, the table says so."

**Show:** this table; the detail is in [`acceptance-criteria.md`](acceptance-criteria.md)
(AC-01 to AC-15).

| Requirement | Artefact | Proof | State |
| --- | --- | --- | --- |
| Reviewed code | `binarybitops/`, `tests/`, `deploy/`, `ci/`, `argocd/`, `vault/` | PR #1, PR check green | **Partial** — automation reviewed, no human approval |
| Approved PR | PR #1 | Review and approval record | **Outstanding** |
| Pipeline-delivered demonstrator | `ci/pipeline.yaml`, `ci/tasks/*` | Tekton PipelineRun log | **Outstanding** |
| Immutable image for GitOps | `deploy/overlays/nonprod/patch-image.yaml` | Registry digest, GitOps PR | **Outstanding** |
| Deployment via GitOps | `argocd/application.yaml` | Sync revision, sync result, sync identity | **Outstanding** |
| Secret injection without Git secrets | `vault/policy.hcl`, `deploy/overlays/nonprod/patch-vault.yaml` | Vault agent read in cluster, redacted `/api/status` | **Outstanding** |
| Observability | `deploy/observability/servicemonitor.yaml`, `/metrics` | Prometheus target, Loki log reference | **Outstanding** |
| Scope boundary | `docs/non-migration-attestation.md` | Attestation, tests asserting no Nexus content | **Complete** |
| Entry gates 3.3–3.6, 3.8, 3.9 | `docs/dependency-gates.md` | Gate outputs | **Not met** (3.6, 3.9) |

---

## 7. What the gates caught

**Say:** "The most useful evidence is not that the checks pass now, it is that
they failed first. Four real defects were caught before anything could be
deployed, including a bug that would have broken Kubernetes probes."

**Show:** the commit list
(`git log --oneline 06ef3b0..HEAD`), or the failed runs.

| # | Defect | How it was caught | Fix |
| --- | --- | --- | --- |
| 1 | Trivy action pinned to a tag that does not exist (`0.28.0`) | Every PR job failed at setup | Pinned `v0.36.0`, Trivy `v0.76.2` |
| 2 | Service bound `127.0.0.1` inside the container | Container smoke test: connection reset | Bind the configured host; **this also fixes liveness/readiness probes in Kubernetes** |
| 3 | Base image a year out of date: 3 CRITICAL, 29 HIGH | Trivy image gate | `python:3.12-alpine3.24`, removed pip/setuptools/wheel |
| 4 | 16 HIGH in `krb5-libs`, fix already published | Trivy image gate | `apk upgrade --no-cache` during build |

**48 HIGH/CRITICAL findings, 3 of them CRITICAL, were removed before the image
could be published.** That is the scan gate doing its job, not a failure of the
deliverable.

---

## 8. Security posture

**Say:** "The workload is hardened by default in four places: the image, the
pod, the network and the secret path."

**Show:** `deploy/base/deployment.yaml`, `deploy/base/networkpolicy.yaml`,
`vault/policy.hcl`.

| Layer | Control |
| --- | --- |
| Image | Non-root UID 10001, no package manager, OCI labels, health check, no third-party runtime packages |
| Pod | `runAsNonRoot`, read-only root filesystem with `/tmp` mount, all capabilities dropped, seccomp `RuntimeDefault`, no privilege escalation, no service account token |
| Namespace | Pod Security Admission `restricted` |
| Network | Default-deny ingress and egress; DNS-only egress; ingress limited to named namespaces on port 8080 |
| Availability | 2 replicas, rolling update, PodDisruptionBudget, probes and resource limits |
| Secrets | Vault agent injects at runtime; read-only, single-path policy; app exposes key names and injection status only |
| Supply chain | Test → scan → build → scan → digest; no tag-based deploy; manual Argo CD sync |

---

## 9. What is not proven yet

**Say:** "This is the honest gap list. Each item has an owner and a blocking
dependency. None of it can be closed from this laptop."

**Show:** `docs/dependency-gates.md` and the outstanding table in
`docs/task-3.10-status.md`.

| # | Outstanding | Owner | Blocked by |
| --- | --- | --- | --- |
| 1 | Independent review and approval of PR #1 | Nomhle | reviewer availability |
| 2 | Branch protection: required review, required checks, no force-push | Manqoba | 3.6 |
| 3 | Tekton run of the pipeline | Reitumetse | 3.9 (tasks not installed) |
| 4 | Publish image, record digest | Manqoba | registry access |
| 5 | GitOps digest PR approved and merged | Nomhle | 3.6, step 4 |
| 6 | Argo CD manual sync | Reitumetse | 3.9, step 5 |
| 7 | Vault injection in cluster, redacted `/api/status` | Nomhle | 3.8, step 6 |
| 8 | Prometheus target and Loki reference | Reitumetse | monitoring stack |
| 9 | Sign `evidence/wbs-3.10-record.md` | Nomhle, Manqoba, Reitumetse | steps 1–8 |

Why the gap exists, plainly: the `hde-pipelines` and `hde-gitops` repositories
still contain scaffold files only, and there is no cluster, registry, Vault or
Argo CD access in this workspace. The identity, device and OpenZiti gates
(3.3–3.5) also gate any deployment or UAT, as the WBS requires.

---

## 10. Decision requested

**Say:** "I am asking for three things today: approval to merge the demonstrator
code, a named independent reviewer, and a date to run the pipeline once 3.9 is
usable."

| Decision | Owner | Needed by |
| --- | --- | --- |
| Merge PR #1 (code and delivery definitions only; no deployment) | Nomhle | before the pipeline run |
| Name an independent reviewer who is not the author | Lelo | this week |
| Confirm 3.9 tasks and registry access for the PipelineRun | Reitumetse | before the run |
| Accept that Task 3.10 stays **open** until the record is signed | All | now |

What merging does **not** do: it does not deploy, does not publish an image, does
not touch Truehost or Nexus, and does not mark the WBS item complete.

---

## 11. Live demo script (about 5 minutes)

Run from a clean checkout on a machine with Python 3.12+.

```powershell
# 1. Tests (about 3 seconds)
python -m unittest discover -s tests -t . -q      # Ran 77 tests ... OK

# 2. The service itself
python -m binarybitops.server                     # listening on 0.0.0.0:8080
```

```text
# 3. In a second terminal
curl http://127.0.0.1:8080/healthz
curl "http://127.0.0.1:8080/api/bitops?left=12&right=10"   # and=8 or=14 xor=6
curl http://127.0.0.1:8080/version
curl http://127.0.0.1:8080/metrics
```

```powershell
# 4. The delivery artefacts
kubectl kustomize deploy/overlays/nonprod        # 9 resources
pwsh ./scripts/verify.ps1                       # full local evidence record
```

Then open PR #1 and its green check run.

Fallback if the laptop misbehaves: use the recorded numbers in section 5 and the
CI run link. Do not improvise numbers.

---

## 12. Anticipated questions

| Question | Answer |
| --- | --- |
| "Is this the live Nexus application?" | No. Separate demonstrator, separate namespace, no Nexus code, data or credentials. Attestation is in the repo. |
| "Has it been deployed?" | Not yet. The Kubernetes, Tekton and Argo CD definitions exist and validate; no cluster has run them. |
| "So what is actually proven?" | Code quality, manifest correctness, security configuration, image buildability, scan cleanliness, and that the gates reject bad input. |
| "Why is the WBS item not complete?" | Completion needs an approved PR and a pipeline-delivered, digest-pinned deployment. Those need 3.6 and 3.9 plus people. |
| "Why Python and no framework?" | The deliverable proves the delivery path. Fewer dependencies means fewer CVEs and a smaller, reviewable surface. |
| "Why is Argo CD manual?" | Deliberate. A human triggers the sync and is recorded, which is stronger evidence than automated sync for this task. |
| "What happens if a scan finds something later?" | The pipeline fails on HIGH/CRITICAL. That is how the four defects in section 7 were found. |
| "Can we skip the gates to hit the window?" | No. 3.3–3.5 gate any deployment or UAT by WBS rule. |

---

## 13. Evidence index

| Evidence | Location | Notes |
| --- | --- | --- |
| Status and gap list | `docs/task-3.10-status.md` | Read this first |
| Acceptance criteria AC-01…AC-15 | `docs/acceptance-criteria.md` | Includes the negative tests |
| Entry gates and stop conditions | `docs/dependency-gates.md` | 3.6 and 3.9 recorded as not met |
| Non-migration attestation | `docs/non-migration-attestation.md` | Scope boundary |
| Runbook | `docs/runbook.md` | Deploy, verify, roll back, troubleshoot |
| Security exceptions | `docs/security-exceptions.md` | Two narrow, documented suppressions |
| Evidence record to sign | `evidence/wbs-3.10-record.md` | Unfilled, by design |
| PR body | `docs/pull-request-body.md` | Reviewer checklist |
| Local verification | `evidence/local/local-verification.md` | Git-ignored; regenerate per machine |
| Pull request | https://github.com/Boitshoko88/BinaryBitOps/pull/1 | Code, review, checks |
| CI run | https://github.com/Boitshoko88/BinaryBitOps/actions/runs/44072141405 | Build, smoke, image scan |

Recording rule: evidence comes from the system that produced it. Never paste
secret values, tokens or kubeconfig into slides or the record.

---

## 14. Sign-off block

Complete only after steps 1–8 in section 9 are done and the record is filled from
project systems.

| Role | Name | Decision | Date (UTC) | Reference |
| --- | --- | --- | --- | --- |
| Work package lead | Nomhle | | | |
| Delivery engineer | Manqoba | | | |
| Delivery engineer | Reitumetse | | | |
| Independent reviewer | | | | |
| Project manager | Lelo | | | |

**Current completion decision: NOT COMPLETE.** Conditions: approved PR, Tekton
PipelineRun, published digest, Argo CD sync, Vault injection, observability
proof, and owner signatures.
