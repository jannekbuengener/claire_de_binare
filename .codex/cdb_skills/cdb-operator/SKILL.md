<!--
Canonical Skill Source: docs/skills/cdb-operator/SKILL.md
Surface: codex
Sync Status: mirrored-from-canon
Last Verified: 2026-08-08
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-operator
description: Enforces Claire de Binare operator workflow with router-first slice delivery as the default. Final-Head prep, Cloud PR Reviewer APPROVE, and Merge Agent regular merge are separate phases; delivery never merges; never --admin.
compatibility: opencode
metadata:
  project: claire-de-binare
  workflow: operator
disable-model-invocation: true
---

# CDB Operator Skill

## Purpose

Use this skill when working on Claire_de_Binare with OpenCode.

## Required workflow

1. Read `AGENTS.md` in the repo root.
2. Follow the pointer to `agents/AGENTS.md`.
3. Read `agents/OPEN_CODE_AGENTS.md` if present.
4. Read the complete repo read order before planning.
5. Pull GitHub issue and PR state live.
6. Treat `CURRENT_STATUS.md` as ledger, not live truth.
7. Produce only Lage, Befund, Plan, Dry-Run, Validierung, Restunsicherheiten.
8. Do not write, commit, push, comment, label, or close without explicit human GO.
9. Delivery is the default after Plan-GO: route first, deliver the scoped slice,
   update ledger and Issue handoff, then stop without merge, approve, or Issue
   closure. Regular merge is never a Delivery Mode action and must not bypass
   the Final-Head pipeline in
   `docs/contracts/final_head_merge_pipeline.v1.md`.
   `--admin` is never a substitute for missing/red hosted Required Checks
   (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`).
10. After a live-verified merge, local post-merge cleanup is
    evidence-based only (`cdb-session-close` § Safe Post-Merge Cleanup):
    never discard unsaved changes, never `branch -D` without tree/patch
    equivalence, never republish a deleted remote head (anti-repush),
    update local `main` with `ff-only` only.

## Stop conditions

Stop immediately on missing bootloader, unclear scope, unexpected diff, failed
targeted slice validation, or scope growth. In Final-Head preparation also stop
on red hosted Required Checks for the exact final head (`ci (Unit/Integration +
Lint gesammelt)`, `policy-gate`; branch-protection-required since #4540). Delivery sessions must not attempt
merge. Also stop on live-readiness/echtgeld implication, or a cleanup request
that would discard unsaved/unmerged local work.

## Delivery versus Final-Head pipeline

- **Delivery Mode:** Router ausführen, Slice in den zugewiesenen PR liefern,
  targeted Validation, Ledger-/Issue-Handoff, kein Approve, kein Merge.
- **Acceptance gate:** run `cdb-pr-completeness-review`. Only a schema-valid
  `MERGE_CANDIDATE` may enter Final-Head preparation. `MERGE_CANDIDATE` alone
  never authorizes approve or merge.
- **Final-Head Preparation:** `cdb-batch-merge-conductor` freezes, integrates
  main, runs Full Fast-CI, verifies hosted Required Checks
  (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`) on the exact SHA,
  and stops at
  `FINAL_HEAD_READY_FOR_APPROVAL`. Conductor does not approve or merge.
- **Approval:** `cdb_final_head_pr_approval_gate` (PR Reviewer) issues GitHub
  APPROVE bound to the exact final `HEAD_SHA`. Cannot merge.
- **Merge execution:** `cdb_final_head_merge_executor` (Merge Agent) runs
  regular `gh pr merge <PR> --squash --delete-branch` after re-verify. Cannot
  approve. Never `--admin`.
- **Close:** `cdb-session-close` verifies live MERGED (may be async).

Ein Merge-Trigger ist kein Approval und keine Merge-Autorisierung. Head- oder
Base-Drift invalidiert Final-Evidence und Approval und erzwingt erneute
Completeness Review.

