<!--
Canonical Skill Source: docs/skills/gh-fix-ci/SKILL.md
Surface: opencode
Sync Status: mirrored-from-canon
Last Verified: 2026-08-08
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
# gh-fix-ci - GitHub CI Failure Inspector

**Version:** 1.1.0
**Status:** Active
**Canonical Location:** `docs/skills/gh-fix-ci/`

---

## Purpose

Inspects failing GitHub Actions checks on Pull Requests for the Claire de Binare (CDB) repository, providing:
- Summary of failing checks with exact names and URLs
- Categorized failure analysis (Lint, Type Check, Test, Security, Governance, E2E)
- Concise failure snippets from logs (last 100 lines, error-filtered)
- Actionable fix suggestions based on failure patterns

**Default Repository:** `jannekbuengener/Claire_de_Binare` (override supported via `--repo`)

---

## Invocation

### Basic Usage
```bash
python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr <PR_NUMBER>
```

### With Options
```bash
# Specify different repository
python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807 --repo owner/name

# JSON output
python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807 --json

# Poll for in-progress checks (wait up to 10 minutes)
python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807 --wait

# Filter by check name (substring match)
python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807 --check "ci (Unit"

# Customize log lines shown
python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807 --lines 200
```

---

## Check Status Handling

Based on [DISCOVERY_REPORT.md](../../../docs/skills/gh-fix-ci/DISCOVERY_REPORT.md) findings:

### Polling Behavior (only with `--wait` flag)
- **Poll Statuses:** `IN_PROGRESS`, `QUEUED`, `PENDING`
- **Poll Interval:** 10 seconds
- **Max Wait Time:** 600 seconds (10 minutes)
- **Default:** NO polling (returns current status immediately)

### Hard Stop Statuses
- `FAILURE` → Report as failed check
- `CANCELLED` → Report as failed (user cancelled)
- `TIMED_OUT` → Report as failed (timeout exceeded)

### Skip/Ignore Statuses
- `SKIPPED` → Ignored (path filters, conditional logic)
- `ACTION_REQUIRED` → Ignored (workflow_dispatch, manual approval gates)

### Success Statuses
- `SUCCESS` → Passing check
- `NEUTRAL` → Passing with warnings

---

## Required Checks for CDB

**SSOT:** `docs/runbooks/merge_policy_ci_gate.md`.
Live branch protection on `main` requires **two** merge-relevant
contexts (both **hosted Check Runs**, #4540):

- **`ci (Unit/Integration + Lint gesammelt)`** — hosted GitHub Actions
  run for the exact PR head SHA.
- **`policy-gate`** — hosted policy-gate Check Run for the exact PR head SHA.

Verify live with `gh api`, not from any hardcoded list (including this one).
A same-named Commit Status is not merge-sufficient.

`cdb-local-ci` (Local CI Status Publisher, App Check Run `app_id=4410232`) is
seit #4540 optionaler Developer-Preflight/Diagnose und kein
branch-protection-required Context. Remaining hosted check-runs — `validate-branch-name`,
`gitleaks (Secrets-Alarm)`, `trivy (kritische CVEs/Supply-Chain)`,
`Check Core Duplicates`, `Check Delivery Gate`, `guard`, `E2E Happy Path`, and
similar — are **advisory/safety-relevant only**. They remain useful signal
(lint, tests, security, governance, E2E) and should be inspected and fixed
when red, but their status alone does **not** gate merge and does not need
to be "8/8 present" for merge eligibility.

### Failure classification (used by this skill)

- `MERGE_READY` — hosted Required Checks `ci (Unit/Integration + Lint gesammelt)`
  and `policy-gate` are SUCCESS on the exact PR head SHA. Means Final-Head CI
  readiness only — **not** merge authority and **not** APPROVE. Other Hosted
  Actions findings remain advisory.
- `REQUIRED_STATUS_MISSING` — one/both Required Checks absent or stale for
  the exact head SHA. Not merge-eligible; needs a fresh hosted run on the
  head SHA.
- `CODE_FAILURE` — a check (hosted Required Check or advisory job) fails
  due to an actual code/test/lint/type issue. Fixable in-repo.
  `--check` name filtering (e.g. `--check "ci (Unit"`) still works for
  Hosted Actions advisory triage.
- `HOSTED_ACTIONS_INFRA_BLOCK` — Hosted Actions run is red/blocked due to
  billing, runner lock, `action_required` approval gate, or similar
  infrastructure condition unrelated to code correctness. Report distinctly
  from `CODE_FAILURE`; does not block merge if Required Checks are SUCCESS.
- `AUTH_PUBLISHER_BLOCK` — the session cannot read/verify the Required
  Checks or (if attempting to publish) cannot authenticate with sufficient
  scope. See Auth Preflight below.

### Conditional Checks

Some Hosted Actions checks may not be present on every PR due to workflow
path filters:

- **E2E Happy Path**: Ergänzender E2E-Workflow; kein branch-protected Required Check.
- The script reports these as "not triggered" rather than failures.
- Output format: `[OK] Hosted Actions advisory checks: 7/7 present, 1 not triggered (2 required checks SUCCESS)`

### Auth Preflight

Before relying on any check result, verify the identity/token can actually
read live status:

1. `gh auth status` — confirm an authenticated identity.
2. `gh api repos/<owner>/<repo>/commits/<head_sha>/check-runs` — confirm
   the hosted Required Checks are readable for the exact PR head SHA.
   A same-named Commit Status via `/status` is not
   sufficient (billing/lock on Hosted Actions does not affect this read).
3. If step 2 fails with an auth/permission error, classify as
   `AUTH_PUBLISHER_BLOCK`, not `REQUIRED_STATUS_MISSING` — these have
   different remediations (fix auth vs. get a fresh hosted run on the head).

Fixing a red check never authorizes Approval or Merge. After any commit
produced by a CI fix, stale Final-Head Evidence and Approval are invalid.

---

## Failure Categories & Auto-Fix Hints

### LINT
**Check Names:** `ci (Ruff)`, `Linting (Ruff)`, `Format Check (Black)`
**Keywords:** "Ruff found", "Black would reformat", "style violation"
**Fix Command:** `black . && ruff check --fix .`

### TYPE_CHECK
**Check Names:** `Type Checking (mypy)`, `ci (mypy)`
**Keywords:** "mypy error", "incompatible type", "missing return"
**Fix Hint:** Add type hints or configure mypy excludes

### TEST
**Check Names:** `Tests (Python 3.11)`, `Tests (Python 3.12)`, `ci (pytest)`
**Keywords:** "FAILED tests/", "AssertionError", "test_"
**Fix Command:** `pytest tests/ -v --tb=short --maxfail=1`

### SECURITY
**Check Names:** `gitleaks`, `trivy`, `pip-audit`
**Keywords:** "Credential detected", "CVE-", "vulnerability"
**Fix Hint:** Remove credentials, update dependencies, or add CVE to allowlist

### GOVERNANCE
**Check Names:** `Check Delivery Gate`, `Check Core Duplicates`
**Keywords:** "DELIVERY_APPROVED", "duplicate core/"
**Fix Hint:** Review governance requirements in `knowledge/governance/`

### E2E
**Check Names:** `E2E Happy Path`, `e2e-paper-trading`
**Keywords:** "Redis connection", "Postgres", "Docker Compose"
**Fix Hint:** Check if STUB mode expected (PR fork?), verify credentials available

---

## Matrix Job Support

The script detects and reports failures across matrix jobs (e.g., Python 3.11 vs 3.12):

**Example Output:**
```
Failing Checks (2/15):

1. Tests (Python 3.11) - FAILURE
   URL: https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/123/job/456
   Category: TEST
   Snippet (last 100 lines):
     FAILED tests/unit/test_foo.py::test_bar - AssertionError
   Fix: pytest tests/ -v --tb=short --maxfail=1

2. Tests (Python 3.12) - SUCCESS (passed)
```

---

## Output Contract

### Human-Readable Summary (Default)
```
PR #807: jannekbuengener/Claire_de_Binare
Status: 13 passed, 0 failed, 2 in_progress

[OK] Required merge context is SUCCESS: MERGE_READY (2/2)

[ADVISORY] 1 Hosted Actions check(s) red (does not block merge if required checks are SUCCESS):
  - trivy (kritische CVEs/Supply-Chain)
```

Missing/red required context is reported instead as:
```
[FAIL] Required merge context missing on this head SHA: REQUIRED_STATUS_MISSING
   Missing: ci (Unit/Integration + Lint gesammelt), policy-gate
```
or
```
[FAIL] Required merge context failed/red (1/2): BLOCKED_REQUIRED_STATUS
  - policy-gate
```

### JSON Output (with `--json`)
```json
{
  "pr_number": 807,
  "repo": "jannekbuengener/Claire_de_Binare",
  "summary": {
    "total": 15,
    "passed": 13,
    "failed": 0,
    "in_progress": 2,
    "skipped": 0,
    "required_checks_status": {
      "ci (Unit/Integration + Lint gesammelt)": "SUCCESS",
      "policy-gate": "SUCCESS"
    }
  },
  "failing_checks": []
}
```

---

## Exit Codes

- **0** - No failing checks (all passed or still in progress)
- **1** - Failing checks found
- **2** - Tool/auth/system error (gh CLI failure, auth blocked, etc.)

---

## Multi-Account Handling

**Detected Accounts** (from `gh auth status`):
- `jannekbuengener` (active, GITHUB_TOKEN)
- `plaketten-ingo` (inactive, keyring)
- `jannekbuengener` (duplicate, keyring)

**Behavior:**
- **NEVER auto-switch** accounts
- **Detect and report only:** If auth fails, print active account and suggest `gh auth switch`
- **Hard stop on auth failure:** Exit code 2 with remediation message

**Auth Failure Message:**
```
❌ Authentication failed for jannekbuengener/Claire_de_Binare

Current active account: jannekbuengener
Available accounts: jannekbuengener, plaketten-ingo

Remediation:
1. Check if you have access to this repository
2. Run: gh auth switch
3. Or set GITHUB_TOKEN environment variable
```

---

## Safety Rules

### What This Skill Does NOT Do

1. ❌ **No auto-merge** - Never merges PRs automatically
2. ❌ **No commits/pushes** - Never commits or pushes code unless explicitly instructed
3. ❌ **No workflow file changes** - Never modifies `.github/workflows/` without explicit approval
4. ❌ **No account switching** - Never runs `gh auth switch` automatically

### What This Skill Does

1. ✅ **Read-only inspection** - Reads PR check status via `gh pr checks`
2. ✅ **Log retrieval** - Fetches logs from failed runs via `gh run view --log`
3. ✅ **Suggest-only fixes** - Provides fix commands but doesn't execute them
4. ✅ **Safe defaults** - No destructive operations, always ask before applying changes

---

## Log Truncation & Filtering

**Default Behavior:**
- Retrieve last **100 lines** from failed job logs
- Filter for error keywords: `error`, `fail`, `fatal`, `exception`, `traceback`
- Include **5 lines context** before/after each error

**Configurable:**
- `--lines N` - Show last N lines (max 500 for safety)
- `--full-log` - Show complete log (WARNING: may be very large)

**Log Retrieval Limitations:**
- Logs unavailable for very old runs (GitHub retention policy)
- Logs unavailable for cancelled runs (not persisted)
- Logs unavailable for runs from forks (permission issues)
- **Fallback:** If log retrieval fails, show check conclusion summary only

---

## CI Workflows in CDB

**Workflow Categories:**

1. **Lint & Format:** Ruff, Black
2. **Type Checking:** mypy
3. **Unit/Integration Tests:** pytest (Python 3.11, 3.12 matrix)
4. **Security Scans:** gitleaks (credentials), trivy (CVE), pip-audit (dependencies)
5. **Governance Gates:** Delivery Gate, Core Guard, Repository Canon Guard
6. **E2E Integration:** Paper Trading pipeline (Redis, Postgres, Docker Compose)

**Total Workflows:** 41 in `.github/workflows/`
**PR-Triggering Workflows:** 10 (run on every PR to `main`)

---

## Dependencies

**Required:**
- `gh` CLI (GitHub CLI) - https://cli.github.com/
- `python` 3.10+ (for script execution)
- `jq` (for JSON parsing in gh commands)

**Optional:**
- `git` (for branch/repo detection)

---

## Examples

### Example 1: Check PR with All Passing Checks
```bash
$ python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807

PR #807: docs(lr): add LR-007 Shadow Mode status tracking
Status: ✅ All checks passed (15/15)

Exit code: 0
```

### Example 2: Check PR with Failing Lint
```bash
$ python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 806

PR #806: docs(lr): start LR-007 Shadow Mode (IN_PROGRESS)
Status: ❌ 1 failing check (19/20 passed)

Failing Checks:

1. Type Checking (mypy) - FAILURE
   Category: TYPE_CHECK
   URL: https://github.com/.../runs/21780276909/job/62843170058

   Error Snippet (last 100 lines, filtered):
   services/market/service.py: error: Duplicate module named "service"
   Found 1 error in 1 file (errors prevented further checking)
   ##[error]Process completed with exit code 2.

   Fix: Add __init__.py or configure mypy excludes

Exit code: 1
```

### Example 3: Poll for In-Progress Checks
```bash
$ python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807 --wait

PR #807: docs(lr): add LR-007 Shadow Mode status tracking
Status: ⏳ Waiting for checks to complete (2 in progress)

Polling every 10s (max 10 min)...

[10s] trivy (kritische CVEs/Supply-Chain) - IN_PROGRESS
[20s] trivy (kritische CVEs/Supply-Chain) - IN_PROGRESS
[30s] trivy (kritische CVEs/Supply-Chain) - SUCCESS ✅

All checks complete. Final status: ✅ All passed

Exit code: 0
```

### Example 4: Auth Failure
```bash
$ python docs/skills/gh-fix-ci/scripts/inspect_pr_checks.py --pr 807

❌ Authentication failed: HTTP 403 Forbidden

Current active account: jannekbuengener
Available accounts: jannekbuengener, plaketten-ingo

Remediation:
1. Verify repository access for jannekbuengener
2. Run: gh auth switch
3. Or: export GITHUB_TOKEN=<your_value>

Exit code: 2
```

---

## References

- **Discovery Report:** [DISCOVERY_REPORT.md](../../../docs/skills/gh-fix-ci/DISCOVERY_REPORT.md)
- **CDB Repository:** https://github.com/jannekbuengener/Claire_de_Binare
- **GitHub CLI Docs:** https://cli.github.com/manual/

---

**Created:** 2026-02-08
**Last Updated:** 2026-07-30
**Maintainer:** Claude Code (Session Lead)
