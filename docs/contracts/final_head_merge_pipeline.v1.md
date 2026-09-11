# CDB Final-Head Merge Pipeline v1

Status: Canonical
Issue: `#4411`
Related: `config/governance/pr-acceptance-policy.v1.yaml`,
`docs/runbooks/merge_policy_ci_gate.md`,
`docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md`,
`docs/contracts/agent_approval/CDB_PR_APPROVAL_CONTEXT_V1.md`

## Purpose

Define a single ownership matrix for the Final-Head path after
`MERGE_CANDIDATE`. No parallel merge authorities remain.

## Stable role IDs vs Cursor display names

| Stable role id | Cursor display name | Authority |
|---|---|---|
| `cdb_final_head_pr_approval_gate` | PR Reviewer | GitHub `APPROVE` only |
| `cdb_final_head_merge_executor` | Merge Agent | Regular merge only |

Display names are UI labels. Governance, contracts, and skills MUST bind
behavior to the stable role ids.

## Canonical flow

| Step | Role | Action | Merge authority |
|---|---|---|---|
| M1 | delivery | Issue slice delivered to routed PR | false |
| M2 | acceptance | Integration Wiring Audit | false |
| M3 | acceptance | Gap Classification | false |
| M4 | acceptance | Completeness → `MERGE_CANDIDATE` | false |
| M5 | `cdb-batch-merge-conductor` | Freeze, integrate main, bind final head/base, Final Validation, verify hosted Required Checks (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`) → `FINAL_HEAD_READY_FOR_APPROVAL` | false |
| M6 | `cdb_final_head_pr_approval_gate` | `APPROVE` bound to exact final `HEAD_SHA` | false |
| M7 | `cdb_final_head_merge_executor` | Regular merge after re-verify | true (only this role) |
| M8 | `cdb-session-close` | Verify MERGED, issue close eligibility, safe cleanup | false |

## Hard rules

Exactly one canonical final merge executor exists:
`cdb_final_head_merge_executor`.

1. `MERGE_CANDIDATE` alone never authorizes merge or approval.
2. Conductor must not approve, merge, or close issues.
3. PR Reviewer must not merge or modify code.
4. Merge Agent must not approve or modify code.
5. Approval is invalid when HEAD changes, a new commit lands, or relevant Base
   drift occurs.
6. Required contexts are the hosted GitHub Checks `ci (Unit/Integration + Lint
   gesammelt)` and `policy-gate` on the exact final head (no hardcoded
   `app_id`; hosted GitHub Actions App). Same-named Commit Status is not
   sufficient.
7. Cloud Reviewer/Merger are repo-only by design; they must not require local
   `cdb_context` or fabricate DB evidence.
8. `--admin` is never a bypass.
9. Delivery/implementation sessions do not merge by default.
10. Session Close verifies live delivery after the Merge Agent executed merge;
    it does not require the implementation session to have merged.

## Conductor success handoff

```text
decision: FINAL_HEAD_READY_FOR_APPROVAL
next_role: cdb_final_head_pr_approval_gate
```

## Approval mutation contract (PR Reviewer)

Required fields in the approval evidence / review body:

- `DECISION: APPROVE`
- `RISK: LOW`
- `HEAD_SHA: <exact-final-head>`
- `COMPLETENESS_VERDICT: MERGE_CANDIDATE`
- `BLOCKERS: NONE`
- `REQUIRED_NEXT_ACTION: HANDOFF_TO_MERGE_AGENT`

## Merge Agent re-verify

Before regular merge command
`gh pr merge <PR> --squash --delete-branch`:

- approval identity and approval `HEAD_SHA`
- current `HEAD_SHA` equals approval binding
- base/drift gates
- hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` and
  `policy-gate` SUCCESS on the exact final head
- reviews / mergeability / branch protection
- loop guard: HEAD change or stale approval → re-request Reviewer, do not merge

## Relationship to `cdb.pr_approval_context.v1`

The read-only recommendation envelope
(`APPROVE_RECOMMENDED` / …) remains a deterministic context builder. It does
not merge and does not publish CI. The Cloud PR Reviewer may consume that
context, but the governance mutation is a GitHub review `APPROVE` bound to the
exact final head, not the recommendation enum alone.
