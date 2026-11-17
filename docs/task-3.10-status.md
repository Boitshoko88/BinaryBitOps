# Task 3.10 status — Binary Bit Ops demonstrator

- Status date (UTC): 2026-11-17
- Branch: `feature/task-3.10-demonstrator`
- Repository: `Boitshoko88/BinaryBitOps` (fork of `mahlatse932/BinaryBitOps`)
- Base commit: `06ef3b0`

## Decision

**Task 3.10 is not complete.** The deliverable is implemented and locally
verified, and is ready for independent review. The evidence that the WBS actually
requires — an approved PR, a Tekton PipelineRun, a registry digest, an Argo CD
sync and cluster-side Vault injection — does not exist yet and cannot be produced
from this workspace.

Nothing in this branch implies migration of the live Binary Bit Ops / Nexus
Truehost PHP/MySQL application. The demonstrator is a separate, dependency-free
Python service in its own namespace, and carries no Nexus code, data, DNS,
database connection or credentials. See
[`non-migration-attestation.md`](non-migration-attestation.md).

## What is done

| Area | State | Where |
| --- | --- | --- |
| Demonstrator service (HTTP `/healthz`, `/readyz`, `/version`, `/api/bitops`, `/api/status`, `/metrics`, `/`) | Implemented | `binarybitops/` |
| Prior CLI / environment model preserved | Implemented | `binarybitops.py` |
| Test suite | 75 tests, all passing | `tests/` |
| Hardened container image definition | Written; build not executed locally | `Dockerfile` |
| Kubernetes base + non-production overlay | Rendered and schema-validated locally | `deploy/` |
| Tekton pipeline and tasks | Written; never executed on a cluster | `ci/` |
| Argo CD project and Application (manual sync) | Written; never applied | `argocd/` |
| Vault policy, injector annotations, ESO alternative | Written; never applied | `vault/` |
| PR workflow and gates | Written; never run on GitHub | `.github/workflows/` |
| Local verification script | Runs end to end | `scripts/verify.ps1`, `scripts/verify.sh` |

## Local verification results

Produced by `pwsh ./scripts/verify.ps1`. The generated record
`evidence/local/local-verification.md` is intentionally git-ignored because it
contains host and timestamp data; regenerate it on the reviewing machine.

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -t .` | 75 tests, exit 0 |
| `kubectl kustomize deploy/overlays/nonprod` | 9 resources rendered |
| kubeconform `-strict` | 8 valid, 0 invalid, 1 skipped (ServiceMonitor CRD) |
| Trivy fs (`vuln,secret,misconfig`, HIGH/CRITICAL) | 0 HIGH/CRITICAL, 0 secrets |
| HTTP smoke tests against the running service | 15 passed, 0 failed |
| Container build and image scan | **Skipped** — no reachable Docker daemon |

Skips and limitations:

- The Docker CLI is installed but the engine pipe
  (`npipe:////./pipe/dockerDesktopLinuxEngine`) is not available in this
  workspace, so the image was never built here and no image scan was run.
  The first real image build will be the Tekton `demo-build-image` task, or a
  local `docker build` on a host with a working engine.
- Local Trivy is `v0.76.2`, matching the version pinned in `ci/tasks/`. Trivy
  misconfiguration coverage of kustomize *patches* is partial; the base
  Deployment is fully scanned. The narrow suppressions are documented in
  [`.trivyignore.yaml`](../.trivyignore.yaml) and
  [`security-exceptions.md`](security-exceptions.md).
- `kubectl apply --dry-run=client` was not used: kubectl 1.36 still contacts the
  API server for client-side dry-run, and no cluster is reachable.

## What is not proven

These are the WBS acceptance items. None of them can be satisfied by local
commands, tests or rendered YAML:

1. **Reviewed code and approved PR.** The branch is authored by the same person
   who would have to approve it; independent review is outstanding.
2. **Pipeline-delivered demonstrator.** No Tekton PipelineRun has run. The
   `hde-pipelines` repository still contains scaffold files only, so the tasks
   referenced by `ci/pipeline.yaml` do not exist in the cluster.
3. **Immutable image.** No image has been built, published or digest-pinned. The
   overlay ships a deliberate placeholder digest that the pin task replaces.
4. **Argo CD deployment.** No Application exists, so there is no sync revision,
   no sync result and no manual-sync identity on record.
5. **Vault injection in the cluster.** The policy and annotations are written;
   no workload has read a secret through the Vault agent.
6. **Observability ingestion.** The ServiceMonitor and `/metrics` are defined;
   no Prometheus target or Loki log reference exists.
7. **Owner acceptance.** Nomhle, Manqoba and Reitumetse have not signed the
   record in [`../evidence/wbs-3.10-record.md`](../evidence/wbs-3.10-record.md).
8. **Entry gates.** 3.6 is not met and 3.9 is not usable in this environment.
   See [`dependency-gates.md`](dependency-gates.md).

Per the WBS sequencing rules, no deployment or UAT may happen before the
identity, device and OpenZiti gates (3.3–3.5) pass. The local work does not
bypass that rule; it only prepares the artefacts.

## Outstanding actions

| # | Action | Owner | Blocked by |
| --- | --- | --- | --- |
| 1 | Open PR from `feature/task-3.10-demonstrator` and obtain independent review | Nomhle | — |
| 2 | Protect the default branch: required review, required checks, no force-push | Manqoba | 3.6 |
| 3 | Install Tekton tasks and Trivy from `ci/`, then run the PipelineRun | Reitumetse | 3.9 |
| 4 | Publish the image and record the immutable digest | Manqoba | registry access, 3.9 |
| 5 | Approve and merge the digest-pinning GitOps PR | Nomhle | 3.6, step 4 |
| 6 | Create the Argo CD Application and perform a manual sync | Reitumetse | 3.9, step 5 |
| 7 | Confirm Vault agent injection and record redacted `/api/status` | Nomhle | 3.8, step 6 |
| 8 | Confirm Prometheus target and a Loki log reference | Reitumetse | monitoring stack |
| 9 | Fill and sign `evidence/wbs-3.10-record.md` | Nomhle, Manqoba, Reitumetse | steps 1–8 |

## Reproducing the local checks

```powershell
pwsh ./scripts/verify.ps1
```

```bash
./scripts/verify.sh
```

Both scripts are read-only with respect to the cluster. They require Python 3.12+
(kubectl and Trivy are optional and are reported as skipped when absent).

## Completion path

Task 3.10 can be marked complete only when every row in
[`../evidence/wbs-3.10-record.md`](../evidence/wbs-3.10-record.md) is filled from
project systems, the acceptance criteria in
[`acceptance-criteria.md`](acceptance-criteria.md) are evidenced, and the
accountable owners sign the completion decision.
