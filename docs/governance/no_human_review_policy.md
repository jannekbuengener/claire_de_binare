# No Human Review Policy

**Status**: Active
**Scope**: All PRs to `main` in `Claire_de_Binare`
**Effective**: 2026-02-23
**Owner**: jannekbuengener (repo owner)

## Context

This is a solo-maintainer repo with AI-assisted development (Claude, Copilot).
GitHub self-approval remains unavailable, and there is no second standing human
reviewer for routine PR flow.

The repo already operates this way de facto since 2026-02-15
(see [BRANCH_PROTECTION_LOG.md](BRANCH_PROTECTION_LOG.md) — PR #839, PR #846).
This document makes the practice explicit and auditable.
As of 2026-04-08, `require_code_owner_reviews` is explicitly disabled to avoid
recreating the `.github/CODEOWNERS` self-deadlock later observed on PR #1023
and PR #1024.

## Decision

**Merge gate = required checks + live branch protection settings on `main`.**

SSOT for the required check contract: [`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md).
The merge-relevant required contexts on `main` are the hosted Check Runs
`ci (Unit/Integration + Lint gesammelt)` and `policy-gate` (exact PR head SHA,
live via `gh api`). `cdb-local-ci` (Local CI Status Publisher, App Check Run
`app_id=4410232`) is seit #4540 optionaler Developer-Preflight/Diagnose und
**kein** branch-protection-required Context.

A PR may merge when:
1. The required hosted status checks pass (`ci (Unit/Integration + Lint
   gesammelt)` + `policy-gate`, live via `gh api` Check Runs)
2. Optional `cdb-local-ci` preflight is green where run, or documented as not
   required (infra/billing/lock ≠ code failure)
3. Live branch protection remains satisfied — reverify with `gh api`, do not
   assume this document's field values are current (see table below)
4. A self-review comment is present (see template below)

AI/Jules review comments are advisory only. They do not grant approval or merge
rights, and Six-Eyes is not technically enforced by current branch protection.
`.github/CODEOWNERS` remains available for routing/visibility, but code-owner
review is not part of the active merge gate on `main`.

## Scope and Exceptions

This policy applies to **all PRs** with two explicit exception categories:

| Exception | Trigger | Required action |
|-----------|---------|-----------------|
| System invariant changes | Edits to `SYSTEM_INVARIANTS.md` or enforcement mechanisms | Documented justification + link to governance change in this repo |
| Live trading enablement | Changes to `soak_mode`, `paper_mode`, or live exchange credentials | Explicit operator sign-off in PR comment |

Exception PRs follow the same CI gate but **must** include a `## Risk Assessment`
section with rollback steps. No extra repo-specific AI or human signoff step is
introduced here; live branch protection remains the operative control.

## Definition of Done for PRs

- [ ] Required CI checks green
- [ ] Self-review comment posted (see template)
- [ ] Scope statement: what changed, what was NOT changed
- [ ] For infra/security/schema PRs: rollback plan or revert command documented
- [ ] For new features: feature flag (default OFF) or evidence of no runtime impact
- [ ] No secrets in diff (`gitleaks` check passes)

## Self-Review Template

PR authors post this as a comment before merge:

```markdown
## Self-Review

**Scope**: [1-2 sentences: what this PR changes]
**Not touched**: [what was explicitly left unchanged]
**Risk**: [none / low / medium] — [1 sentence justification]
**Tests**: [test command + result summary]
**Rollback**: [revert command or "git revert <sha>" or "feature flag OFF"]
**Evidence**: [link to CI run or paste of test output]
```

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Bad code merges without review | Required merge contexts on `main`: hosted Check Runs `ci (Unit/Integration + Lint gesammelt)` + `policy-gate` (Branch Protection, strict) |
| Schema/infra breakage | Runbooks required for infra PRs; enforcement scripts are opt-in operator steps |
| Silent behavioral regression | Decision contract tests (`tests/contract/`), deterministic gate in conftest.py |
| Accidental secret exposure | Auxiliary scans (for example `gitleaks`) plus PR hygiene; not a required merge context on `main` |
| Force-push / branch deletion | `enforce_admins: true`, `allow_force_pushes: false`, `allow_deletions: false` |
| Flakey/pre-existing test failures | See "Quarantined Tests" below |

## Quarantined Tests

Tests that fail due to missing dependencies or external services (not code bugs)
are documented here. They do not block merge.

| Test | Reason | Tracked in |
|------|--------|-----------|
| `tests/smoke/test_mcp_runtime.py` | Requires `pytest-twisted` (not in CI deps) | Pre-existing |
| `tests/integration/test_execution_pipeline.py` | Requires `flask` (service dep, not in test env) | Pre-existing |
| `tests/integration/test_mexc_testnet.py` | Requires `requests_mock` | Pre-existing |
| `tests/unit/candles/test_regime_lookup.py` | Requires `flask` | Pre-existing |
| `tests/unit/execution/test_service*.py` | Requires `flask` | Pre-existing |
| `tests/unit/signal/test_service.py` | Requires `flask` | Pre-existing |

When a quarantined test is fixed, remove it from this table and add it
to the required CI check suite.

## Branch Protection Settings (verify live, do not trust this table alone)

Live lookup (authoritative; reverify before relying on any value below):

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection
```

| Setting | Last-known live value | Purpose |
|---------|-------|---------|
| `required_status_checks.checks` | `[{"context":"ci (Unit/Integration + Lint gesammelt)"},{"context":"policy-gate"}]` | Merge-relevant required contexts on `main` (hosted Check Runs, kein festes `app_id`) |
| `required_status_checks.strict` | `true` | Branch must be up-to-date |
| `enforce_admins` | `true` | Admins also bound by checks |
| `required_conversation_resolution` | `false` | Verify live — do not assume `true` |
| `allow_force_pushes` | `true` | Verify live — do not assume `false` |
| `required_approving_review_count` | `0` | No fixed approving-review count |
| `require_code_owner_reviews` | `false` | Disabled to avoid `.github/CODEOWNERS` self-deadlock in solo-maintainer mode |
| `dismiss_stale_reviews` | `true` | Prior review state is invalidated after new pushes |
| `required_linear_history` | `true` | Merge commits are disallowed on `main` |
| `allow_deletions` | `false` | Cannot delete main |

All other fields not confirmed by the most recent live `gh api` check must be
re-verified rather than assumed from this table; treat this table as a
historical snapshot, not a live source of truth.

## References

- [BRANCH_PROTECTION_LOG.md](BRANCH_PROTECTION_LOG.md) — historical decisions
- [GOVERNANCE_AUDIT_RUNBOOK.md](GOVERNANCE_AUDIT_RUNBOOK.md)
- [docs/ci/ACTION_REQUIRED_RUNBOOK.md](../ci/ACTION_REQUIRED_RUNBOOK.md) — bot PR approval flow
