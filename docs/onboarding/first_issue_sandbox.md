# First-Issue Sandbox

Status: docs-only guided rehearsal
Issue: #3251
Parent: #3246

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

## Purpose / What this sandbox is

This sandbox is a safe, minimal rehearsal path for a new developer or agent who
wants to walk through CDB's PR Router, Slice Validation, Dual-Lock and handoff
workflow without touching runtime, Docker, trading, LR, or
productive DB surfaces.

After completing this rehearsal you will have:

- executed or simulated `cdb-pr-router` before creating a work surface,
- reused a compatible PR or recorded a justified create decision,
- made the smallest docs-only change,
- run targeted Slice Validation,
- practiced the Issue-/PR-Level-Lock pair,
- updated the Batch Ledger and Issue handoff,
- understood why Full Fast-CI and `cdb-local-ci` belong only to a frozen final
  merge head, and
- left the Issue open until an actual verified merge.

Sections describing merge criteria are a separate merge-candidate rehearsal;
they are not the default end of the first Issue-Slice.

The sandbox expects a **tiny docs-only issue**. If no real issue is available,
simulate one: add a sentence to `docs/onboarding/cdb_glossary.md` or
`docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`. Choose the smallest,
safest change that satisfies the rehearsal.

## Safety Boundaries

| Boundary | Rule |
|----------|------|
| **LR** | NO-GO. Never touched by this sandbox. |
| **Live-Go** | Not permitted. |
| **Echtgeld-Go** | Not permitted. |
| **Board stage** | `trade-capable` is Board context, not Live-Go. |
| **Runtime (BLUE+RED)** | No changes. |
| **Docker / Compose** | No changes. |
| **Trading / Strategy / Risk / Execution** | No changes. |
| **Productive DB writes** | No changes. |
| **MCP mutations** | No changes. |
| **SurrealDB writes** | No changes. |
| **Secrets** | No output, no display, no value in any file. |
| **Legacy pack decision** | Outside scope; handled by #3252. |
| **Scope growth** | If the diff drifts outside docs/onboarding or narrow discovery updates, stop. |

## Before starting: Bootloader and live truth

Read these surfaces before you branch. Do not treat any of them as optional.

### For humans

1. `README.md` — repo landing page and safety boundary.
2. `docs/index.md` — shortest active docs landing page.
3. `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md` — visual map for developers.
4. `docs/onboarding/cdb_glossary.md` — terminology anchor for CDB-specific terms.
5. `docs/onboarding/fresh_clone_rehearsal.md` — read-only fresh-clone path.

### For agents

1. `AGENTS.md` → `agents/AGENTS.md` (bootloader + full Read Order).
2. `knowledge/governance/CDB_AGENT_POLICY.md` section 4 (LOCK rules).
3. `docs/runbooks/CONTROL_REGISTER.md` (Board stage and operating focus).
4. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (LR SSOT, NO-GO).
5. `agents/OPEN_CODE_AGENTS.md` (Brain Evidence Gate and gh-only writes).
6. If scope includes Strategy, Runtime, Module, Service, Contract, Context,
   SurrealDB, MCP tools, DB-backed Memory, or Evidence: emit Brain Evidence
   block before the plan.

### Live truth check (both)

```bash
git fetch origin --prune
git status -sb
git rev-parse HEAD
git rev-parse origin/main
git branch --show-current
gh issue view <issue> --json number,title,state,labels,body,comments
gh pr list --state open --limit 20
```

Stop if:
- you are not on `main`,
- local `main` differs from `origin/main`,
- the target issue is already closed,
- a matching open PR already exists with an active `LOCK:` comment by another writer,
- or scope drifts into runtime, Docker, trading, DB write, memory write, or LR changes.

**Remember**: `CURRENT_STATUS.md` is a ledger, not live truth. GitHub live + repo
live evidence wins.

## Pick or simulate a tiny docs-only issue

1. Verify the issue on GitHub live (`gh issue view`). Confirm it is OPEN and the
   scope is docs-only.
2. Read the full issue body and any linked parent/child comments.
3. If no suitable docs-only issue exists, simulate one:
   - Add a sentence to `docs/onboarding/cdb_glossary.md` that explains a term
     already used in onboarding docs.
   - Or add a clarifier to `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`.
   - Keep the change to 1-3 lines.

## Create a feature branch or worktree

Always branch from current `main`.

```bash
git switch -c docs/<short-scope>-<issue>
```

Example: `docs/first-issue-sandbox-3251` or `docs/glossary-clarify-XXXX`.

If you prefer a dedicated worktree on the local Windows operator host, use the
governed entry (canonical root `Y:\Worktrees`):

```powershell
python -m tools.worktrees create `
  --repository Claire_de_Binare `
  --name cdb-sandbox-<issue> `
  --branch docs/sandbox-<issue> `
  --execute
cd Y:\Worktrees\Claire_de_Binare\cdb-sandbox-<issue>
```

Do **not** create new additional worktrees on `C:` or `D:`. The main checkout
may remain on `D:`. See `docs/runbooks/windows_worktree_y_root.md`.
On Linux/CI, Windows drive policy does not apply.

Verify:

```bash
git status -sb
git branch --show-current
```

## Make a minimal docs-only change

Rules:
- Only edit files under `docs/onboarding/` or the discovery surfaces named in
  the issue.
- Never touch `infrastructure/`, `services/`, `core/`, `knowledge/governance/`,
  or `.github/workflows/`.
- Do not output secrets.
- Do not change `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- Do not change `docs/runbooks/CONTROL_REGISTER.md`.
- No opportunistic cleanup outside the issue scope.

## Run targeted validation

Validation depends on the change. For docs-only slices:

```bash
# Whitespace sanity
git diff --check

# Link integrity (if new links were added)
python -m tools.validate_onboarding_docs

# Lint (CI-required)
ruff check .

# Onboarding doctor
python -m tools.onboarding_doctor
```

If a validation failure is caused by known unrelated untracked files (e.g.
`.opencode/plans/`, `docs/decisions/`), document it as scope-fremd and do not
fix it inside the issue.

For agent-specific validation, also run:

```bash
python -m tools.onboarding_tour --role agent
python -m tools.onboarding_tour --role developer
```

## Prepare routed PR body

For a Batch-PR start from
`.github/PULL_REQUEST_TEMPLATE/cdb_batch_pr.md`; Dedicated PRs retain the
standard PR template.

Required sections in every PR body:

| Section | Content |
|---------|---------|
| Summary | What changed and why it is scoped to this issue. |
| Changed Files | List of paths with purpose. |
| Validation | Commands run and their results. |
| Scope Boundary | Docs/onboarding only; no runtime/Docker/trading/LR/DB changes. |
| Safety/LR | LR bleibt NO-GO. Board stage `trade-capable` is not Live-Go. No Echtgeld-Go. |
| Issue Links | Ledger row plus exactly one `Closes #<issue>` per delivered Issue. |
| Brain Evidence | Required when scope touches module/service/contract/context surfaces. |

## Reserve and post the Dual-Lock

Before a new PR, reserve the Issue:

```text
LOCK_RESERVATION: agent=<agent-id> issue=#<issue> batch_pr=pending ts=<ISO8601> mode=batch-slice
```

After Draft-PR creation, post the identical lock on Issue and PR:

```text
LOCK: agent=<agent-id> issue=#<issue> batch_pr=#<pr> ts=<ISO8601> mode=batch-slice
```

**Rules**:

- Until both live comments match, `PARTIAL_LOCK` blocks further writes.
- If a `LOCK:` from another agent already exists on the PR: **HARD STOP**.
  Do not push, comment, or mutate.
- Never auto-take over a stale or malformed lock.
- Reuse the PR selected by `cdb-pr-router`; never create a duplicate.

**Post via `gh` CLI**:

```bash
gh issue comment <issue> --body "LOCK: agent=<agent-id> issue=#<issue> batch_pr=#<pr> ts=<ISO8601> mode=batch-slice"
gh pr comment <pr> --body "LOCK: agent=<agent-id> issue=#<issue> batch_pr=#<pr> ts=<ISO8601> mode=batch-slice"
```

All GitHub writes (PR create, comment, merge, issue comment, labels) go through
`gh` CLI only. No MCP/GitHub API/connector writes.

## Slice Handoff

The normal sandbox result uses targeted tests, affected lint/format and
`git diff --check`, updates the Ledger and Issue, and ends
`DONE_SLICE_ADDED_TO_BATCH_PR`. It does not publish a status, merge, or close
the Issue.

## Check required status (final merge-candidate gate)

SSOT: [`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md).
Verify live with `gh api` — do not hardcode elsewhere.

| Context | Required? | What it validates |
|---------|-----------|-------------------|
| `ci (Unit/Integration + Lint gesammelt)` | **Yes** (hosted Check Run, exact PR head) | Full Fast-CI published for this head via `ci.yml` |
| `policy-gate` | **Yes** (hosted Check Run, exact PR head) | PR scope/policy safety gate |
| `cdb-local-ci` | Optional (local preflight) | Local Fast-CI developer preflight; not merge-required since #4540 |

Only after the PR is frozen as `merge_candidate`, use the final publish path:

```powershell
pwsh -File ci/scripts/run_all.ps1 -Profile fast
pwsh -File ci/scripts/publish_status.ps1 -Command publish `
  -EvidenceDir ci/artifacts/<run_id> -StatusContext cdb-local-ci -PrNumber <n>
```

If `cdb-local-ci` is missing/red and the session cannot publish: fix inside
scope if possible, otherwise stop with `DONE_PR_OPEN_MERGE_HANDOFF`.

## Merge criteria (capability-based)

Normal squash merge is allowed when **all** capability gates are proven
(see merge-policy runbook). Not agent-type-based. Checklist:

1. PR is frozen as `merge_candidate`.
2. Hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` + `policy-gate`
   SUCCESS live on the exact PR head SHA.
3. Full local Fast-CI PASS bound to Head and integrated Base SHA.
4. Diff stays inside the approved scope (docs/onboarding + narrow discovery).
5. No conflicting lock; no blocking reviews / `CHANGES_REQUESTED`.
6. PR is not draft / HOLD / BLOCKED; mergeable.
7. No secrets in the diff; no LR/Live/Echtgeld boundary touched.
8. Session can perform regular squash merge (no `--admin` bypass).

If gates are met and the task allows autonomous merge:

```bash
gh pr merge <pr-number> --squash --delete-branch
```

If the session lacks publisher/merge capability: leave the PR open and report
`DONE_PR_OPEN_MERGE_HANDOFF` (do not loop, do not `--admin`).

After a successful merge, verify and **do not re-push** the deleted remote branch:

```bash
git fetch origin --prune
git rev-parse origin/main
gh pr view <pr-number> --json state,mergedAt,mergeCommit
```

## Close issue / parent comment pattern

### Close the target issue

After merge, comment on the target issue with:
- PR link and merge SHA,
- what was delivered,
- validation evidence,
- scope boundary confirmation,
- Brain Evidence (if applicable).

Then close the issue:

```bash
gh issue close <issue-number>
```

### Parent progress comment

If the issue is a child of a parent issue, add a progress comment on the parent:

```text
## Progress Update — #<child> complete

Delivered via PR #<pr> (<merge-sha-short>):
- <what changed>

Status:
- #<child> complete and merged.
- Parent #<parent> remains open for remaining children: #<next-child>.
```

Keep the parent open unless all children are done.

## Human developer path

1. Read the [CDB Glossary](cdb_glossary.md) first.
2. Follow [Fresh-Clone Rehearsal](fresh_clone_rehearsal.md) if this is your
   first checkout.
3. Pick a tiny docs-only issue or simulate one.
4. Follow this sandbox step by step. Do not skip the bootloader reads.
5. All commands in this sandbox are examples; adjust paths, issue numbers,
   and branch names to your actual task.
6. If you get stuck: stop. Re-read `docs/index.md` or ask on the issue.

## Agent path

1. Resolve the full bootloader: `AGENTS.md` → `agents/AGENTS.md` → full Read
   Order from `agents/AGENTS.md`.
2. If the scope includes Strategy, Runtime, Module, Service, Contract, Context,
   SurrealDB, MCP tools, DB-backed Memory, or Evidence: output the
   **Brain Evidence** block before the plan (see `agents/AGENTS.md` § Brain
   Evidence Gate and `agents/OPEN_CODE_AGENTS.md`).
3. Verify GitHub live state: target issue, related issues, open PRs.
   GitHub live wins over ledger state.
4. Follow this sandbox step by step. Do not skip the PR LOCK.
5. All GitHub writes go through `gh` CLI only.
6. If a matching open PR already exists with a `LOCK:` from another agent:
   **HARD STOP**. Do not push, comment, or mutate.
7. Treat `CURRENT_STATUS.md` as a ledger, not live truth.
8. `trade-capable` (Board stage) is never Live-Go.
9. LR remains NO-GO.

For more detail on the first issue-to-PR flow pattern, see the companion example
at [`examples/first_issue_to_pr_flow.md`](examples/first_issue_to_pr_flow.md).

## Common HOLD conditions

| Condition | Action |
|-----------|--------|
| Not on `main` at start | Switch to `main` and pull. Start over. |
| `main` diverged from `origin/main` | `git fetch origin --prune && git reset --hard origin/main` |
| Issue already closed | Pick a different open issue. |
| Matching open PR with active `LOCK:` by another writer | HARD STOP. Wait or ask. |
| Required hosted Check (`ci (Unit/Integration + Lint gesammelt)` / `policy-gate`) missing/red on a frozen final merge candidate | Verify via `gh api` that both were run on the exact final head (`required-checks-audit.yml` can verify), fix real code/governance issues, or hand off with `DONE_PR_OPEN_MERGE_HANDOFF`. Intermediate slices do not run full CI. |
| Hosted Actions `ci`/`policy-gate` red | Fix real code/governance issues; billing-red ≠ code failure. |
| Diff grows into runtime/Docker/trading/LR/DB scope | Revert the out-of-scope change. Commit only docs. |
| Secret value appears in diff | Revert immediately. Do not push. |
| `CURRENT_STATUS.md` treated as live truth in the change | Correct to ledger/ledger wording. |
| Opportunistic cleanup of unrelated files | Revert those changes. Keep the diff narrow. |

## What this sandbox must never touch

- `infrastructure/compose/`, `infrastructure/database/`, `infrastructure/scripts/`
- `services/`, `core/`
- `.github/workflows/`
- `knowledge/governance/`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `CURRENT_STATUS.md` (except as read-only evidence)
- `docs/archive/`
- Secret files, `.env`, `SECRETS_PATH`
- Any file outside `docs/onboarding/`, `tools/`, and `tests/` that was not
  explicitly named in the issue scope

## Sources

- [`cdb_glossary.md`](cdb_glossary.md) — PR LOCK, Required Checks, CI, policy-gate
- [`fresh_clone_rehearsal.md`](fresh_clone_rehearsal.md) — read-only fresh-clone path
- [`examples/first_issue_to_pr_flow.md`](examples/first_issue_to_pr_flow.md) — companion example flow
- [`templates/pr_body_template.md`](templates/pr_body_template.md) — PR body template
- [`../index.md`](../index.md) — docs landing page
- [`DEVELOPER_VISUAL_START_HERE.md`](DEVELOPER_VISUAL_START_HERE.md) — visual developer start
- [`../../DEVELOPER_ONBOARDING.md`](../../DEVELOPER_ONBOARDING.md) — developer onboarding guide
- [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) — contribution workflow and LOCK semantics
- [`../../knowledge/governance/CDB_AGENT_POLICY.md`](../../knowledge/governance/CDB_AGENT_POLICY.md) — agent policy, LOCK rules
- [`../../docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md) — Board stage
- [`../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) — LR SSOT
- [`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) — repo/engineering ledger
- [`../../agents/AGENTS.md`](../../agents/AGENTS.md) — agent bootloader and Read Order

## Safety / LR Reminder

- **LR remains NO-GO.**
- **Board stage `trade-capable` is not Live-Go.**
- **No Echtgeld-Go.**
- **Docs/UI are orientation, not authority.**
- **`CURRENT_STATUS.md` is a ledger, not GitHub live truth.**
- **GitHub live and repo live evidence wins over Brain, memory, or ledger claims.**
