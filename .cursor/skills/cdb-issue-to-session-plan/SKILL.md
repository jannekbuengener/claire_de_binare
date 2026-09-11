<!--
Canonical Skill Source: docs/skills/cdb-issue-to-session-plan/SKILL.md
Surface: cursor
Sync Status: mirrored-from-canon
Last Verified: 2026-08-08
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-issue-to-session-plan
description: >
  Turn a concrete Claire_de_Binare GitHub issue into a fail-closed session plan.
  Use when given an issue number or URL and control context must be rebuilt first
  via CONTROL_REGISTER and Issue #1445 before deriving a conservative mini-plan.
disable-model-invocation: true
---

# CDB issue to session plan

Use this after `cdb-control-intake` when the next concrete unit of work is one specific GitHub issue. Convert that issue into an executable session plan without treating the issue itself as authorization.

## Inputs

- A concrete GitHub issue number, URL, or issue thread.
- Claire de Binare repository at `D:\Dev\Workspaces\Repos\Claire_de_Binare`.
- Access to GitHub Issue `#1445`, its comments, and current open issues/PRs.

## Workflow

1. Rebuild the control context first. Do not read the target issue before this sequence is complete:
   - Read `docs/runbooks/CONTROL_REGISTER.md`.
   - Read GitHub Issue `#1445`.
   - Read the current newest substantive human weekly comment in `#1445`, not a later bot-generated digest or report-only follow-up.
   - Read `CURRENT_STATUS.md`.
   - Read `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
2. Read the target issue only after the control stack above is in hand.
3. Pull only the extra workflow context needed to ground the issue:
   - Check relevant open PRs if the issue references them or they materially affect execution order.
   - Check closely related follow-up or blocker issues only when the target issue explicitly depends on them.
   - Check newer repo-backed automation comments in `#1445` only when they materially change the issue's readiness, blocker state, or sequencing.
   - Do not broaden the search surface without evidence from the issue or the control sources.
4. Mirror the issue against the current operating reality:
   - Determine current Board stage and operating focus from `CONTROL_REGISTER.md`.
   - Determine weekly priorities and sequencing from the newest weekly comment in `#1445`.
   - Determine repo and engineering posture from `CURRENT_STATUS.md`.
   - Determine Go/No-Go and live-trading boundaries from `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
   - Determine whether the issue is aligned, premature, blocked, superseded, or too risky in the current workflow state.
5. Derive a session plan from the issue without overcommitting:
   - State the short diagnosis first.
   - Rank the issue inside the current stage and weekly context.
   - Name guardrails, blockers, and explicit non-goals.
   - Break the work into a short, ordered session plan with concrete next steps.
   - Every plan ends in a PR handoff. Name the target PR from the routing
     block and the expected close state `DONE_SLICE_ADDED_TO_BATCH_PR`: the
     issue is delivered into a compatible open PR, that PR stays open, and the
     issue stays open until a verified merge. A compatible open PR always has
     priority over a new PR.
   - Never plan a merge, approve, a full final-head Fast-CI, a hosted
     Required-Check verification, an acceptance-chain run (`cdb-integration-wiring-audit`,
     `cdb-pr-gap-classifier`, `cdb-pr-completeness-review`,
     `cdb-batch-merge-conductor`), or an issue closure into a delivery
     session.      Final-Head prep, Cloud PR Reviewer APPROVE, and Merge Agent
     execution belong to a separately started merge session per
     `docs/contracts/final_head_merge_pipeline.v1.md`.
   - Mark all unresolved assumptions as unconfirmed.

## Interpretation Rules

- Never implement or recommend work only because an issue is open.
- Treat an open issue as a work package candidate, not as authorization.
- Never treat Board stage as live-trading approval.
- Never use `CURRENT_STATUS.md` as the LR verdict source.
- Use `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` as SSOT for Go/No-Go.
- If LR is `NO-GO`, keep the session plan in shadow/mock-only scope even if the issue language sounds execution-ready.
- Respect solo-maintainer reality unless a source explicitly proves otherwise.
- Keep scope pinned to the target issue and proven prerequisites.
- Keep parked or future-anchor issues out of the committed plan unless the control context proves they are active again.
- If status sources conflict, stay conservative and surface the conflict instead of reconciling it optimistically.

## Fail-Closed Rules

- If the control stack cannot be rebuilt in the required order, stop and report planning blocked.
- If Issue `#1445` or its newest weekly comment cannot be read confidently, stop and report planning blocked.
- If the target issue is missing, ambiguous, or underspecified, stop and report what remains unconfirmed.
- If the issue conflicts with current stage, LR guardrails, or weekly sequencing, do not silently rewrite priorities; surface the conflict and narrow the plan.
- If related PRs or follow-up issues appear relevant but cannot be confirmed as dependencies, mark them as possible context and keep them out of the committed plan.
- If the target issue is parked, future-facing, or otherwise lacks an active delivery signal in the current control context, do not force a work plan; return a narrow no-action or watch-state plan instead.
- If live-readiness is unclear, assume `NO-GO`.

## Output

Return the result in this structure:

```md
Kurzbefund
- ...

Prioritaet im aktuellen Stage-Kontext
- ...

Risiken / Guardrails
- ...

Empfohlene Session-Schritte
1. Action - why now - evidence
2. Action - why now - evidence
3. Action - why now - evidence

Nicht anfassen
- ...

Restunsicherheiten
- ...
```

## Anti-Patterns

- Do not read the target issue first and add control context afterward.
- Do not convert issue text directly into implementation tasks without checking current control posture.
- Do not expand into adjacent issues, epics, or refactors unless the dependency is explicit and current.
- Do not imply live approval, Echtgeld readiness, or strategy release from issue wording.
- Do not hide uncertainty; mark open points as unconfirmed.

## Mandatory Routing Block

Jeder Session-Plan enthält vor Implementation:

```yaml
routing:
  issue_number: <N>
  routing_decision: <decision>
  target_pr: <number-or-null>
  target_branch: <branch-or-null>
  batch_key: <key-or-null>
  lane: <lane>
  lock_state: <state>
  validation_profile: <profile>
  merge_mode: <batch-or-dedicated>
  merge_trigger_state: <state>
  reason_codes: []
```

Der Block stammt aus `cdb-pr-router`. Ohne sichere Route bleibt der Plan HOLD.
Ein normaler Plan endet mit Slice-Handoff; Full Fast-CI und Merge werden nur für
einen separaten Final-Batch-Head geplant.
