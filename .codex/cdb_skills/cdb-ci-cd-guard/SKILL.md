<!--
Canonical Skill Source: docs/skills/cdb-ci-cd-guard/SKILL.md
Surface: codex
Sync Status: mirrored-from-canon
Last Verified: 2026-08-08
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-ci-cd-guard
description: CDB CI/CD governance audit and hardening for the Claire de Binare repository. Use when GitHub Actions, rulesets, required checks, secret guards, or fake-green behavior need to be verified or fixed. Derive protected refs, required checks, and enforcement behavior from current repo evidence and GitHub state instead of assuming old branch patterns or legacy repository-canon paths.
disable-model-invocation: true
---

# CI/CD Guard

## Canon first
- Use the Claire de Binare repository as the only default source.
- Start control-first:
  1. GitHub control issue `#1445`
  2. newest weekly comment on `#1445`
  3. stage-ratification issue `#1492` as Board context only
  4. `docs/runbooks/CONTROL_REGISTER.md`
  5. `CURRENT_STATUS.md`
  6. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  7. only then inspect rulesets, issues, PRs, and workflows
- Read `docs/index.md` and `docs/runbooks/merge_policy_ci_gate.md` for local CI canon after the control-first chain.
- Treat GitHub rulesets and required checks as evidence-bearing runtime state. If they are not observable, report the gap instead of inventing a result.
- Treat `#1492` only as current Board context, not as any CI or LR override.

## Use this when
- a run is green but hidden stub, mock, skip, or fallback behavior is suspected
- required checks, branch protection, secret guards, or delivery gates look inconsistent
- workflow behavior changes by branch or secret availability

## Hard rules
- Do not assume protected branch patterns. Derive them from current rulesets, workflows, or explicit user input.
- No silent stub or mock path on protected refs.
- Missing critical secrets on protected refs must fail closed.
- Without explicit approval, default to audit plus fix plan rather than mutation.
- The merge-relevant required contexts are the hosted Check Runs
  `ci (Unit/Integration + Lint gesammelt)` (#4540) and `policy-gate` — not a
  Commit Status. Verify live with `gh api` on `/commits/<sha>/check-runs`; do
  not hardcode a required-checks list from memory. `cdb-local-ci` (Local CI
  Status Publisher, App Check Run `app_id=4410232`) is seit #4540 optionaler
  Developer-Preflight/Diagnose und kein branch-protection-required Context.
- This skill validates and helps publish Final-Head CI evidence. It does
  **not** own approval or merge. Regular merge is owned only by
  `cdb_final_head_merge_executor` after HEAD-bound APPROVE from
  `cdb_final_head_pr_approval_gate` (see
  `docs/contracts/final_head_merge_pipeline.v1.md`). `--admin` is never a
  valid bypass for missing/red hosted Required Checks.
- CI PASS / green Hosted Actions does **not** authorize blind local post-merge
  cleanup. After `--delete-branch`, remote absence is expected; local
  worktree/branch removal remains evidence-based
  (`cdb-session-close` § Safe Post-Merge Cleanup). Do not equate required-status
  SUCCESS with safe `worktree remove` / `branch -D`.

## Workflow
1. Inventory active workflows and identify gate-bearing jobs.
2. Derive protected refs, required checks, and enforcement scope from repo evidence plus GitHub state.
3. Search for fake-green vectors: stub, mock, fallback, skipped gates, soft-fail secret handling.
4. Verify that guard decisions are visible in logs and outputs.
5. Produce deterministic evidence per workflow: protected behavior, unprotected behavior, secret handling, merge-blocking effect.
6. If fixes are needed, propose the smallest reversible patchset first.

## External Documentation Lookup

This skill audits CI/CD tooling with external documentation dependencies:
- Load `cdb-external-docs` to find official docs for GitHub Actions, Gitleaks, Trivy, etc.
- Look up `docs/external-docs/index.md` → Repo-Control / Security sections.
- Verify expected behavior against official docs before labelling a gate as fake-green.
- If no internet/browsing is available, report the docs gap and proceed conservatively.

## Output
- PASS or FAIL
- concrete enforcement gaps, grouped by workflow or ruleset
- mapping table: workflow -> trigger/ref scope -> secret behavior -> merge effect
- minimal fix plan, or patchset if explicit approval exists

## Slice Validation

- Deterministische Auswahl über `ci/config/slice_validation_policy.v1.yaml`
  (Inputs: `changed_paths`, `routing_lane`, `validation_profile`).
- Outputs maschinenlesbar: `selected_test_groups`, `selection_reasons`,
  `unclassified_paths`, `fallback_reason`, immer `merge_evidence=false`.
- Unbekannte Pfade, Policy-/Schemafehler, Runtime/Risk/Docker-Pfade →
  fail-closed Full Fast-CI Unit-Selektor.
- Targeted Tests und relevante Contract-Tests laut Selection,
- Lint/Format für betroffene Dateien,
- `git diff --check`,
- kein Full Fast-CI als Default für Delivery-Slices,
- **kein** `cdb-local-ci` Publish als Merge-Evidence (Publisher rejected slice
  evidence; Preflight bleibt optional, ist aber kein Required Check).
- Stage-/Unit-Timing: `reports/stage_timing.json`, `reports/unit_timing.json`
  (`--durations`) — ändert nicht Pass/Fail.

## Final Batch Head Validation

- PR ist `merge_candidate` und für neue Slices eingefroren,
- Full Fast-CI auf dem exakten finalen Head
  (`pytest -q -k "not test_mcp_time_server_runtime"` unverändert),
- integrierter Base-SHA ist in der Evidence gebunden,
- lokaler Policy-Gate-Mirror ist grün,
- hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` und
  `policy-gate` sind grün auf exakt diesem Head (Branch Protection,
  kein hartkodiertes `app_id`),
- Head-/Base-Drift erzwingt vollständige Revalidierung.
- Slice-Validation ist **kein** Ersatz für Final-Head-Evidence.

Check Runs und Commit Status sind getrennte GitHub-Typen. Ein namensgleicher
**Commit Status** erfüllt die hosted Required Checks nicht. Cloud
Approval/Merge agents only consume the hosted Check Runs; they do not
fabricate local CI. Slice Validation never becomes Final-Head Evidence.
