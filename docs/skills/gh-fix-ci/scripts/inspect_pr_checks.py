#!/usr/bin/env python3
"""
GitHub CI Failure Inspector for Claire de Binare

Inspects failing GitHub Actions checks on Pull Requests, providing categorized
failure analysis with actionable fix suggestions.

Usage:
    python inspect_pr_checks.py --pr <NUMBER> [OPTIONS]

Exit Codes:
    0 - No failing checks
    1 - Failing checks found
    2 - Tool/auth/system error
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Any

# Configuration from DISCOVERY_REPORT.md
DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
POLL_INTERVAL = 10  # seconds
MAX_WAIT_TIME = 600  # 10 minutes
DEFAULT_LOG_LINES = 100
MAX_LOG_LINES = 500
RETRY_COUNT = 2

# The merge-relevant required contexts on `main` are the hosted Check Runs
# `ci (Unit/Integration + Lint gesammelt)` and `policy-gate` (Branch
# Protection, #4540). SSOT: docs/runbooks/merge_policy_ci_gate.md. A
# same-named Commit Status is not merge-sufficient. `cdb-local-ci` (Local CI
# Status Publisher, App Check Run `app_id=4410232`) is optional developer
# preflight/diagnose and not branch-protection-required.
REQUIRED_CHECKS = ["ci (Unit/Integration + Lint gesammelt)", "policy-gate"]

# Legacy Commit Status `state` values (same name, non-sufficient) normalized
# to Check Run-style conclusions so rollup parsing can treat both uniformly.
_STATUS_STATE_TO_CONCLUSION = {
    "SUCCESS": "SUCCESS",
    "FAILURE": "FAILURE",
    "ERROR": "FAILURE",
}

# Status handling
POLL_STATUSES = ["IN_PROGRESS", "QUEUED", "PENDING"]
FAILURE_STATUSES = ["FAILURE", "CANCELLED", "TIMED_OUT"]
SKIP_STATUSES = ["SKIPPED", "ACTION_REQUIRED"]
SUCCESS_STATUSES = ["SUCCESS", "NEUTRAL"]


class FailureCategory(Enum):
    """Failure categories from DISCOVERY_REPORT.md"""

    LINT = "LINT"
    TYPE_CHECK = "TYPE_CHECK"
    TEST = "TEST"
    SECURITY = "SECURITY"
    GOVERNANCE = "GOVERNANCE"
    E2E = "E2E"
    UNKNOWN = "UNKNOWN"


@dataclass
class FailurePattern:
    """Pattern for categorizing failures"""

    category: FailureCategory
    check_names: List[str]
    keywords: List[str]
    fix_hint: str


# Failure patterns from DISCOVERY_REPORT.md Section 8.2
FAILURE_PATTERNS = [
    FailurePattern(
        category=FailureCategory.LINT,
        check_names=["ci (Ruff)", "Linting (Ruff)", "Format Check (Black)"],
        keywords=["Ruff found", "Black would reformat", "style violation"],
        fix_hint="Run: black . && ruff check --fix .",
    ),
    FailurePattern(
        category=FailureCategory.TYPE_CHECK,
        check_names=["Type Checking (mypy)", "ci (mypy)"],
        keywords=[
            "mypy error",
            "incompatible type",
            "missing return",
            "Duplicate module",
        ],
        fix_hint="Add type hints or configure mypy excludes",
    ),
    FailurePattern(
        category=FailureCategory.TEST,
        check_names=["Tests (Python", "ci (pytest)"],
        keywords=["FAILED tests/", "AssertionError", "test_"],
        fix_hint="Run: pytest tests/ -v --tb=short --maxfail=1",
    ),
    FailurePattern(
        category=FailureCategory.SECURITY,
        check_names=["gitleaks", "trivy", "pip-audit"],
        keywords=["Credential detected", "CVE-", "vulnerability"],
        fix_hint="Remove credentials, update dependencies, or add CVE to allowlist",
    ),
    FailurePattern(
        category=FailureCategory.GOVERNANCE,
        check_names=["Check Delivery Gate", "Check Core Duplicates"],
        keywords=["DELIVERY_APPROVED", "duplicate core/"],
        fix_hint="Review governance requirements in knowledge/governance/",
    ),
    FailurePattern(
        category=FailureCategory.E2E,
        check_names=["E2E", "e2e-"],
        keywords=["Redis connection", "Postgres", "Docker Compose"],
        fix_hint="Check if STUB mode expected (PR fork?), verify credentials",
    ),
]


@dataclass
class CheckResult:
    """Result of a single check"""

    name: str
    status: str
    conclusion: Optional[str]
    details_url: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class FailingCheck:
    """Detailed information about a failing check"""

    name: str
    conclusion: str
    url: str
    category: FailureCategory
    log_snippet: Optional[str]
    fix_hint: str


class PRCheckInspector:
    """Inspects PR checks and provides failure analysis"""

    def __init__(self, repo: str, pr_number: int, verbose: bool = False):
        self.repo = repo
        self.pr_number = pr_number
        self.verbose = verbose

    def run_gh_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """
        Run gh CLI command with retry logic

        Returns:
            Parsed JSON output

        Raises:
            SystemExit(2) on auth failure or repeated errors
        """
        for attempt in range(RETRY_COUNT + 1):
            try:
                cmd = ["gh"] + args
                if self.verbose:
                    print(f"[DEBUG] Running: {' '.join(cmd)}", file=sys.stderr)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    check=True,
                )
                stdout = result.stdout if result.stdout else ""
                return json.loads(stdout) if stdout.strip() else {}

            except subprocess.TimeoutExpired:
                if attempt < RETRY_COUNT:
                    if self.verbose:
                        print(
                            f"[WARN] Timeout, retrying ({attempt+1}/{RETRY_COUNT})...",
                            file=sys.stderr,
                        )
                    time.sleep(2)
                    continue
                else:
                    self._error_exit(f"Command timed out after {timeout}s", exit_code=2)

            except subprocess.CalledProcessError as e:
                # Check for auth failures
                if (
                    "403" in e.stderr
                    or "401" in e.stderr
                    or "authentication" in e.stderr.lower()
                ):
                    self._handle_auth_failure(e.stderr)

                if attempt < RETRY_COUNT:
                    if self.verbose:
                        print(
                            f"[WARN] Command failed, retrying ({attempt+1}/{RETRY_COUNT})...",
                            file=sys.stderr,
                        )
                    time.sleep(2)
                    continue
                else:
                    self._error_exit(f"gh CLI error: {e.stderr}", exit_code=2)

            except json.JSONDecodeError as e:
                self._error_exit(f"Failed to parse gh output: {e}", exit_code=2)

        # Should never reach here
        self._error_exit("Unexpected error in run_gh_command", exit_code=2)

    def _handle_auth_failure(self, error_message: str):
        """Handle authentication failures"""
        print("❌ Authentication failed", file=sys.stderr)
        print(file=sys.stderr)

        # Get current auth status
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            print("Current auth status:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
        except Exception:
            logging.getLogger(__name__).debug(
                "Could not get auth status (ignored)", exc_info=True
            )

        print(file=sys.stderr)
        print("Remediation:", file=sys.stderr)
        print("1. Check if you have access to this repository", file=sys.stderr)
        print("2. Run: gh auth switch", file=sys.stderr)
        print("3. Or set GITHUB_TOKEN environment variable", file=sys.stderr)

        sys.exit(2)

    def _error_exit(self, message: str, exit_code: int = 2):
        """Print error and exit"""
        print(f"❌ Error: {message}", file=sys.stderr)
        sys.exit(exit_code)

    def get_pr_checks(self) -> List[CheckResult]:
        """Get all checks for the PR.

        `statusCheckRollup` mixes two GitHub object shapes:
                - Check Run (Hosted Actions): `name` / `status` / `conclusion`.
                - Required hosted Check Runs (`ci (Unit/Integration + Lint gesammelt)`,
                  `policy-gate`) use Check Run `name` / `conclusion`; legacy Commit
                  Status same name is not merge-sufficient. Rollup may still include
                  StatusContext entries (no separate
                  status/conclusion pair). Both are normalized into `CheckResult`
                  here so downstream logic (required-check lookup, categorization)
                  does not need to special-case the required context.
        """
        data = self.run_gh_command(
            [
                "pr",
                "view",
                str(self.pr_number),
                "--repo",
                self.repo,
                "--json",
                "statusCheckRollup",
            ]
        )

        checks = []
        for check_data in data.get("statusCheckRollup", []):
            name = check_data.get("name") or check_data.get("context") or "Unknown"
            status = check_data.get("status")
            conclusion = check_data.get("conclusion")
            state = check_data.get("state")
            if state is not None and status is None and conclusion is None:
                normalized_state = str(state).upper()
                conclusion = _STATUS_STATE_TO_CONCLUSION.get(normalized_state)
                status = "COMPLETED" if conclusion else normalized_state

            checks.append(
                CheckResult(
                    name=name,
                    status=status or "",
                    conclusion=conclusion,
                    details_url=check_data.get("detailsUrl")
                    or check_data.get("targetUrl", ""),
                    started_at=check_data.get("startedAt"),
                    completed_at=check_data.get("completedAt"),
                )
            )

        return checks

    def categorize_failure(
        self, check_name: str, log_snippet: Optional[str]
    ) -> tuple[FailureCategory, str]:
        """
        Categorize a failing check based on name and log content

        Returns:
            (category, fix_hint) tuple
        """
        # Match by check name first
        for pattern in FAILURE_PATTERNS:
            if any(name_pattern in check_name for name_pattern in pattern.check_names):
                return pattern.category, pattern.fix_hint

        # Match by log keywords if snippet available
        if log_snippet:
            for pattern in FAILURE_PATTERNS:
                if any(
                    keyword.lower() in log_snippet.lower()
                    for keyword in pattern.keywords
                ):
                    return pattern.category, pattern.fix_hint

        return FailureCategory.UNKNOWN, "Inspect check logs for details"

    def get_check_logs(
        self, check: CheckResult, lines: int = DEFAULT_LOG_LINES
    ) -> Optional[str]:
        """
        Retrieve logs for a failing check

        Returns:
            Last N lines of log, filtered for errors, or None if unavailable
        """
        if not check.details_url:
            return None

        # Extract run ID from URL
        # Format: https://github.com/owner/repo/actions/runs/{run_id}/job/{job_id}
        parts = check.details_url.split("/")
        if "runs" not in parts:
            return None

        try:
            run_idx = parts.index("runs") + 1
            run_id = parts[run_idx]
        except (ValueError, IndexError):
            return None

        # Try to get logs
        try:
            cmd = ["gh", "run", "view", run_id, "--repo", self.repo, "--log"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if result.returncode != 0 or not result.stdout:
                return None

            # Filter and truncate
            log_lines = result.stdout.splitlines()

            # Filter for error keywords
            error_keywords = [
                "error",
                "fail",
                "fatal",
                "exception",
                "traceback",
                "##[error]",
            ]
            filtered_lines = [
                line
                for line in log_lines
                if any(keyword in line.lower() for keyword in error_keywords)
            ]

            # Use filtered if we found errors, otherwise use full log
            relevant_lines = filtered_lines if filtered_lines else log_lines

            # Take last N lines
            truncated = relevant_lines[-lines:]

            return "\n".join(truncated)

        except Exception as e:
            if self.verbose:
                print(
                    f"[WARN] Could not retrieve logs for {check.name}: {e}",
                    file=sys.stderr,
                )
            return None

    def poll_for_completion(self, max_wait: int = MAX_WAIT_TIME) -> List[CheckResult]:
        """
        Poll checks until all complete or timeout

        Returns:
            Final list of checks
        """
        start_time = time.time()
        iteration = 0

        while time.time() - start_time < max_wait:
            iteration += 1
            checks = self.get_pr_checks()

            # Count in-progress checks
            in_progress = [c for c in checks if c.status in POLL_STATUSES]

            if not in_progress:
                print("\n✅ All checks complete", file=sys.stderr)
                return checks

            # Show progress
            elapsed = int(time.time() - start_time)
            print(
                f"\r⏳ [{elapsed}s] Waiting for {len(in_progress)} check(s) to complete...",
                end="",
                file=sys.stderr,
            )

            if iteration % 6 == 0:  # Every minute, show check names
                print(file=sys.stderr)
                for check in in_progress[:3]:  # Show first 3
                    print(f"  - {check.name}", file=sys.stderr)

            time.sleep(POLL_INTERVAL)

        print(
            f"\n⚠️  Timeout after {max_wait}s with {len(in_progress)} check(s) still in progress",
            file=sys.stderr,
        )
        return checks

    def analyze_checks(
        self, checks: List[CheckResult], log_lines: int = DEFAULT_LOG_LINES
    ) -> tuple[List[FailingCheck], Dict[str, Any]]:
        """
        Analyze checks and generate failure report

        Returns:
            (failing_checks, summary_stats) tuple
        """
        failing_checks = []

        # Count by status/conclusion
        passed = sum(1 for c in checks if c.conclusion in SUCCESS_STATUSES)
        failed = sum(1 for c in checks if c.conclusion in FAILURE_STATUSES)
        in_progress = sum(1 for c in checks if c.status in POLL_STATUSES)
        skipped = sum(
            1
            for c in checks
            if c.status in SKIP_STATUSES or c.conclusion in SKIP_STATUSES
        )

        # Check required checks
        required_status = {}
        for req_check in REQUIRED_CHECKS:
            matching = [c for c in checks if c.name == req_check]
            if matching:
                required_status[req_check] = (
                    matching[0].conclusion or matching[0].status
                )
            else:
                required_status[req_check] = "NOT_FOUND"

        # Analyze failures
        for check in checks:
            if check.conclusion not in FAILURE_STATUSES:
                continue

            # Get logs
            log_snippet = self.get_check_logs(check, lines=log_lines)

            # Categorize
            category, fix_hint = self.categorize_failure(check.name, log_snippet)

            failing_checks.append(
                FailingCheck(
                    name=check.name,
                    conclusion=check.conclusion,
                    url=check.details_url,
                    category=category,
                    log_snippet=log_snippet,
                    fix_hint=fix_hint,
                )
            )

        summary = {
            "total": len(checks),
            "passed": passed,
            "failed": failed,
            "in_progress": in_progress,
            "skipped": skipped,
            "required_checks_status": required_status,
        }

        return failing_checks, summary


def format_human_output(
    pr_number: int,
    repo: str,
    failing_checks: List[FailingCheck],
    summary: Dict[str, Any],
):
    """Format human-readable output"""
    # Use ASCII-safe characters for Windows console compatibility
    check_pass = "[OK]"
    check_fail = "[FAIL]"

    print(f"PR #{pr_number}: {repo}")
    print(
        f"Status: {summary['passed']} passed, {summary['failed']} failed, {summary['in_progress']} in_progress"
    )
    print()

    # Check required checks
    required_failed = [
        name
        for name, status in summary["required_checks_status"].items()
        if status in FAILURE_STATUSES
    ]

    if required_failed:
        print(
            f"{check_fail} Required merge context failed/red ({len(required_failed)}/{len(REQUIRED_CHECKS)}): BLOCKED_REQUIRED_STATUS"
        )
        for name in required_failed:
            print(f"  - {name}")
        print()
    else:
        not_found = [
            name
            for name, s in summary["required_checks_status"].items()
            if s == "NOT_FOUND"
        ]
        passed_count = len(
            [
                s
                for s in summary["required_checks_status"].values()
                if s in SUCCESS_STATUSES
            ]
        )

        if not_found:
            print(
                f"{check_fail} Required merge context missing on this head SHA: REQUIRED_STATUS_MISSING"
            )
            print(f"   Missing: {', '.join(not_found)}")
        else:
            print(
                f"{check_pass} Required merge context is SUCCESS: MERGE_READY ({passed_count}/{len(REQUIRED_CHECKS)})"
            )
        print()

    hosted_actions_failed = [c for c in failing_checks if c.name not in REQUIRED_CHECKS]
    if hosted_actions_failed:
        print(
            f"[ADVISORY] {len(hosted_actions_failed)} Hosted Actions check(s) red (does not block merge if required checks are SUCCESS):"
        )
        for check in hosted_actions_failed:
            print(f"  - {check.name}")
        print()

    # Show failing checks
    if failing_checks:
        print(f"Failing Checks ({len(failing_checks)}):\n")

        for i, check in enumerate(failing_checks, 1):
            print(f"{i}. {check.name} - {check.conclusion}")
            print(f"   Category: {check.category.value}")
            print(f"   URL: {check.url}")

            if check.log_snippet:
                print(f"\n   Error Snippet (last {DEFAULT_LOG_LINES} lines, filtered):")
                for line in check.log_snippet.splitlines()[
                    :20
                ]:  # Show first 20 lines of snippet
                    print(f"     {line}")
                if len(check.log_snippet.splitlines()) > 20:
                    print(
                        f"     ... ({len(check.log_snippet.splitlines()) - 20} more lines)"
                    )

            print(f"\n   Fix: {check.fix_hint}")
            print()


def format_json_output(
    pr_number: int,
    repo: str,
    failing_checks: List[FailingCheck],
    summary: Dict[str, Any],
):
    """Format JSON output"""
    output = {
        "pr_number": pr_number,
        "repo": repo,
        "summary": summary,
        "failing_checks": [
            {
                "name": check.name,
                "conclusion": check.conclusion,
                "url": check.url,
                "category": check.category.value,
                "log_snippet": check.log_snippet,
                "fix_hint": check.fix_hint,
            }
            for check in failing_checks
        ],
    }
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Inspect failing GitHub Actions checks on Pull Requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pr 807
  %(prog)s --pr 807 --repo owner/name
  %(prog)s --pr 807 --wait
  %(prog)s --pr 807 --json
  %(prog)s --pr 807 --check "ci (Unit" --lines 200
""",
    )

    parser.add_argument("--pr", type=int, required=True, help="Pull Request number")
    parser.add_argument(
        "--repo", default=DEFAULT_REPO, help=f"Repository (default: {DEFAULT_REPO})"
    )
    parser.add_argument(
        "--wait", action="store_true", help="Poll for in-progress checks (max 10 min)"
    )
    parser.add_argument("--check", help="Filter by check name (substring match)")
    parser.add_argument(
        "--lines",
        type=int,
        default=DEFAULT_LOG_LINES,
        help=f"Log lines to show (default: {DEFAULT_LOG_LINES}, max: {MAX_LOG_LINES})",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Validate
    if args.lines > MAX_LOG_LINES:
        print(f"Warning: Limiting lines to {MAX_LOG_LINES} for safety", file=sys.stderr)
        args.lines = MAX_LOG_LINES

    # Create inspector
    inspector = PRCheckInspector(args.repo, args.pr, verbose=args.verbose)

    # Get checks
    checks = inspector.get_pr_checks()

    if not checks:
        print(f"No checks found for PR #{args.pr}", file=sys.stderr)
        sys.exit(0)

    # Poll if requested
    if args.wait:
        checks = inspector.poll_for_completion()

    # Filter if requested
    if args.check:
        checks = [c for c in checks if args.check.lower() in c.name.lower()]
        if not checks:
            print(f"No checks matching '{args.check}'", file=sys.stderr)
            sys.exit(0)

    # Analyze
    failing_checks, summary = inspector.analyze_checks(checks, log_lines=args.lines)

    # Output
    if args.json:
        format_json_output(args.pr, args.repo, failing_checks, summary)
    else:
        format_human_output(args.pr, args.repo, failing_checks, summary)

    # Exit code
    if failing_checks:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
