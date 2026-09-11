# Runbook: Resolve review threads via GraphQL (required_conversation_resolution)

## Purpose

- Use when a PR is mergeable and CI-green but merge is blocked by `required_conversation_resolution` due to unresolved review threads (often bot reviews).
- This is deterministic and avoids UI actions or admin bypass.

## PR comment vs review thread

- **Issue/PR comments** (timeline comments, bot receipts, `@`-mentions) do **not** satisfy `required_conversation_resolution`.
- **Review threads** (inline comments on the *Files changed* tab, tied to a path/line or an outdated diff hunk) are what branch protection counts.
- Merge blockers from bot reviews (Copilot, Codex, Sourcery) are almost always **review threads**, not general comments.

## GitHub UI path

1. Open the PR → **Files changed**.
2. Find the unresolved thread (often marked with a conversation icon).
3. For **outdated** threads on an old diff: open the thread → **Resolve conversation** (or reply then resolve if policy requires acknowledgment).
4. Re-check the PR merge box — “All conversations must be resolved” should clear when the unresolved thread count is zero.

## Preconditions

- `gh auth status` is OK
- You have permission to resolve review threads on the repo

## Step 1 — Find unresolved, non-outdated threads

Replace `PR_NUMBER` and repo owner/name as needed.

```bash
gh api graphql --input - --jq '
  .data.repository.pullRequest.reviewThreads.nodes
  | map(select(.isResolved==false and .isOutdated==false))
  | {unresolved: length,
     details: (map({id, path, line,
                    author: .comments.nodes[0].author.login,
                    snippet: (.comments.nodes[0].bodyText | tostring)}))}
' <<'JSON'
{
  "query": "query{repository(owner:\"jannekbuengener\",name:\"Claire_de_Binare\"){pullRequest(number:PR_NUMBER){reviewThreads(first:100){nodes{id isResolved isOutdated path line comments(first:1){nodes{author{login} bodyText}}}}}}}"
}
JSON
```

On Windows PowerShell, prefer piping JSON from a file or use `gh api graphql -f query=...` if heredocs are awkward.

## Step 2 — Resolve a specific thread

Replace `THREAD_ID_HERE` with the returned `id` from Step 1. The mutation field is **`threadId`** (GraphQL type `ID`), not `pullRequestReviewThreadId`.

```bash
gh api graphql --input - --jq '.data.resolveReviewThread.thread.isResolved' <<'JSON'
{
  "query": "mutation{resolveReviewThread(input:{threadId:\"THREAD_ID_HERE\"}){thread{isResolved}}}"
}
JSON
```

## Step 3 — Re-check unresolved count (must be 0)

```bash
gh api graphql --input - --jq '
  .data.repository.pullRequest.reviewThreads.nodes
  | {total:length, unresolved:(map(select(.isResolved==false and .isOutdated==false))|length)}
' <<'JSON'
{
  "query": "query{repository(owner:\"jannekbuengener\",name:\"Claire_de_Binare\"){pullRequest(number:PR_NUMBER){reviewThreads(first:100){nodes{isResolved isOutdated}}}}}"
}
JSON
```

## Step 4 — Merge normally (no admin bypass)

This repo requires **squash** merge (merge commits are disallowed). Use `--squash`, not `--merge`.

```bash
gh pr checks PR_NUMBER
gh pr merge PR_NUMBER --squash --delete-branch
```

### SHA-gated merge (`--match-head-commit`)

When branch protection uses `strict: true` and the base branch moved after CI ran, GitHub may reject merge until the PR head is current. After updating the branch (merge/rebase from `main`), merge with an explicit head match:

```bash
HEAD_SHA=$(gh pr view PR_NUMBER --json headRefOid -q .headRefOid)
gh pr merge PR_NUMBER --squash --delete-branch --match-head-commit "$HEAD_SHA"
```

Only use `--match-head-commit` when the merge UI/`gh` reports the PR is behind or head SHA mismatch; do not bypass failing checks.

## Troubleshooting

| Symptom | Action |
|---------|--------|
| GraphQL permission error on `resolveReviewThread` | Escalate to repo admin; confirm `gh auth` has `repo` scope |
| Codex/Copilot rate limit on review | Wait and retry; resolve stale bot threads only when they contain no actionable requests |
| Thread is **outdated** but still blocks merge | Resolve via UI on outdated thread, or re-run Step 1 including outdated threads if policy still counts them |
| Bot thread with no actionable content | Safe to resolve after human skim; document in PR if non-obvious |
| `Merge commits are not allowed` | Use `--squash` (or rebase merge if enabled), not `--merge` |

## Example: PR #2639

PR #2639 was blocked on `required_conversation_resolution` despite green CI. Pattern used:

1. List unresolved threads (Step 1) — bot review on a workflow-only diff.
2. Confirm thread had no open human action items.
3. `resolveReviewThread` with the returned `threadId` (Step 2).
4. Verify unresolved count `0` (Step 3).
5. `gh pr merge 2639 --squash --delete-branch` after the hosted Required
   Checks `ci (Unit/Integration + Lint gesammelt)` + `policy-gate` are SUCCESS
   live on the exact PR head (SSOT: `docs/runbooks/merge_policy_ci_gate.md`).
   Never use `--admin` as a bypass.

No secrets or tokens belong in thread bodies; sanitize before posting examples.

## Notes

- Prefer resolving only bot threads that contain no actionable requests.
- If the GraphQL mutation fails due to permissions, escalate to repo admin/maintainer policy decision.
- See also [`merge_policy_ci_gate.md`](./merge_policy_ci_gate.md) for the full blocked-PR diagnosis order.
