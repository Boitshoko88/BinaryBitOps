# Pull request title

feat(demo): deliver WBS 3.10 Binary Bit Ops HDE demonstrator

# Pull request body

## Task

WBS 3.10 — Create and deliver the Binary Bit Ops demonstrator (Phase 3, HDE).
Dependency: 3.6 started; 3.9 required for deployment.

## Scope boundary

This is a demonstrator workload only. It contains no Binary Bit Ops/Nexus code,
data or credentials, does not connect to the Truehost PHP/MySQL database, and
does not authorise a migration of the live application. See
`docs/non-migration-attestation.md`.

## What changed

- Added a dependency-free Python 3.12 HTTP demonstrator with liveness,
  readiness, version, status, metrics and 16-bit bitwise endpoints.
- Added unit, HTTP, secret-redaction, build-metadata and manifest security tests.
- Added a non-root container image with read-only root filesystem support,
  OCI labels and a health check.
- Added restricted Kubernetes manifests: namespace PSA `restricted`,
  PodDisruptionBudget, default-deny NetworkPolicy, probes, resources and a
  Prometheus ServiceMonitor.
- Added a Tekton pipeline: tests → Trivy source → build → Trivy image →
  publish → optional digest-pinned GitOps branch. No direct deployment.
- Added a restricted Argo CD project and manual-sync application.
- Added Vault read-only policy, Kubernetes auth role setup and Agent Injector
  template; the app exposes only injection status, never values.
- Added delivery plan, acceptance criteria, dependency gates, runbook, security
  exceptions, evidence record and non-migration attestation.
- Added PR checks for tests, manifest rendering, schema validation, filesystem
  and image Trivy scans, and a container smoke test.

## Verification

- `python -m unittest discover -s tests -t . -v`
- `kubectl kustomize deploy/overlays/nonprod`
- `pwsh -File scripts/verify.ps1` (or `sh scripts/verify.sh`)
- Trivy filesystem and image scans

Evidence: `docs/task-3.10-status.md`, the local record from
`scripts/verify.ps1`, and the "PR check" run attached to this pull request.

## Out of scope / not yet evidenced

- HDE Tekton run, registry publication and Argo CD sync require 3.9 access and
  are recorded separately in `evidence/wbs-3.10-record.md`.
- Vault proof requires the 3.8 injector/role to be available.
- Exact current state, skips and outstanding owners: `docs/task-3.10-status.md`.
  Task 3.10 is not complete until that record is signed.

## Risk and rollback

- Blast radius: non-production `binarybitops-demo` namespace only.
- Rollback: `argocd app rollback binarybitops-demo <id>` or revert this PR; no
  Nexus or Truehost impact.

## Reviewer checklist

- [ ] Independent reviewer (not the author).
- [ ] Scope boundary confirmed.
- [ ] No secret, token, kubeconfig or real hostname added.
- [ ] Image is digest-pinned for deployment; mutable tags are not used.
- [ ] Tests and scans pass.
