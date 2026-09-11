# Example: First Issue To PR Flow

Status: Orientation
Issue: #3238

This example shows a conservative CDB docs-slice delivery path. Adjust paths,
issue numbers, validation, and closure wording to the actual task.

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

## PR-Flow v1

This example now rehearses a routed **Issue-Slice**, not an automatic
Issue→own-PR→merge chain. Before creating a Branch, Worktree or PR, run
`cdb-pr-router`. Reuse the selected compatible PR. A normal rehearsal ends
`DONE_SLICE_ADDED_TO_BATCH_PR` after targeted Validation and handoff; the later
merge section applies only when the PR is explicitly frozen as
`merge_candidate`.

## 1. Read The Issue And Canon First

Start with the issue, but do not trust issue prose alone.

Required shape:

1. Resolve the bootloader: `AGENTS.md` -> `agents/AGENTS.md` -> full Read Order.
2. Read `CDB_AGENT_POLICY.md` section 4 before write-zone work.
3. Read `docs/runbooks/CONTROL_REGISTER.md`, `CURRENT_STATUS.md`, and
   `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` as separate status
   surfaces.
4. Pull GitHub live state for the target issue, related issues, and open PRs.
5. Run `python -m tools.pr_routing route --issue <ISSUE>` and record the
   target PR/branch, lane, validation profile and lock state.

Governance reminders:

- GitHub live comes before ledger state.
- `CURRENT_STATUS.md` is a ledger, not live truth.
- Board stage `trade-capable` is not Live-Go.
- LR bleibt NO-GO.

## 2. Verify The Clean Start Surface

Example command shape:

```bash
git fetch origin --prune
git status -sb
git rev-parse HEAD
git rev-parse origin/main
git branch --show-current
gh issue view <issue> --json number,title,state,labels,body,comments
gh pr list --state open --limit 20
```

Stop if the base cannot be verified, the Issue is closed, the router returns
`HOLD_*`, or scope drifts into GUI,
runtime, Docker, trading, live, DB write, memory write, or LR changes.

## 3. Route, Change, And Dual-Lock

Run the router before selecting any work surface:

```powershell
python -m tools.pr_routing route --issue <issue> --agent <agent-id>
```

Reuse `target_pr` when routed to an existing Batch-PR. Only a create decision
permits a new branch. Before a new PR, reserve the Issue:

```text
LOCK_RESERVATION: agent=<agent-id> issue=#<issue> batch_pr=pending ts=<ISO8601> mode=batch-slice
```

After Draft-PR creation, set the identical lock on Issue and PR:

```text
LOCK: agent=<agent-id> issue=#<issue> batch_pr=#<pr> ts=<ISO8601> mode=batch-slice
```

Until both comments match live, `PARTIAL_LOCK` blocks all further writes.
Make the smallest docs change that satisfies the issue. Avoid opportunistic
cleanup in adjacent docs unless the issue explicitly asks for it.

## 4. Validate Locally

Use the validation required by the issue. For docs-only slices this often means:

```bash
git diff --check
rg -n "Live-Go|Echtgeld-Go|LR bleibt NO-GO|Docs/UI sind Orientierung" docs/<scope>
ruff check .
```

Run the repo's agreed sensitive-term scan for the changed docs path as a
separate validation step, and investigate any hit before publishing.

If a validation failure is caused by known unrelated untracked files, document it
as scope-fremd and do not fix it inside the issue unless explicitly instructed.

## 5. Commit, Push, And Slice Handoff

Use a narrow commit message:

```bash
git add docs/<scope>
git commit -m "docs(onboarding): add visual developer start pack"
git push <assigned-remote> <assigned-branch>
```

Update the PR ledger and Issue with PR, Commit, targeted Validation and
Restunsicherheit. Finish the normal Session as
`DONE_SLICE_ADDED_TO_BATCH_PR`.

## 6. Final Merge Candidate (separate flow)

Only after a Merge Trigger freezes the PR as `merge_candidate`:

1. Hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` + `policy-gate`
   SUCCESS live on the exact PR head SHA.
2. Combined diff remains in scope; Full Fast-CI is bound to Head and Base.
3. No new stop condition appeared in comments or checks.
4. No live, runtime, Docker, trading, DB write, memory write, or LR change was
   introduced.
5. Session can perform regular squash merge (capability gate). Hosted Actions
   red due to billing/lock is not automatically a merge blocker.

Use squash merge when the capability gate is proven:

```bash
gh pr merge <pr-number> --squash --delete-branch
```

If the session lacks publisher/merge rights: leave the PR open and report
`DONE_PR_OPEN_MERGE_HANDOFF`. Never use `--admin` as a bypass. Do not
re-push a remote branch deleted after squash merge.

## 7. Comment And Close

After a **live-verified final merge** (`DONE_MERGED_CLOSED`), comment on the target
issue with the PR link, commit, validation, and scope boundary. Close the
issue only when the merged PR satisfies the issue acceptance.

If the issue is part of a parent chain, add a short parent status comment with
the next recommended slice.
