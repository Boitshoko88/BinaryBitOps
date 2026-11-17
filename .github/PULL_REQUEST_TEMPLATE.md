# Pull request

## Task

WBS 3.10 — Create and deliver the Binary Bit Ops demonstrator (Phase 3, HDE).

## Scope boundary

<!-- This must remain true for every change in this repository. -->
- [ ] This change is a demonstrator workload only.
- [ ] It does not contain Binary Bit Ops/Nexus application code, data or credentials.
- [ ] It does not connect to, migrate or modify the Truehost PHP/MySQL deployment.
- [ ] No developer workspace access was enabled before the 3.3–3.5 gates passed.

## What changed

<!-- One or two sentences per item, with paths. -->

## Verification evidence

- [ ] `python -m unittest discover -s tests -t . -v` passes locally.
- [ ] `kubectl kustomize deploy/overlays/nonprod` renders without error.
- [ ] Trivy source scan passes (no leaked secrets, no HIGH/CRITICAL).
- [ ] Container smoke test passes (`/healthz`, `/api/bitops`, `/metrics`).
- [ ] Image is pinned by digest for GitOps (not a mutable tag).
- [ ] No secret, token, kubeconfig or real hostname is added to the repository.

Commands and output summary:

```text
<paste the relevant output or link to evidence>
```

## Risk and rollback

- Blast radius:
- Rollback: `argo cd app rollback binarybitops-demo <revision>` or revert this PR.

## Reviewer independence

- [ ] Reviewer is not the author and has not pair-authored this change.
- [ ] Reviewer confirmed the non-migration scope statement above.
