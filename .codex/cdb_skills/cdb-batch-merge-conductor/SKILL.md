<!--
Canonical Skill Source: docs/skills/cdb-batch-merge-conductor/SKILL.md
Surface: codex
Sync Status: mirrored-from-canon
Last Verified: 2026-08-08
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-batch-merge-conductor
description: >
  Final-Head Preparation Conductor for a MERGE_CANDIDATE PR. Freezes slices,
  integrates main, binds final head/base, delegates Final Validation, verifies
  hosted Required Checks (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`),
  and hands off FINAL_HEAD_READY_FOR_APPROVAL to cdb_final_head_pr_approval_gate.
  Does not approve or merge. Never --admin.
disable-model-invocation: true
---

# CDB Batch Merge Conductor

## Purpose

Orchestration skill of the PR-Acceptance Skill Family v1. Own freeze, main
integration, final head/base capture, delegation of final checks, and
required-status readiness for the Final-Head approval pipeline. Success ends at
`FINAL_HEAD_READY_FOR_APPROVAL` with handoff to
`cdb_final_head_pr_approval_gate` (Cursor display: PR Reviewer).

Policy: `config/governance/pr-acceptance-policy.v1.yaml` (`cdb-pr-acceptance-v1`)
Schema: `docs/contracts/pr_acceptance_skill_family.v1.schema.json`
Pipeline contract: `docs/contracts/final_head_merge_pipeline.v1.md`
Evidence marker: `<!-- cdb-pr-acceptance:v1 -->`

## Ownership

- Reihenfolge
- Freeze
- Main-Integration
- Final-Head- und Base-Erfassung
- Delegation der finalen Prüfungen
- Required-Status-Verifikation (hosted Checks `ci (Unit/Integration + Lint
  gesammelt)` + `policy-gate`)
- Handoff `FINAL_HEAD_READY_FOR_APPROVAL` → `cdb_final_head_pr_approval_gate`
- Deferred closure ledger rows for later `cdb-session-close` (after Merge Agent)

## Does not own

- GitHub APPROVE (`cdb_final_head_pr_approval_gate` only)
- Regular merge execution (`cdb_final_head_merge_executor` only; that role runs
  `gh pr merge --squash --delete-branch`)
- Issue closure
- eigene CI-Implementierung
- eigene Review-Taxonomie
- eigene Routing-Engine
- eigene Gap-Klassifikation
- eigene Evidence-Taxonomie

## Authorization contract

- No separate Human-/Merge-GO micro-approval field after an authorized Conductor
  phase.
- No field `human_merge_authorization`.
- No status `BLOCKED_HUMAN_AUTHORITY`.
- Conductor readiness is gate-based against
  `docs/runbooks/merge_policy_ci_gate.md` for Final-Head / hosted Required
  Check readiness only — not merge execution authority.
- Missing publisher/auth capability before handoff →
  `DONE_PR_OPEN_MERGE_HANDOFF` (Final Head not ready), never `--admin`.
- After successful Final-Head readiness, stop. Do not approve. Do not merge.

## Phases

1. `FREEZE` — set acceptance lifecycle `FROZEN`; no further slices; reject new slices
2. `MAIN_INTEGRATION` — integrate current `origin/main`; rebind head/base
3. `FINAL_VALIDATION` — delegate Full Fast-CI, policy-gate mirror, hosted
   Required Checks
4. `HANDOFF_APPROVAL` — emit `FINAL_HEAD_READY_FOR_APPROVAL` to
   `cdb_final_head_pr_approval_gate`
5. `HANDOFF_SESSION_CLOSE` — after Merge Agent live merge only, pass
   `SLICE_DELIVERED` ledger rows to `cdb-session-close`

Any conflict resolution, new commit, or semantic change after Completeness
invalidates the old Completeness bundle and forces a fresh
`cdb-pr-completeness-review` before continuing.

## Workflow

1. Read current `MERGE_CANDIDATE` acceptance bundle.
2. Verify live PR, reviews, locks, head, and base.
3. Verify task scope and Final-Head preparation capability.
4. Set acceptance state to `FROZEN`; reject new slices.
5. Integrate current main (`origin/main`).
6. Recapture final head and base SHAs.
7. On drift/semantic change: re-run Completeness Review.
8. Re-check combined diff and closure claims.
9. Delegate final validation path to existing skills (`cdb-ci-cd-guard`, etc.).
10. Run Full Fast-CI once on the exact final head.
11. Run local policy-gate mirror.
12. Publish or verify the hosted Required Checks
    (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`) on exactly that
    head.
13. Re-check head, base, reviews, and required hosted Check Runs immediately
    before handoff.
14. Set lifecycle to `FINAL_HEAD_READY_FOR_APPROVAL` and hand off to
    `cdb_final_head_pr_approval_gate`. Do not approve. Do not merge.
15. When Merge Agent has live-verified MERGED, hand only ledger rows with
    `SLICE_DELIVERED` to `cdb-session-close`.

## Block codes

- `BLOCKED_SCOPE_OR_REVIEW` → session status `HOLD_SCOPE_OR_REVIEW`
- `BLOCKED_HEAD_BASE_DRIFT` → session status `HOLD_MAIN_OR_HEAD_DRIFT`
- `BLOCKED_LOCAL_VALIDATION`
- `BLOCKED_REQUIRED_STATUS`
- `BLOCKED_AUTH_PUBLISHER`
- `BLOCKED_MERGE_METHOD` (observed merge-method conflict during readiness; Conductor still does not merge)
- `BLOCKED_ISSUE_CLOSEOUT`

Missing technical capability for Final-Head readiness maps to
`DONE_PR_OPEN_MERGE_HANDOFF`.

## Forbidden

- `--admin`
- Fake-Green
- stale slice evidence as final evidence
- approve or merge from this skill
- merge retry loops (merge is not owned here)
- closing undelivered issues
- reviving a remote branch after merge
- inventing `human_merge_authorization` or `BLOCKED_HUMAN_AUTHORITY`
- opening a post-merge `CURRENT_STATUS-only` / `ledger-only` Nachlauf-PR
  after squash-merge (Issue `#4218`); ledger/status lines belong
  **vor dem Freeze** in this PR or later in a `docs-governance` batch
- capability-based autonomous merge that bypasses
  PR Reviewer → Merge Agent

## Required envelope fields

Producer: `cdb-batch-merge-conductor`

Common envelope:

- `schema_version`: `cdb-pr-acceptance-skill-family/v1`
- `policy_id`: `cdb-pr-acceptance-v1`
- `subject.repository`, `subject.pr_number`
- `subject.head_sha` / `subject.base_sha` — 40 lowercase hex
- `observed_at` — RFC3339
- `run_status` — `COMPLETE` | `BLOCKED` | `INVALIDATED_BY_DRIFT`
- `lifecycle`, `decision`, `findings`, `evidence`, `limitations`, `handoff`
- `result.phase`
- `result.block_codes`
- `result.final_head_ready` (optional boolean)
- `result.success_decision` — `FINAL_HEAD_READY_FOR_APPROVAL` when ready
- `result.handoff_role` — `cdb_final_head_pr_approval_gate`
- `result.closure_eligible_issues` (optional issue numbers; close only after merge)

## Handoff

On Final-Head readiness:

```text
decision: FINAL_HEAD_READY_FOR_APPROVAL
next_role: cdb_final_head_pr_approval_gate
```

After Merge Agent live-verified merge, hand `SLICE_DELIVERED`
closure-eligible issues to `cdb-session-close`. Do not close undelivered ledger
rows. Do not close issues from the Conductor itself.
