<!--
Canonical Skill Source: docs/skills/cdb-drift-reconcile/SKILL.md
Surface: claude
Sync Status: mirrored-from-canon
Last Verified: 2026-08-08
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-drift-reconcile
description: >
  Reconcile known Claire_de_Binare drift vectors against the current canon and
  produce a conservative findings report. Use when Codex must inspect
  documentation, runbooks, discovery surfaces, architecture maps, stack and
  secrets references, or service catalogs for canon drift, classify each area
  as belegt, unklar, or kein Befund, and separate documentation drift from
  operational drift without expanding scope. Use this for bounded canon-drift
  reconciliation, not for generic docs cleanup.
disable-model-invocation: true
---

# CDB drift reconcile

Check known drift vectors against the current canon and return a bounded reconciliation finding, not a broad cleanup campaign.

## Inputs

- A drift-check request, drift suspicion, or maintenance pass over canon surfaces.
- Claire de Binare repository at `D:\Dev\Workspaces\Repos\Claire_de_Binare`.
- Access to `docs/runbooks/CONTROL_REGISTER.md` and the repo surfaces it points to.

## Required Drift Areas

Always check these areas unless the request explicitly narrows scope further:

- Solo-Maintainer-Drift in SOPs
- Terminologie-Drift: use `Risk Service` / `cdb_risk` consistently; avoid stale service terminology
- Stack-Canon-Drift: `BLUE/RED` instead of legacy single-compose language
- Secrets-Canon-Drift
- SSOT-Grenzen between `CURRENT_STATUS.md` and `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- Discovery-Surfaces / EntryPoints / Cheatsheets
- `ARCHITECTURE_MAP` / `SERVICE_CATALOG` when service changes are implicated
- Skill Surface Mirror Drift: canon `docs/skills/<name>/SKILL.md` vs adapter surfaces `.opencode`, `.cursor`, `.codex`, `.claude`

## Workflow

1. Read `docs/runbooks/CONTROL_REGISTER.md` first.
2. Build the search and review matrix from the drift vectors defined there:
   - Do not invent new drift categories unless the control source itself requires them.
   - Use the required drift areas above as the minimum matrix.
3. Inspect only the repo surfaces needed to evaluate the active matrix:
   - Runbooks, SOPs, status files, architecture maps, service catalogs, discovery docs, cheatsheets, and stack or secrets references.
   - Pull service maps only when the suspected drift touches service naming, boundaries, or runtime topology.
   - Keep historical snapshots and archive paths out of scope unless needed to confirm that something is merely historical.
4. Classify every checked area with exactly one finding state:
   - `belegt`
   - `unklar`
   - `kein Befund`
5. For every `belegt` or `unklar` finding, separate the impact type:
   - Documentation drift only
   - Operational drift
   - Blocker-relevant operational drift
6. Reconcile conservatively:
   - Treat historical anchors as historical unless current canon still points to them as active.
   - Treat canon-boundary uncertainty as unresolved, not as clean.
   - Do not convert every drift finding into a follow-up issue or workflow change.
   - Keep Board stage separate from LR status at all times.

## Post-Merge Status-/Ledger Drift (Issue #4218)

Stale `CURRENT_STATUS.md` or ledger lines after a merge are **documentation
drift**, not a reason to open an immediate `CURRENT_STATUS-only` /
`ledger-only`-**Nachlauf-PR**. Route corrections via freeze-in-original-PR or
the next compatible **`docs-governance`** batch (`cdb-pr-router`). Fail-closed
when urgency is unclear. Safety-critical false claims need an explicit
Incident-/Governance exception — never a routine status-tail PR.

## Skill Surface Mirror Drift

Since PR #3637 the canonical skill source is `docs/skills/<name>/SKILL.md`.
Surface adapters mirror those bodies (PR #3641). Canon edits can silently drift
the adapters, so this drift vector has a dedicated, scriptable check.

- Canon: `docs/skills/<name>/SKILL.md`
- Adapters: `.opencode/skills/<name>/SKILL.md`, `.cursor/skills/<name>/SKILL.md`,
  `.codex/cdb_skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`
- Check command (read-only, no writes, no network):

  ```bash
  python tools/validate_skill_surface_mirror.py          # human report
  python tools/validate_skill_surface_mirror.py --json   # machine-readable
  python tools/validate_skill_surface_mirror.py --skill <name>
  ```

- Result semantics and exit codes:
  - `PASS` (exit 0): every expected adapter matches canon in body (header ignored)
    and carries a valid `mirrored-from-canon` surface header.
  - `DRIFT_FOUND` (exit 1): an adapter body differs, an adapter header is missing or
    not `mirrored-from-canon`, or an expected adapter is missing.
  - `BLOCKED` (exit 2): missing canon tree, unknown skill, or parse/usage error.
- Documented exclusions (not drift): `cdb-onboarding` is codex-only alias;
  `gh-fix-ci` keeps `META.yaml`/`evals.json`/`scripts/` canon-only (only `SKILL.md`
  bodies are compared); `.claude/skills/*.skill` and `.gemini/skills/` are out of scope.

**Fail-Closed rule:** If `docs/skills/<name>/SKILL.md` was changed in the session
and the drift checker was not run, do not mark the session as fully complete —
report `skill surface drift unknown`.

**Follow-up rule:** On `DRIFT_FOUND`, either re-mirror the affected adapters from
canon within the current scope, or create a deduplicated re-mirror follow-up issue
and hand off. Never auto-merge. Regular merge is owned only by
`cdb_final_head_merge_executor` after HEAD-bound APPROVE and live
hosted Required Check SUCCESS (`ci (Unit/Integration + Lint gesammelt)`,
`policy-gate`) on the exact PR head
(SSOT: `docs/contracts/final_head_merge_pipeline.v1.md`).

## Post-merge branch / worktree drift

When classifying local/remote branch lineage after a squash merge:

- Treat `[gone]` after `--delete-branch` as normal, not as a push trigger.
- Detect republished merged heads (same topic branch reappearing remotely
  after MERGED) as drift; do not recommend `git push -u origin HEAD` to
  "restore" them.
- Squash non-ancestor / `git cherry +` is **not** alone proof of unmerged
  work — require tree/patch equivalence (see `cdb-session-close`
  § Safe Post-Merge Cleanup).
- Worktree/branch cleanup routing: hand off to `cdb-session-close`; do not
  remove foreign worktrees from this skill.

## Classification Rules

- `belegt` means the repo surface directly contradicts or lags the current canon.
- `unklar` means the evidence is incomplete, ambiguous, or canon boundaries are not stable enough to call clean.
- `kein Befund` means the checked surface matches the current canon closely enough for the reviewed vector.
- Documentation drift only means wording, pointers, naming, or navigation are stale but the live operational path or enforced runtime behavior is not changed by the drift.
- Operational drift means the stale canon can misroute execution, verification, secrets handling, stack invocation, or service understanding in current work.
- Blocker-relevant operational drift means the drift can directly compromise safe operation, safe validation, or correct control interpretation and should be treated as a blocker until reconciled.

## Fail-Closed Rules

- If `CONTROL_REGISTER.md` cannot be read, stop and report reconciliation blocked.
- If canon boundaries between active docs and historical snapshots cannot be determined confidently, classify the area as `unklar`.
- If a surface looks stale but the active canon source is not identifiable, do not normalize it away; keep the finding conservative.
- If service topology, secrets canon, or status-source boundaries may be affected and the relevant maps cannot be confirmed, do not downgrade below `unklar`.
- If a finding appears historical only, but current entrypoints still route users there, classify it as active drift rather than archive noise.

## Output

Return the result in this structure:

```md
Drift-Befund
- Area: belegt | unklar | kein Befund

Betroffene Dateien / Artefakte
- ...

Schweregrad
- low | medium | high

Drift-Typ
- Dokumentationsdrift | operative Drift | blocker-relevante operative Drift

Empfohlene naechste Schritte
- ...

Nicht im Scope
- ...
```

## Anti-Patterns

- Do not turn every stale reference into a new issue.
- Do not create meta-management work that is not justified by current canon.
- Do not treat historical anchors as active tasks by default.
- Do not expand from one drift vector into a full repo rewrite.
- Do not read Board stage as LR-GO or use LR files to redefine Board stage.

## PR-Flow Drift

Zusätzlich erkennen:

- dieselbe Issue in mehreren aktiven Delivery-PRs,
- mehrere kompatible Batch-PRs derselben Lane und Objective,
- PR ohne parsebaren Batch-Marker oder Ledger,
- `accepting_slices` trotz erreichtem Merge-Trigger,
- Session-Surfaces, die weiterhin automatisch eigenen PR, Full Fast-CI oder
  Merge pro Issue verlangen,
- Slice-Evidence, die als Final-Head-Evidence wiederverwendet wird.

Duplicate- oder Lock-Drift führt zu HOLD; keine automatische Konsolidierung.
