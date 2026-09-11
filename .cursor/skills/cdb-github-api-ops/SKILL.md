<!--
Canonical Skill Source: docs/skills/cdb-github-api-ops/SKILL.md
Surface: cursor
Sync Status: mirrored-from-canon
Last Verified: 2026-08-08
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-github-api-ops
description: >
  GitHub API-aware agent routing for CDB. Teaches agents when to use GitHub
  API calls, which data to pull, which permissions matter, and when to stop.
  Covers Status Snapshot, API Opportunity Scan, CI/Checks Readout, PR Queue
  Radar, Issue Dedupe, ProjectV2 Reconciliation, Rate-Limit Awareness, and
  Permission Safety. Read-only by default; writes require separate approved
  scope. Does not replace gh-fix-ci or gh-address-comments but complements
  them with upstream API awareness.
disable-model-invocation: true
---

# CDB GitHub API Ops

Route GitHub API usage intelligently. Read broadly, write narrowly.

## Use this skill when

- the agent touches PRs, issues, CI checks, or ProjectV2 and needs live
  GitHub data beyond what `git` alone provides
- the agent should check whether a GitHub API call is the right approach
  before firing `gh api` blindly
- the agent needs a Status Snapshot of the repo, PR queue, or CI state
- the agent encounters repetitive manual GitHub actions that could be API calls
- the agent sees red checks and wants to understand the API-level picture
  before delegating to `gh-fix-ci`
- the agent considers creating an issue and should deduplicate first
- the agent works on Modusmono/CDB portfolio and needs multi-repo visibility
- ProjectV2 fields are relevant and `read:project` may be missing
- a write operation seems necessary and the agent must verify scope first

## Do NOT use this skill when

- CI is already failing and the task is purely fixing code (use `gh-fix-ci`)
- PR review comments need triage or replies (use `gh-address-comments`)
- the task is local git work with no GitHub interaction needed
- the task is repo settings, branch protection, or admin changes (separate
  scope, never automatic)

## Inputs

- Authenticated `gh` CLI
- Target repo (default: current repo)
- Optional: issue/PR numbers, branch names, ProjectV2 board IDs

## Workflow

### 1. Auth profile check

Before any API call, verify what the current auth profile can do:

```bash
gh auth status
```

Determine:

| Signal | Meaning |
|--------|---------|
| `repo` scope present | Issues, PRs, contents, actions readable |
| `read:org` scope present | Org membership readable |
| `workflow` scope present | Workflow runs readable |
| `read:project` scope missing | ProjectV2 NOT visible — known gap |
| fine-grained PAT in use | Checks API may be blocked; see limits below |

Record the auth profile in any output:

```text
auth_profile: gh-session | fine-grained-pat | classic-pat | github-app
evidence_sources: [list what was actually readable]
partial_visibility: [list what was blocked or incomplete]
```

### 2. Route to the right sub-operation

| Situation | Sub-operation | Primary API | Notes |
|-----------|---------------|-------------|-------|
| Need full repo status picture | Status Snapshot | GraphQL (issues, PRs, reviews, statusCheckRollup) + REST (Actions runs/jobs, commit statuses) | See `docs/github/UNIFIED_GITHUB_STATUS_SNAPSHOT.md` |
| Red checks on a PR | CI/Checks Readout | REST Actions runs/jobs + Checks | Delegate fix to `gh-fix-ci` after readout |
| Open PRs need triage view | PR Queue Radar | GraphQL (PRs + reviews + mergeState) | Complement `gh pr list` with deeper fields |
| About to create an issue | Issue Dedupe | REST search: `GET /search/issues?q=repo:...+<keywords>` | Always search before opening |
| Repetitive manual GitHub clicks | API Opportunity Scan | N/A (diagnostic) | Propose API automation, do not implement |
| Multi-repo portfolio view | Multi-Repo Snapshot | GraphQL per repo or `gh api` loop | Same snapshot logic, multiple repos |
| ProjectV2 fields needed | ProjectV2 Reconciliation | GraphQL ProjectV2 items | Requires `read:project`; mark as gap if missing |
| Rate limit approaching | Rate-Limit Awareness | REST `/rate_limit` | Check before batch operations |
| Write seems necessary | Permission Safety | N/A (gate check) | STOP — see write rules below |

### 3. Execute the read

Use `gh api` as the CLI-MVP carrier:

**GraphQL example (Status Snapshot):**

```bash
gh api graphql -f query='
{
  repository(owner: "jannekbuengener", name: "Claire_de_Binare") {
    pullRequests(states: [OPEN], first: 10, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        number title reviewDecision mergeStateStatus
        statusCheckRollup { nodes { state description } }
      }
    }
  }
}
'
```

**REST example (Actions runs):**

```bash
gh api repos/jannekbuengener/Claire_de_Binare/actions/runs --jq '.workflow_runs[] | {id, name, status, conclusion, created_at}'
```

**Search example (Issue Dedupe):**

```bash
gh api "search/issues?q=repo:jannekbuengener/Claire_de_Binare+<keywords>" --jq '.items[] | {number, title, state}'
```

**Rate limit check:**

```bash
gh api rate_limit --jq '.resources | to_entries[] | {name: .key, remaining: .value.remaining, limit: .value.limit, reset: .value.reset}'
```

### 4. Handle partial visibility honestly

If an API call fails due to missing scope or permissions:

- Record exactly what failed and why
- Do NOT silently skip the missing data
- Do NOT treat the partial result as complete
- Output must include `partial_visibility` and `collection_errors`

Example:

```text
partial_visibility:
  - ProjectV2: BLOCKED (missing read:project scope)
  - Checks details: BLOCKED (fine-grained PAT cannot access Checks API)
collection_errors:
  - gh project view 8: FORBIDDEN
```

### 5. Write gate

| Intent | Rule |
|--------|------|
| Read any GitHub data | Automatically OK when scope touches GitHub live state |
| Comment on issue/PR | Only if Plan-GO explicitly allows it |
| Create issue/PR | Only if Plan-GO explicitly allows it |
| Label/milestone changes | Only if Plan-GO explicitly allows it |
| Rebase/push | Only if Plan-GO explicitly allows it |
| Squash merge (`gh pr merge --squash --delete-branch`) | Never a Delivery Mode or Conductor action. Only `cdb_final_head_merge_executor` (Merge Agent) may execute regular merge after HEAD-bound APPROVE from `cdb_final_head_pr_approval_gate`, with Final-Head gates re-verified (`FINAL_HEAD_READY_FOR_APPROVAL`, exact head/base, hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` + `policy-gate` SUCCESS on the exact head). Read/write capability is not governance authority. `--admin` is never a substitute. |
| GitHub APPROVE review | Only `cdb_final_head_pr_approval_gate` (PR Reviewer) on the exact final `HEAD_SHA`. Cannot merge. |
| Repo settings/admin | Separate scope, never automatic |
| Branch protection changes | Separate scope, never automatic |

When a write seems necessary but no approved scope exists:

1. STOP.
2. Report what needs writing and why.
3. Propose the write as a follow-up with explicit Human-GO.
4. Do NOT execute the write.

For Final-Head readiness specifically: if Conductor cannot verify the hosted
Required Checks, report `DONE_PR_OPEN_MERGE_HANDOFF` (Final Head not ready).
Delivery sessions and Conductor must not execute merge.

## Hard rules

### Read-first posture

- GitHub live data is truth. Prefer API reads over assumptions or cached
  memory.
- Always record auth profile, evidence sources, and partial visibility in
  output.
- Never treat a partial result as complete.

### Permission safety

- Broad read, narrow write. Snapshot MVP is strictly read-only.
- Fine-grained PAT has known gaps: cannot call Checks API, cannot access
  user-owned Projects per GitHub docs (see Fine-grained PAT permissions
  matrix: https://docs.github.com/en/rest/overview/permissions-required-for-fine-grained-personal-access-tokens).
- Classic PAT has `repo` scope but no `read:project` — ProjectV2 remains
  invisible without it.
- GitHub App is the target architecture for stable broad read access but
  is not yet implemented.
- Never present fine-grained PAT as a universal solution for the full
  snapshot surface.

### ProjectV2 visibility

- `read:project` scope is required to read ProjectV2 items via GraphQL.
- If `read:project` is missing, mark ProjectV2 as a known visibility gap.
- Do NOT infer ProjectV2 field values from other data sources.
- The existing `project_reconcile_daily.yml` workflow prefers GitHub App
  over PAT for this reason.

### Rate limit discipline

- Primary: 5,000 requests/hour (authenticated REST).
- GraphQL: 5,000 points/hour (single-node query = 1 point).
- Check `/rate_limit` before batch operations.
- Prefer GraphQL for connected data (issues, PRs, reviews, checks) to
  reduce request count.
- Use REST for Actions runs/jobs/logs, labels, commit statuses, contents.

### Fail-closed on auth ambiguity

- If auth scope is unclear, test with a minimal read before assuming
  access.
- If a read returns 403/404, record it as a visibility gap, not as
  "nothing there."
- If auth scope is unclear, test with a minimal read before assuming access.
- If a read returns 403/404, record it as a visibility gap, not as "nothing there."
- Do NOT retry with elevated privileges or different tokens automatically.

## API surface reference

| Sub-operation | Preferred API | Key permission | Known gap |
|---------------|---------------|---------------|-----------|
| Status Snapshot | GraphQL + REST | `repo`, `read:project` | ProjectV2 without `read:project` |
| CI/Checks Readout | REST (Actions, Checks) | `repo` | Fine-grained PAT: no Checks |
| PR Queue Radar | GraphQL | `repo` | — |
| Issue Dedupe | REST Search | `repo` | — |
| API Opportunity Scan | N/A (diagnostic) | — | — |
| Multi-Repo Snapshot | GraphQL + REST per repo | `repo` per repo | Same per-repo auth gaps |
| ProjectV2 Reconciliation | GraphQL ProjectV2 | `read:project` | Missing scope = invisible |
| Rate-Limit Awareness | REST `/rate_limit` | none | — |
| Permission Safety | N/A (gate) | — | — |

## Official GitHub docs evidence

- REST overview: https://docs.github.com/en/rest/about-the-rest-api/about-the-rest-api
- GraphQL overview: https://docs.github.com/en/graphql
- `gh api` manual: https://cli.github.com/manual/gh_api
- REST rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- `GITHUB_TOKEN` permissions: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- PAT creation/limits: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/choosing-permissions-for-a-github-app
- Fine-grained PAT permissions matrix: https://docs.github.com/en/rest/overview/permissions-required-for-fine-grained-personal-access-tokens
- Issues REST: https://docs.github.com/en/rest/issues/issues
- Pull Requests REST: https://docs.github.com/en/rest/pulls/pulls
- PR Reviews REST: https://docs.github.com/en/rest/pulls/reviews
- Labels REST: https://docs.github.com/en/rest/issues/labels
- Commit Statuses REST: https://docs.github.com/en/rest/commits/statuses
- Contents REST: https://docs.github.com/en/rest/repos/contents
- Actions workflow runs REST: https://docs.github.com/en/rest/actions/workflow-runs
- Checks REST: https://docs.github.com/en/rest/checks

## Relationship to existing skills

- `gh-fix-ci`: handles CI fix implementation after this skill identifies
  the failure picture
- `gh-address-comments`: handles PR review comment triage after this skill
  identifies the PR landscape
- `cdb-ci-cd-guard`: governs CI/CD ruleset compliance; this skill provides
  the live API data that `cdb-ci-cd-guard` may need
- `cdb-control-intake`: reads control context; this skill reads live GitHub
  data as a complementary source
- `cdb-session-start`: may invoke this skill when session scope touches
  GitHub live data
- `docs/github/UNIFIED_GITHUB_STATUS_SNAPSHOT.md`: the detailed reference
  document for the Status Snapshot sub-operation

## Follow-up issues (proposed, not created)

- `[GITHUB-API][MVP] Build read-only Unified GitHub Status Snapshot CLI`
- `[GITHUB-API][GRAPHQL] Add reusable ProjectV2/statusCheckRollup query bundle`
- `[GITHUB-API][AGENTS] Add API Opportunity Scan to CDB/Modusmono agent prompts`
- `[GITHUB-API][APP] Evaluate GitHub App target architecture`

## Anti-patterns

- Do NOT fire `gh api` calls without checking auth scope first
- Do NOT treat partial GitHub data as complete truth
- Do NOT write to GitHub without explicit Plan-GO
- Do NOT present fine-grained PAT as a universal auth solution
- Do NOT infer ProjectV2 data when `read:project` is missing
- Do NOT batch API calls without checking rate limits first
- Do NOT retry 403 with different credentials automatically
- Do NOT replace `gh-fix-ci` or `gh-address-comments` with this skill
- Do NOT read or expose tokens, secrets, or private keys in any output
- Do NOT create issues, PRs, or comments without Human-GO
- Do NOT treat Board stage or `trade-capable` as Live-Go; LR remains NO-GO

## PR-Routing und gh-only Writes

- Vor neuen Branches oder PRs `cdb-pr-router` ausführen.
- Routing-Inventar read-only über `gh issue view`, `gh pr list` und
  `gh pr view` erheben.
- Issue-/PR-Kommentare, Body-/Ledger-Updates und Merge ausschließlich über
  `gh`.
- Der `cdb-local-ci` Publisher schreibt App-gebundene Check Runs (default) über
  `gh api`; direkte HTTP-Writes sind verboten.
- Combined Commit Status über `/commits/<sha>/status` prüfen; Check Runs separat
  lesen.
- Bei Pagination, Rate-Limit, Auth- oder Lock-Ambiguität fail-closed HOLD.
