# GitHub Actions `action_required` Runbook (Bots/Apps)

## Purpose
This runbook defines deterministic handling for workflow runs that end in `action_required`, especially on bot/app PRs where checks show no started jobs.

## A) Symptom / Detection
- Workflow run conclusion is `action_required`.
- Run details show `jobs=[]` (no jobs started).
- UI typically shows an approval gate, e.g. `Approval required` / `Approve and run`.
- Why this is critical:
  - Required contexts may not be emitted.
  - PR signal is blocked even when workflow definitions are valid.
  - This can deadlock bot/app PRs.

Evidence anchors from triage:
- `22192989773` (PR `#867`, branch `copilot/sub-pr-865`) -> `action_required`, `jobs=[]`  
  Link: `https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989773`
- `22192989851` (`E2E Happy Path`) -> `action_required`  
  Link: `https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22192989851`

## B) Immediate Unblock (< 60 seconds)
1. Open the affected run in GitHub Actions (`Actions` -> run).
2. Check for the approval banner (`Approval required`).
3. Click `Approve and run` (or equivalent approval button).
4. Verify jobs are created and start running (no longer `jobs=[]`).
5. Verify the required contexts on the PR head: `ci (Unit/Integration + Lint
   gesammelt)` and `policy-gate` (the branch-protection-required hosted
   Checks; SSOT:
   [`merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md)). Hosted
   Actions runs must emit these two check names — approve the run so the
   required merge gate can be satisfied.

Important:
- Approve only; do not post or expose secret values.
- Only secret names may be referenced for troubleshooting.

## C) Root Cause (Policy, Not Flake)
`action_required` is usually deterministic governance behavior, not an intermittent test failure.

Typical causes:
- Repository policy requires approval for workflows from untrusted contributors.
- Bot/app-authored PRs are treated as untrusted until maintainer approval.
- Token/permission constraints for app-triggered runs.

## D) Prevention / Governance Options (Documentation Only)
No settings are changed by this runbook. This section documents decision options.

Decision tree:
- Need maximum safety and explicit human gate? -> **MODE 1 (Strict approval)**
- Need fewer bot/app deadlocks and faster CI signal? -> **MODE 2 (Auto-run for trusted bots)**

### MODE 1: Strict approval (safer default)
- Keep approval gates enabled.
- Maintainers must explicitly approve `action_required` runs.
- This runbook is mandatory operating procedure.
- Watch required-check workflows first.

### MODE 2: Auto-run for trusted bots
- Goal: bot/app PR workflows run without manual approval deadlock.
- This is a repository settings decision and must be consciously approved.
- UI paths to review:
  - `Settings -> Actions -> General -> Fork pull request workflows`
  - `Require approval for all outside collaborators` (on/off)
  - `Require approval for first-time contributors` (on/off)
  - `Settings -> Actions -> General -> Workflow permissions` (keep least privilege)
- Security warning:
  - Auto-run increases attack surface.
  - Keep least privilege and review trust boundaries before enabling.

## E) Maintainer Checklist (Daily Ops)
- If a PR run is `action_required`:
  - 1) Approve run.
  - 2) Confirm the actual required merge contexts are live-green on the exact
       PR head SHA: `ci (Unit/Integration + Lint gesammelt)` and `policy-gate`
       (verify via `gh api` check runs; `required-checks-audit.yml` audits it).
  - 3) If recurring, review governance settings using MODE 1 vs MODE 2.

## F) Do / Don't
DO:
- Approve runs only as a maintainer.
- Reference secret names only (never values).
- Track repeat incidents as governance debt.

DON'T:
- Do not switch workflows to `pull_request_target` as a quick fix (scope/threat-model risk).
- Do not rename workflows/jobs that participate in required-check context stability (`ci`, `policy-gate`).
- Do not treat `action_required` as a flaky test symptom.
