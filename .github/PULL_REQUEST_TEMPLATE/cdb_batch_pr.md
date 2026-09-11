<!-- cdb-batch-pr:v1
policy_id: cdb-pr-routing-v1
batch_key: <stable-key>
lane: <lane>
base_branch: main
validation_profile: <profile>
merge_mode: batch
steward_state: accepting_slices
objective_key: <objective>
planned_issues: #<N>
contract_keys: <sorted-keys-or-none>
risk_flags: <sorted-flags-or-none>
-->

## Kurzbefund

<!-- Was ist das gemeinsame, fachlich runde Batch-Ziel? -->

## CDB Batch Ledger

| Issue | Status | Commit | Targeted Validation | Risk Class | Restunsicherheit |
| --- | --- | --- | --- | --- | --- |
| #N | PLANNED | pending | pending | pending | pending |

## Final-Head-Evidence

- Final Head SHA: `pending`
- Integrated Base SHA: `pending`
- Full Fast-CI: `pending`
- Policy-Gate mirror: `pending`
- Hosted Required Checks exact SHA (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`): `pending`
- Blocking reviews: `pending`

## Guardrails

- Merge-Trigger ist keine Merge-Autorisierung.
- Kein Zwischenstands-Publish.
- Kein Admin-Merge ohne separate Human Authority.
- LR bleibt `NO-GO`.

Closes #N
