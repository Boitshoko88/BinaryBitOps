# Security exceptions and compensating controls

Every exception is scoped to the non-production demonstrator, has an owner and a
review date, and must be re-approved before reuse beyond Task 3.10.

| ID | Exception | Scope | Justification | Compensating control | Owner | Review |
| --- | --- | --- | --- | --- | --- | --- |
| EX-01 | Kaniko build pod runs as root | `demo-build-image` Task only, isolated CI namespace | Kaniko must write its own filesystem and build layers; there is no daemonless non-root equivalent in the approved toolchain | No host mounts, no privileged flag, `allowPrivilegeEscalation: false`, RuntimeDefault seccomp, short-lived pod, dedicated namespace, no cluster credentials | Mahlatse | Before production reuse |
| EX-02 | Git clone and GitOps pin tasks run as root | `demo-git-clone`, `demo-pin-gitops` | PVC ownership is root by default; changing ownership would require an init step and additional privilege | No capabilities, no privilege escalation, credentials via mounted secret/askpass, no Kube API token | Nkosinathi | Before production reuse |
| EX-03 | GitOps overlay ships a tag before the first pin | `deploy/overlays/nonprod/patch-image.yaml` | The digest does not exist until the pipeline publishes the image | Argo CD sync is manual; approval checks `@sha256:`; the pin task rewrites the single image line; tag is never used for a sync | Reitumetse | Until first pinned sync |
| EX-04 | ServiceMonitor CRD may be absent | Observability overlay | ServiceMonitor is required for Prometheus integration but the CRD is cluster-owned | PR check uses `kubeconform -ignore-missing-schemas`; apply only after the monitoring stack exists; removal does not affect the workload | Nqubeko | With monitoring stack |
| EX-05 | Demo has no HPA or multi-zone spread guarantee | `deploy/base` | Deliberately small non-production workload; capacity testing is out of scope | Two replicas, PodDisruptionBudget, topology spread with `ScheduleAnyway`, resource limits | Nomhle | At decommission |
| EX-06 | Registry pull secret is referenced but not stored in Git | Overlay patch | Credentials must not be committed | Secret is created by the platform from the approved store; Argo CD shows the missing secret instead of silently pulling from an unapproved registry | Elvis | Continuous |

## Accepted-by

| Role | Name | Date | Reference |
| --- | --- | --- | --- |
| Security lead | Elvis | | |
| Platform lead | Kagiso | | |
| Work package lead | Nomhle | | |

Unapproved exceptions block the 3.10 completion decision.
