from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import pytest
import yaml

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "dependabot_autopilot_report.py"
)
WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "cdb-dependabot-autopilot.yml"
)
CLASSIFIER_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "dependabot_autopilot_classifier.py"
)
ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "dependabot-autopilot-allowlist.yml"
)

SPEC = importlib.util.spec_from_file_location(
    "dependabot_autopilot_report", SCRIPT_PATH
)
assert SPEC is not None
report = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = report
assert SPEC.loader is not None
SPEC.loader.exec_module(report)

classifier = report._load_classifier_module()

VALID_HEAD_SHA = "b366010aa9cbcfca440497dc64b6c8746c50ff55"
BASE_SHA = "1111111111111111111111111111111111111111"
HEAD_SHA = VALID_HEAD_SHA
REPO = "owner/example"


def _load_policy() -> classifier.AllowlistPolicy:
    raw = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    return classifier.parse_allowlist_policy(raw)


def _checks(
    *,
    conclusion: str = "success",
    duplicate_conclusion: str | None = None,
) -> dict:
    """Build a live Check Runs payload for the two required merge checks.

    Post-#4540 the merge gate is ``ci (Unit/Integration + Lint gesammelt)`` and
    ``policy-gate``, both hosted GitHub Actions Check Runs (name/status/conclusion).
    """
    check_runs = [
        {"name": "ci (Unit/Integration + Lint gesammelt)", "status": "completed", "conclusion": conclusion},
        {"name": "policy-gate", "status": "completed", "conclusion": conclusion},
    ]
    if duplicate_conclusion is not None:
        check_runs.append(
            {"name": "ci (Unit/Integration + Lint gesammelt)", "status": "completed", "conclusion": duplicate_conclusion}
        )
    return {"check_runs": check_runs}


def _dependabot_commit_message() -> str:
    return (
        "deps(pip): bump ruff from 0.15.20 to 0.15.21\n\n"
        "updated-dependencies:\n"
        "- dependency-name: ruff\n"
        "  dependency-version: 0.15.21\n"
        "  dependency-type: direct:development\n"
        "  update-type: version-update:semver-patch\n"
    )


def _pull_stub(
    number: int,
    *,
    author: str = "dependabot[bot]",
    head_ref: str = "dependabot/pip/ruff-0.15.21",
    mergeable_state: str = "clean",
) -> dict:
    return {
        "number": number,
        "user": {"login": author},
        "head": {"ref": head_ref, "sha": HEAD_SHA},
        "base": {"ref": "main", "sha": BASE_SHA},
        "mergeable_state": mergeable_state,
    }


def _detail_stub(
    *,
    author: str = "dependabot[bot]",
    head_ref: str = "dependabot/pip/ruff-0.15.21",
    head_sha: str = HEAD_SHA,
    mergeable_state: str = "clean",
    draft: bool = False,
    labels: list[str] | None = None,
) -> dict:
    return {
        "number": 4049,
        "draft": draft,
        "labels": [{"name": name} for name in (labels or [])],
        "user": {"login": author},
        "head": {"ref": head_ref, "sha": head_sha},
        "base": {"ref": "main", "sha": BASE_SHA},
        "mergeable_state": mergeable_state,
    }


def _commits_stub(
    *,
    authors: tuple[str, ...] = ("dependabot[bot]",),
    include_dependabot_message: bool = True,
    rest_author_schema: bool = False,
) -> list[dict]:
    commits: list[dict] = []
    for index, login in enumerate(authors):
        message = (
            _dependabot_commit_message()
            if include_dependabot_message and index == 0
            else "merge main"
        )
        payload: dict = {
            "commit": {"message": message},
        }
        if rest_author_schema:
            payload["author"] = {"login": login}
        else:
            payload["authors"] = [{"login": login}]
        commits.append(payload)
    return commits


def _files_stub(
    *,
    patch: str | None = "-ruff==0.15.20\n+ruff==0.15.21\n",
    filename: str = "requirements-dev.txt",
) -> list[dict]:
    return [{"filename": filename, "patch": patch}]


def _compare_stub(*, behind_by: int = 0) -> dict:
    return {"behind_by": behind_by}


def _build_transport(
    *,
    pulls: list[dict] | None = None,
    detail: dict | None = None,
    commits: list[dict] | None = None,
    files: list[dict] | None = None,
    check_runs: list[dict] | None = None,
    compare: dict | None = None,
    pull_list_error: Exception | None = None,
    check_runs_error: Exception | None = None,
) -> report.InMemoryGhTransport:
    if pull_list_error is not None:
        routes: dict = {
            f"repos/{REPO}/pulls": lambda *_args, **_kwargs: (_ for _ in ()).throw(
                pull_list_error
            )
        }
        return report.InMemoryGhTransport(routes)

    detail = detail or _detail_stub()
    commits = commits if commits is not None else _commits_stub()
    files = files if files is not None else _files_stub()
    check_runs = check_runs if check_runs is not None else _checks()
    compare = compare if compare is not None else _compare_stub()

    routes = {
        f"repos/{REPO}/pulls": pulls or [_pull_stub(4049)],
        f"repos/{REPO}/pulls/4049": detail,
        f"repos/{REPO}/pulls/4049/commits": commits,
        f"repos/{REPO}/pulls/4049/files": files,
        f"repos/{REPO}/compare/{BASE_SHA}...{HEAD_SHA}": compare,
    }
    if check_runs_error is not None:
        routes[f"repos/{REPO}/commits/{HEAD_SHA}/check-runs"] = lambda *_args, **_kwargs: (
            _ for _ in ()
        ).throw(check_runs_error)
    else:
        routes[f"repos/{REPO}/commits/{HEAD_SHA}/check-runs"] = check_runs
    return report.InMemoryGhTransport(routes)


def _run(transport: report.InMemoryGhTransport) -> report.ReportOutcome:
    return report.run_report(
        transport,
        REPO,
        ALLOWLIST_PATH,
        execution_mode="report_only",
    )


def test_ruff_patch_report_only_is_eligible_not_merge_authorized() -> None:
    outcome = _run(_build_transport())

    assert outcome.exit_code == 0
    assert len(outcome.rows) == 1
    row = outcome.rows[0]
    assert row.classification == "ELIGIBLE"
    assert row.action == "REPORT_ONLY"
    assert row.merge_authorized is False
    assert classifier.REASON_ELIGIBLE in row.reason_codes
    assert classifier.REASON_REPORT_ONLY in row.reason_codes


def test_rest_api_commit_author_schema_eligible() -> None:
    outcome = _run(
        _build_transport(
            commits=_commits_stub(rest_author_schema=True),
        )
    )

    row = outcome.rows[0]
    assert row.classification == "ELIGIBLE"
    assert classifier.REASON_ELIGIBLE in row.reason_codes


def test_non_dependabot_author_holds() -> None:
    outcome = _run(
        _build_transport(
            detail=_detail_stub(author="jannekbuengener"),
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_AUTHOR in row.reason_codes


def test_human_commit_and_behind_merge_state_hold() -> None:
    outcome = _run(
        _build_transport(
            detail=_detail_stub(mergeable_state="behind"),
            commits=_commits_stub(authors=("dependabot[bot]", "jannekbuengener")),
            compare=_compare_stub(behind_by=2),
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_COMMIT_COUNT in row.reason_codes
    assert classifier.REASON_COMMIT_AUTHOR in row.reason_codes
    assert classifier.REASON_BRANCH in row.reason_codes
    assert classifier.REASON_MERGE_STATE in row.reason_codes


def test_missing_required_check_holds() -> None:
    outcome = _run(
        _build_transport(
            check_runs={"check_runs": [{"name": "unrelated-check", "status": "completed", "conclusion": "success"}]}
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_CHECK_MISSING in row.reason_codes


def test_in_progress_required_check_holds() -> None:
    outcome = _run(
        _build_transport(
            check_runs={
                "check_runs": [
                    {"name": "ci (Unit/Integration + Lint gesammelt)", "status": "in_progress", "conclusion": ""},
                    {"name": "policy-gate", "status": "completed", "conclusion": "success"},
                ]
            }
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_CHECK_FAIL in row.reason_codes


def test_duplicate_required_check_holds() -> None:
    outcome = _run(_build_transport(check_runs=_checks(duplicate_conclusion="failure")))

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_CHECK_AMBIGUOUS in row.reason_codes


def test_per_pr_api_error_holds() -> None:
    outcome = _run(
        _build_transport(
            check_runs_error=report.GitHubApiError("rate limit"),
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_API in row.reason_codes


def test_global_discovery_failure_is_non_zero_with_summary() -> None:
    outcome = _run(
        _build_transport(pull_list_error=report.GlobalDiscoveryError("403 forbidden"))
    )

    assert outcome.exit_code == 1
    assert outcome.global_error is not None
    summary = report.render_job_summary(
        outcome, execution_mode="report_only", repo=REPO
    )
    assert "Global API Error" in summary
    assert "403 forbidden" in summary
    assert "ghp_" not in summary


def test_missing_patch_holds_without_title_only_eligible() -> None:
    outcome = _run(
        _build_transport(
            files=_files_stub(patch=None),
            commits=_commits_stub(include_dependabot_message=False),
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert row.action == "HOLD"
    assert row.merge_authorized is False
    assert classifier.REASON_FACTS_INVALID in row.reason_codes


def test_truncated_patch_holds() -> None:
    outcome = _run(_build_transport(files=_files_stub(patch="")))

    row = outcome.rows[0]
    assert row.classification == "HOLD"


@pytest.mark.parametrize(
    "patch,filename,expected_reason",
    [
        (
            "-numpy>=1.26.0\n+numpy>=2.5.1\n",
            "requirements-dev.txt",
            classifier.REASON_RANGE,
        ),
        (
            "-mcp-server-time==2026.6.4\n+mcp-server-time==2026.7.10\n",
            "requirements-dev.txt",
            classifier.REASON_DATE_VERSION,
        ),
        (
            "-    uses: actions/stale@v10.3.0\n+    uses: actions/stale@v10.4.0\n",
            ".github/workflows/stale.yml",
            classifier.REASON_ACTIONS,
        ),
        (
            "-    image: postgres:18.4-alpine\n+    image: postgres:18.5-alpine\n",
            "infrastructure/compose/docker-compose.yml",
            classifier.REASON_DOCKER,
        ),
    ],
)
def test_non_allowlisted_or_risky_updates_hold(
    patch: str, filename: str, expected_reason: str
) -> None:
    outcome = _run(
        _build_transport(
            files=_files_stub(patch=patch, filename=filename),
            detail=_detail_stub(head_ref=f"dependabot/patch/{filename}"),
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert expected_reason in row.reason_codes


def test_minor_update_holds() -> None:
    outcome = _run(
        _build_transport(
            files=_files_stub(patch="-mypy==2.1.0\n+mypy==2.2.0\n"),
            detail=_detail_stub(head_ref="dependabot/pip/mypy-2.2.0"),
            commits=[
                {
                    "authors": [{"login": "dependabot[bot]"}],
                    "commit": {
                        "message": (
                            "updated-dependencies:\n"
                            "- dependency-name: mypy\n"
                            "  dependency-version: 2.2.0\n"
                            "  dependency-type: direct:development\n"
                            "  update-type: version-update:semver-minor\n"
                        )
                    },
                }
            ],
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_UPDATE_TYPE in row.reason_codes


def test_multiple_open_dependabot_pulls_sorted_by_number() -> None:
    transport = report.InMemoryGhTransport(
        {
            f"repos/{REPO}/pulls": [_pull_stub(4048), _pull_stub(4049)],
            f"repos/{REPO}/pulls/4048": _detail_stub(
                head_ref="dependabot/pip/mypy-2.2.0"
            ),
            f"repos/{REPO}/pulls/4048/commits": [
                {
                    "authors": [{"login": "dependabot[bot]"}],
                    "commit": {"message": "minor bump"},
                }
            ],
            f"repos/{REPO}/pulls/4048/files": _files_stub(
                patch="-mypy==2.1.0\n+mypy==2.2.0\n"
            ),
            f"repos/{REPO}/pulls/4049": _detail_stub(),
            f"repos/{REPO}/pulls/4049/commits": _commits_stub(),
            f"repos/{REPO}/pulls/4049/files": _files_stub(),
            f"repos/{REPO}/compare/{BASE_SHA}...{HEAD_SHA}": _compare_stub(),
            f"repos/{REPO}/commits/{HEAD_SHA}/check-runs": _checks(),
        }
    )
    outcome = report.run_report(transport, REPO, ALLOWLIST_PATH)

    assert [row.pr_number for row in outcome.rows] == [4048, 4049]


def test_merge_paginated_payload_merges_two_pull_array_pages() -> None:
    merged = report._merge_paginated_payload([[{"number": 4048}], [{"number": 4049}]])
    assert merged == [{"number": 4048}, {"number": 4049}]


def test_merge_paginated_payload_merges_two_check_runs_object_pages() -> None:
    merged = report._merge_paginated_payload(
        [
            {"check_runs": [{"name": "ci (Unit/Integration + Lint gesammelt)"}]},
            {"check_runs": [{"name": "policy-gate"}]},
        ]
    )
    assert merged == [
        {"name": "ci (Unit/Integration + Lint gesammelt)"},
        {"name": "policy-gate"},
    ]


def test_subprocess_transport_uses_get_and_paginate_without_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        captured["args"] = args
        captured["shell"] = kwargs.get("shell")
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(report.subprocess, "run", fake_run)
    transport = report.SubprocessGhTransport(REPO)
    transport.get_json(f"repos/{REPO}/pulls")

    assert "--method" in captured["args"]
    assert "GET" in captured["args"]
    assert "--paginate" in captured["args"]
    assert captured["shell"] is not True


def test_malformed_second_paginated_json_page_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args, 0, stdout='[{"number": 4049}]\n{broken', stderr=""
        )

    monkeypatch.setattr(report.subprocess, "run", fake_run)
    transport = report.SubprocessGhTransport(REPO)
    with pytest.raises(report.GitHubApiError, match="malformed gh api paginated JSON"):
        transport.get_json(f"repos/{REPO}/pulls")


def _actions_commit_message() -> str:
    return (
        "deps(actions): bump actions/stale\n\n"
        "updated-dependencies:\n"
        "- dependency-name: actions/stale\n"
        "  dependency-version: 10.4.0\n"
        "  dependency-type: direct:production\n"
        "  update-type: version-update:semver-patch\n"
    )


def test_markdown_injection_neutralized_in_rendered_summary() -> None:
    evil_package = "actions/stale|bad`![](https://evil.example/pwn.png)"
    row = report.PullReportRow(
        pr_number=4049,
        head_branch="dependabot/github_actions/actions-stale-10.4.0",
        package_name=evil_package,
        ecosystem="github-actions",
        classification="HOLD",
        action="HOLD",
        merge_authorized=False,
        reason_codes=(classifier.REASON_ACTIONS,),
        human_summary="hold",
    )
    outcome = report.ReportOutcome((row,), None, 0)
    summary = report.render_job_summary(
        outcome, execution_mode="report_only", repo=REPO
    )
    assert "![](https://evil.example" not in summary
    assert "![" not in summary
    assert "| #4049 |" in summary
    assert "actions/stale" in summary


def test_actions_update_hold_integration_summary_is_safe() -> None:
    outcome = _run(
        _build_transport(
            files=_files_stub(
                patch="-    uses: actions/stale@v10.3.0\n+    uses: actions/stale@v10.4.0\n",
                filename=".github/workflows/stale.yml",
            ),
            detail=_detail_stub(
                head_ref="dependabot/github_actions/actions-stale-10.4.0"
            ),
            commits=[
                {
                    "authors": [{"login": "dependabot[bot]"}],
                    "commit": {"message": _actions_commit_message()},
                }
            ],
            pulls=[
                _pull_stub(
                    4049, head_ref="dependabot/github_actions/actions-stale-10.4.0"
                )
            ],
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_ACTIONS in row.reason_codes
    summary = report.render_job_summary(
        outcome, execution_mode="report_only", repo=REPO
    )
    assert "actions/stale" in summary
    assert "![" not in summary


def test_human_dependabot_head_with_markdown_injection_holds() -> None:
    outcome = _run(
        _build_transport(
            pulls=[
                _pull_stub(
                    4049,
                    author="jannekbuengener",
                    head_ref="dependabot/github_actions/actions-stale-10.4.0",
                )
            ],
            detail=_detail_stub(
                author="jannekbuengener",
                head_ref="dependabot/github_actions/actions-stale-10.4.0",
            ),
            commits=[
                {
                    "authors": [{"login": "jannekbuengener"}],
                    "commit": {"message": _actions_commit_message()},
                }
            ],
            files=_files_stub(
                patch="-    uses: actions/stale@v10.3.0\n+    uses: actions/stale@v10.4.0\n",
                filename=".github/workflows/stale.yml",
            ),
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_AUTHOR in row.reason_codes
    summary = report.render_job_summary(
        outcome, execution_mode="report_only", repo=REPO
    )
    assert "![" not in summary


def test_control_characters_neutralized_in_summary_cell() -> None:
    cell = report._sanitize_markdown_table_cell("ruff\nevil\r|injection")
    assert "\n" not in cell
    assert "\r" not in cell
    assert "|" not in cell.replace("\\|", "")


def test_token_redaction_ghp_and_github_pat_in_summary() -> None:
    for token in (
        "ghp_abcdefghijklmnopqrstuvwxyz1234567890ABCDEF",
        "github_pat_11AAAAbbbbccccddddEEEEffffGGGG",
    ):
        outcome = report.ReportOutcome((), global_error=token, exit_code=1)
        summary = report.render_job_summary(
            outcome, execution_mode="report_only", repo=REPO
        )
        assert token not in summary
        assert "[REDACTED_TOKEN]" in summary


def test_normal_package_names_remain_readable_in_summary() -> None:
    outcome = _run(_build_transport())
    summary = report.render_job_summary(
        outcome, execution_mode="report_only", repo=REPO
    )
    assert "`ruff`" in summary
    assert "`pip`" in summary

    actions_outcome = _run(
        _build_transport(
            files=_files_stub(
                patch="-    uses: actions/stale@v10.3.0\n+    uses: actions/stale@v10.4.0\n",
                filename=".github/workflows/stale.yml",
            ),
            detail=_detail_stub(
                head_ref="dependabot/github_actions/actions-stale-10.4.0"
            ),
        )
    )
    actions_summary = report.render_job_summary(
        actions_outcome, execution_mode="report_only", repo=REPO
    )
    assert "actions/stale" in actions_summary


def test_summary_is_deterministic_and_secrets_free() -> None:
    outcome = _run(_build_transport())
    first = report.render_job_summary(outcome, execution_mode="report_only", repo=REPO)
    second = report.render_job_summary(outcome, execution_mode="report_only", repo=REPO)
    assert first == second
    assert "requirements-dev.txt" not in first
    assert "+ruff" not in first
    assert "ghp_" not in first
    assert "merge_authorized: `false`" in first


def test_main_writes_summary_and_returns_exit_code_on_global_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenTransport:
        def get_json(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise report.GlobalDiscoveryError("429 rate limit")

    monkeypatch.setattr(
        report, "SubprocessGhTransport", lambda _repo: BrokenTransport()
    )
    summary_file = tmp_path / "summary.md"
    exit_code = report.main(
        [
            "--repo",
            REPO,
            "--allowlist-path",
            str(ALLOWLIST_PATH),
            "--summary-file",
            str(summary_file),
        ]
    )

    assert exit_code == 1
    content = summary_file.read_text(encoding="utf-8")
    assert "Global API Error" in content


def test_subprocess_transport_rejects_disallowed_endpoint() -> None:
    transport = report.SubprocessGhTransport(REPO)
    with pytest.raises(report.GitHubApiError, match="endpoint not allowed"):
        transport.get_json(f"repos/{REPO}/issues/1")


def test_subprocess_transport_uses_gh_repo_env_not_repo_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        captured["args"] = args
        captured["env"] = kwargs.get("env")
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(report.subprocess, "run", fake_run)
    transport = report.SubprocessGhTransport(REPO)
    transport.get_json(f"repos/{REPO}/pulls")

    assert "--repo" not in captured["args"]
    assert captured["env"]["GH_REPO"] == REPO


def _load_workflow_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _workflow_triggers(workflow: dict) -> set[str]:
    on_section = workflow.get("on") or workflow.get(True)
    if isinstance(on_section, dict):
        return set(on_section.keys())
    if isinstance(on_section, str):
        return {on_section}
    return set()


def test_workflow_has_only_schedule_and_dispatch_triggers() -> None:
    workflow = _load_workflow_yaml(WORKFLOW_PATH)
    assert _workflow_triggers(workflow) == {"schedule", "workflow_dispatch"}


def test_workflow_has_read_only_permissions_and_no_merge_commands() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = _load_workflow_yaml(WORKFLOW_PATH)
    permissions = workflow.get("permissions") or {}

    assert permissions == {
        "contents": "read",
        "pull-requests": "read",
        "statuses": "read",
    }
    lowered = content.lower()
    assert ": write" not in lowered
    assert "contents: write" not in lowered
    assert "issues: write" not in lowered
    assert "pull-requests: write" not in lowered
    assert "pull_request_target" not in content
    assert "workflow_run" not in content
    assert "gh pr merge" not in content
    assert re.search(r"ref:\s*main", content)
    assert "persist-credentials: false" in content


def test_workflow_dispatch_fail_closed_guard_present() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "github.event_name == 'workflow_dispatch'" in content
    assert "refs/heads/main" in content


def test_workflow_checkout_is_pinned_by_sha() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert re.search(r"actions/checkout@[0-9a-f]{40}", content)


def test_workflow_cron_documented_for_utc_and_berlin_offset() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'cron: "0 5 * * 1"' in content
    assert "Europe/Berlin" in content or "CET" in content or "CEST" in content


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "dependabot"


def _load_fixture(name: str) -> dict[str, Any]:
    payload = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _transport_from_fixture(fixture: Mapping[str, Any]) -> report.InMemoryGhTransport:
    files = [
        {"filename": item["filename"], "patch": item.get("patch")}
        for item in fixture["files"]
    ]
    commits = [
        {
            "authors": [{"login": str(fixture.get("author") or "dependabot[bot]")}],
            "commit": {"message": fixture["commit_message"]},
        }
    ]
    head_ref = str(fixture["head_ref"])
    return _build_transport(
        pulls=[_pull_stub(4049, head_ref=head_ref)],
        detail=_detail_stub(
            author=str(fixture.get("author") or "dependabot[bot]"),
            head_ref=head_ref,
        ),
        commits=commits,
        files=files,
    )


@pytest.mark.parametrize(
    "fixture_name,expected_reason",
    [
        ("phase0_numpy_range_4046.json", classifier.REASON_RANGE),
        ("phase0_prometheus_docker_4054.json", classifier.REASON_DOCKER),
        ("phase0_postgres_docker_4055.json", classifier.REASON_DOCKER),
        ("incomplete_api_payload.json", classifier.REASON_FACTS_INVALID),
    ],
)
def test_phase0_facts_invalid_cases_normalize_to_concrete_holds(
    fixture_name: str, expected_reason: str
) -> None:
    fixture = _load_fixture(fixture_name)
    outcome = _run(_transport_from_fixture(fixture))

    assert outcome.exit_code == 0
    assert len(outcome.rows) == 1
    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert row.action == "HOLD"
    assert row.merge_authorized is False
    assert expected_reason in row.reason_codes
    if expected_reason != classifier.REASON_FACTS_INVALID:
        assert classifier.REASON_FACTS_INVALID not in row.reason_codes


def test_docker_compose_digest_pin_parses_as_docker_change() -> None:
    # Tag suffix intentionally avoids host/user secret substrings in CI agents.
    patch = (
        "-    image: grafana/grafana:13.0.3-bookworm"
        "@sha256:7c1acd41225a05af53fa2af32a044a2a96cdef2540f2c415ee5b1e98fae99084\n"
        "+    image: grafana/grafana:13.1.1-bookworm"
        "@sha256:5a9df011defa8384ee01fc9b393854daecc6afb98132c66e2e658b3f564830e8\n"
    )
    outcome = _run(
        _build_transport(
            files=_files_stub(
                patch=patch,
                filename="infrastructure/compose/compose.red.yml",
            ),
            detail=_detail_stub(
                head_ref=(
                    "dependabot/docker_compose/infrastructure/compose/"
                    "grafana/grafana-13.1.1-bookworm"
                )
            ),
            commits=[
                {
                    "authors": [{"login": "dependabot[bot]"}],
                    "commit": {
                        "message": (
                            "updated-dependencies:\n"
                            "- dependency-name: grafana/grafana\n"
                            "  dependency-version: 13.1.1-bookworm\n"
                            "  dependency-type: direct:production\n"
                            "  update-type: version-update:semver-minor\n"
                        )
                    },
                }
            ],
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_DOCKER in row.reason_codes
    assert classifier.REASON_FACTS_INVALID not in row.reason_codes
    assert row.ecosystem == "docker-compose"


def test_date_version_remains_concrete_hold() -> None:
    outcome = _run(
        _build_transport(
            files=_files_stub(
                patch="-mcp-server-time==2026.6.4\n+mcp-server-time==2026.7.10\n",
                filename="requirements-mcp.txt",
            ),
            detail=_detail_stub(head_ref="dependabot/pip/mcp-server-time-2026.7.10"),
            commits=[
                {
                    "authors": [{"login": "dependabot[bot]"}],
                    "commit": {
                        "message": (
                            "updated-dependencies:\n"
                            "- dependency-name: mcp-server-time\n"
                            "  dependency-version: 2026.7.10\n"
                            "  dependency-type: direct:production\n"
                            "  update-type: version-update:semver-minor\n"
                        )
                    },
                }
            ],
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert classifier.REASON_DATE_VERSION in row.reason_codes
    assert classifier.REASON_FACTS_INVALID not in row.reason_codes


def test_title_or_branch_alone_never_eligible() -> None:
    outcome = _run(
        _build_transport(
            files=_files_stub(patch=None, filename="requirements-dev.txt"),
            detail=_detail_stub(head_ref="dependabot/pip/ruff-0.15.21"),
            commits=[
                {
                    "authors": [{"login": "dependabot[bot]"}],
                    "commit": {
                        "message": "deps(pip): bump ruff from 0.15.20 to 0.15.21"
                    },
                }
            ],
        )
    )

    row = outcome.rows[0]
    assert row.classification == "HOLD"
    assert row.merge_authorized is False
    assert classifier.REASON_ELIGIBLE not in row.reason_codes
    assert classifier.REASON_FACTS_INVALID in row.reason_codes


def test_report_module_has_no_mutation_helpers() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "gh pr merge" not in lowered
    assert "pull-requests: write" not in lowered
    assert "issues: write" not in lowered
    assert "add_label" not in lowered
    assert "create_comment" not in lowered
    assert "--method" in source
    assert "GET" in source
