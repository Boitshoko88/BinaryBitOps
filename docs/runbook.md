# Runbook â€” deploy and verify the WBS 3.10 demonstrator

All commands are examples. Use the approved cluster, registry, Vault mount and
identity. Never paste credentials into a terminal that records history, and never
commit generated secrets.

## 0. Preconditions

- [ ] `docs/dependency-gates.md` checks pass (3.2, 3.3, 3.6, 3.8, 3.9).
- [ ] An independent reviewer is available.
- [ ] The non-production context is selected: `kubectl config current-context`.
- [ ] You are on a compliant device and connected through OpenZiti.

Stop if the context is production.

## 1. Prepare namespace, image pull and GitOps credentials

The namespace is rendered by the overlay. Create it first if Argo CD is not
permitted to create namespaces:

```sh
kubectl apply -f deploy/base/namespace.yaml
```

Create the registry pull secret from the approved credential source (Vault or
the platform secret store). Example shape only:

```sh
kubectl -n binarybitops-demo create secret docker-registry ecr-pull-auth \
  --docker-server="$REGISTRY" \
  --docker-username=AWS \
  --docker-password="$(aws ecr get-login-password --region "$REGION")"
```

Create the GitOps token secret for the optional pin task:

```sh
kubectl -n binarybitops-ci create secret generic gitops-token \
  --from-literal=token="$GITOPS_TOKEN"
```

The token must be a fine-grained token limited to the GitOps repository with
contents:write. It must not be able to push to `main`.

## 2. Register and apply the pipeline (3.9 change)

Pipeline definitions belong in `hde-pipelines`; raise a PR there and apply only
after approval.

```sh
kubectl -n binarybitops-ci apply -f ci/workspace-pvc.yaml
kubectl -n binarybitops-ci apply -f ci/rbac.yaml
kubectl -n binarybitops-ci apply -f ci/tasks/
kubectl -n binarybitops-ci apply -f ci/pipeline.yaml
```

Create the registry push secret used by the publish task:

```sh
kubectl -n binarybitops-ci create secret generic ecr-push-auth \
  --from-file=.dockerconfigjson="$HOME/.docker/config.json" \
  --type=kubernetes.io/dockerconfigjson
```

## 3. Run the pipeline for the merged commit

Copy `ci/pipelinerun-demo.yaml`, set `revision` to the merged commit SHA, set
`image-tag` to the same SHA, and keep `update-gitops=false` for the first run.

```sh
kubectl create -f ci/pipelinerun-demo.yaml
tkn pipelinerun list -n binarybitops-ci
tkn pipelinerun logs -n binarybitops-ci -f <pipelinerun>
```

Expected results:

- `unit-tests` passed;
- `trivy-source` passed (no leaked secret, no HIGH/CRITICAL);
- `build-image` produced a tar;
- `scan-image` passed;
- `publish-image` recorded `sha256:...`.

Record the digest:

```sh
tkn pipelinerun describe <pipelinerun> -n binarybitops-ci -o yaml \
  | grep -A2 'image'
```

### Negative gate check (required evidence)

Run once against a branch with a synthetic HIGH finding and once with a
synthetic credential pattern. Confirm the pipeline stops before publish and the
task log names the gate. Use non-usable values and delete the branch afterwards.

## 4. Pin the digest through GitOps

Preferred: raise a PR that changes only
`deploy/overlays/nonprod/patch-image.yaml` to:

```yaml
image: 445137568300.dkr.ecr.eu-north-1.amazonaws.com/binarybitops-demo@sha256:<digest>
```

Alternative: rerun the pipeline with `update-gitops=true` to push a
`gitops/binarybitops-demo-*` branch, then raise the PR yourself. The task never
merges or pushes to `main`.

Verification before approval:

```sh
kubectl kustomize deploy/overlays/nonprod | grep 'image:'
# must contain @sha256: and no :0.1.0 tag
```

Merge only after an independent approval.

## 5. Apply Argo CD and sync manually

```sh
kubectl apply -f argocd/project.yaml
kubectl apply -f argocd/application.yaml
argocd app get binarybitops-demo
argocd app sync binarybitops-demo --revision <merged-gitops-commit>
argocd app wait binarybitops-demo --health
```

Record the sync revision, result and timestamp. No `kubectl apply` of the
workload is permitted; Argo CD is the only deployment actor.

## 6. Verify the runtime

```sh
kubectl -n binarybitops-demo get deploy,pods,svc,pdb,networkpolicy -o wide
kubectl -n binarybitops-demo rollout status deploy/binarybitops-demo

# Non-root, read-only root filesystem, capabilities dropped
kubectl -n binarybitops-demo get pod -l app.kubernetes.io/name=binarybitops-demo \
  -o jsonpath='{.items[0].spec.containers[0].securityContext}'

kubectl -n binarybitops-demo port-forward svc/binarybitops-demo 8080:80
```

Then, from another terminal:

```sh
curl -s http://127.0.0.1:8080/healthz
curl -s http://127.0.0.1:8080/version
curl -s http://127.0.0.1:8080/api/status
curl -s "http://127.0.0.1:8080/api/bitops?left=12&right=10"
curl -s http://127.0.0.1:8080/metrics | head -20
```

Confirm `/version` shows the merged commit, `/api/status` shows environment
`nonprod` and the correct scope statement, and the page shows the demonstrator
banner.

Vault check (only when 3.8 is integrated):

```sh
vault kv metadata get secret/hde/nonprod/binarybitops-demo
kubectl -n binarybitops-demo logs deploy/binarybitops-demo -c vault-agent-init
```

`/api/status` must show `"injected": true` while never showing the value.

Observability:

```sh
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
# query: up{namespace="binarybitops-demo"}
kubectl -n monitoring port-forward svc/loki-gateway 3100:80
# query LogQL: {namespace="binarybitops-demo"}
```

## 7. Capture evidence

Use `evidence/wbs-3.10-record.md` and save raw output under
`evidence/run-<date>/`:

```sh
tkn pipelinerun describe <pipelinerun> -n binarybitops-ci -o yaml > evidence/run-$(date +%F)/pipelinerun.yaml
tkn taskrun list -n binarybitops-ci > evidence/run-$(date +%F)/taskruns.txt
crane digest <repo>@sha256:<digest> > evidence/run-$(date +%F)/digest.txt
argocd app get binarybitops-demo -o yaml > evidence/run-$(date +%F)/argocd-app.yaml
kubectl -n binarybitops-demo get all,networkpolicy,pdb -o wide > evidence/run-$(date +%F)/k8s.txt
kubectl -n binarybitops-demo logs deploy/binarybitops-demo --tail=200 > evidence/run-$(date +%F)/logs.txt
```

The report must not contain secret values. Redact registry tokens, Vault tokens
and ARN account details if policy requires.

## 8. Rollback

```sh
argocd app history binarybitops-demo
argocd app rollback binarybitops-demo <previous-id>
```

Or revert the GitOps PR and sync. Rollback does not touch Nexus or Truehost.

## 9. Cleanup after evidence capture

```sh
argocd app delete binarybitops-demo --cascade
kubectl delete namespace binarybitops-demo
```

Keep the pipeline and tests in place for the Phase 3 re-run; delete only the demo
runtime unless the owner wants it retained.

## 10. Troubleshooting

| Symptom | Check |
| --- | --- |
| `ImagePullBackOff` | `ecr-pull-auth` exists in the namespace; node role/registry policy allows pull |
| Pod rejected by Pod Security | Namespace labels still `restricted`; container not privileged; seccomp/RuntimeDefault set |
| `0/1 Ready`, `/healthz` healthy | Readiness depends on `REQUIRE_VAULT_INJECTION`; inspect `/api/status` and Vault agent logs |
| Argo CD `OutOfSync` on image | Digest PR merged but app revision not updated; sync the merged commit |
| Pipeline cannot resolve task | `ci/tasks/` applied to the PipelineRun namespace |
| Trivy fails without findings shown | Re-run locally with `trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL .` |
| `permission denied` writing workspace | PVC ownership; CI tasks run as root by design (see security exceptions) |
