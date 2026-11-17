# Non-migration attestation — WBS 3.10

## Statement

The Task 3.10 demonstrator is a delivery-path proof only. It does **not** migrate,
replace, wrap, proxy or reimplement the Binary Bit Ops/Nexus application.

Binary Bit Ops/Nexus remains the live PHP/MySQL application hosted on Truehost
cPanel, released through its existing controlled path, until a separate
migration proposal is approved through the project's change governance.

## Technical assertions

| Assertion | How it is verifiable |
| --- | --- |
| No Nexus application source is present | Repository tree contains only `binarybitops/`, tests, delivery manifests and documentation |
| No Nexus database is contacted | The workload has no database driver and opens no outbound connection; egress policy allows only DNS |
| No Nexus data or staff records are present | No fixtures, dumps or data files; the only records are the 16-bit calculation inputs |
| No production credentials are present | Trivy secret scan; tests assert secret values are never exposed; credentials come from Vault/managed secrets |
| No DNS, ingress or Truehost configuration is changed | Repository contains no DNS records, cPanel configuration or Truehost credentials |
| The workload runs in a separate namespace and repository path | `binarybitops-demo` namespace; separate `deploy/` and `ci/` assets |
| No developer workspace was enabled before gates 3.3–3.5 | Workspace enablement is outside this work package; gate evidence is held by 3.3–3.5 |
| Production migration is not authorised by this work | This attestation, the README scope boundary, the UI banner and the PR template checklist |

## Organisational assertions

1. No production change window, database backup or Truehost release is required
   for this demonstrator.
2. The demonstrator is not linked from Nexus, does not share its session or
   authentication trust, and is not presented to end users as a Nexus service.
3. Any future proposal to move Nexus to Kubernetes requires its own scope,
   architecture, data-migration, security and rollback approval. Task 3.10 does
   not constitute that approval.
4. The demo deployment is non-production and may be scaled to zero or removed
   after evidence capture without business impact.

## Sign-off

| Role | Name | Confirm statement | Date | Signature/reference |
| --- | --- | --- | --- | --- |
| Work package lead | Nomhle | ☐ | | |
| Delivery engineer | Manqoba | ☐ | | |
| Delivery engineer | Reitumetse | ☐ | | |
| Project manager | Lelo | ☐ | | |
| Architecture owner | Ayanda | ☐ | | |
| Business owner | Mr Kau | ☐ | | |

Sign-off is recorded in `evidence/wbs-3.10-record.md` with a link to the signed
copy. An unsigned attestation does not satisfy the work package exit criteria.
