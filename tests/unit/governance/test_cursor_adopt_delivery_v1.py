"""
test_id: tc_agent_control_cursor_adopt_delivery_v1_001
test_name: agent_control_cursor_adopt_delivery_v1
test_type: Bauteil-Test
cdb_area: governance
rule_ref: docs/contracts/agent_control/CDB_CURSOR_DELIVERY_ADOPTION_V1.md
decision_ref: cdb.cursor_delivery_adoption.v1
issue_ref: 4258
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.agent_control.cli import main as cli_main
from tools.agent_control.cursor_adopt_delivery import (
    AUTHORITY_LIMITS,
    CURSOR_AUTHOR_EMAIL,
    CURSOR_AUTHOR_LOGIN,
    IMMUTABLE_FAILED_RUN_IDS,
    CursorAdoptError,
    adopt_cursor_delivery,
    build_adoption_receipt,
    build_approval_agent_handoff,
    compute_adoption_digest,
    validate_adoption_receipt,
    verify_cursor_cloud_delivery,
)
from tools.agent_control.paths import REPO_ROOT

AGENT_ID = "bc-1d8c87d1-249a-46ab-a5b0-5734f8fe1519"
HEAD = "01a65ae6e1b55648da1cf62c3de8a4ec2e3a926b"
BASE = "ec663f4f542827775721f077b255b678bd205894"
BRANCH = "cloud-cursor/dev-env-setup-1519"
REPO = "jannekbuengener/Claire_de_Binare"
PR = 4345


def _pr_payload(**overrides: object) -> dict:
    data = {
        "number": PR,
        "state": "OPEN",
        "title": "chore(devenv): Cursor Cloud environment setup + verification",
        "body": (
            "<!-- CURSOR_AGENT_PR_BODY_BEGIN -->\n"
            f"agent {AGENT_ID}\n"
            "<!-- CURSOR_AGENT_PR_BODY_END -->\n"
            f'<a href="https://cursor.com/agents/{AGENT_ID}">Open</a>'
        ),
        "headRefOid": HEAD,
        "baseRefOid": BASE,
        "headRefName": BRANCH,
        "baseRefName": "main",
        "url": f"https://github.com/{REPO}/pull/{PR}",
        "author": {"login": "jannekbuengener"},
        "commits": [{"oid": HEAD}],
        "statusCheckRollup": [{"conclusion": "SUCCESS", "name": "ci"}],
        "isDraft": False,
        "mergeable": "MERGEABLE",
    }
    data.update(overrides)
    return data


def _commit_payload(
    *,
    login: str = CURSOR_AUTHOR_LOGIN,
    email: str = CURSOR_AUTHOR_EMAIL,
) -> dict:
    return {
        "sha": HEAD,
        "author": {"login": login},
        "commit": {
            "author": {"email": email, "name": "Cursor Agent"},
            "message": (
                "docs(agents): note Docker-dependent unit tests\n\n"
                "Co-authored-by: Jannek Büngener <jannekbungener@gmail.com>"
            ),
        },
    }


def _make_runner(
    *,
    pr: dict | None = None,
    commit: dict | None = None,
    tip: str | None = HEAD,
    branch_404: bool = False,
) -> object:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> dict:
        calls.append(list(argv))
        # Reject any mutating argv patterns.
        joined = " ".join(argv)
        assert "pr create" not in joined
        assert "pr merge" not in joined
        assert "pr comment" not in joined
        if argv[:2] == ["gh", "pr"] and "view" in argv:
            return pr if pr is not None else _pr_payload()
        if argv[:2] == ["gh", "api"] and "/git/ref/heads/" in argv[2]:
            if branch_404:
                raise CursorAdoptError("ADOPT_GITHUB_QUERY_FAILED", "404")
            return {"object": {"sha": tip or HEAD, "type": "commit"}}
        if argv[:2] == ["gh", "api"] and "/commits/" in argv[2]:
            return commit if commit is not None else _commit_payload()
        raise AssertionError(f"unexpected gh argv: {argv}")

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def test_valid_cursor_agent_commit_and_pr_accepted() -> None:
    runner = _make_runner()
    verified = verify_cursor_cloud_delivery(
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        expected_branch=BRANCH,
        runner=runner,
    )
    assert verified["pr_body_agent_ref_present"] is True
    assert verified["commit_agent_author_match"] is True
    assert verified["branch_tip_matches_expected"] is True


def test_footer_without_commit_provenance_rejected() -> None:
    runner = _make_runner(commit=_commit_payload(login="someone", email="a@b.c"))
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head=HEAD,
            runner=runner,
        )
    assert exc.value.code == "HOLD_CURSOR_DELIVERY_PROVENANCE_INSUFFICIENT"


def test_wrong_agent_rejected() -> None:
    runner = _make_runner()
    with pytest.raises(CursorAdoptError):
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id="bc-00000000-0000-0000-0000-000000000000",
            delivery_pr=PR,
            expected_head=HEAD,
            runner=runner,
        )


def test_wrong_repository_rejected() -> None:
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository="not-a-repo",
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head=HEAD,
            runner=_make_runner(),
        )
    assert exc.value.code == "ADOPT_REPO_INVALID"


def test_wrong_branch_rejected() -> None:
    runner = _make_runner()
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head=HEAD,
            expected_branch="cloud-cursor/other",
            runner=runner,
        )
    assert exc.value.code == "ADOPT_BRANCH_MISMATCH"


def test_wrong_head_rejected() -> None:
    runner = _make_runner()
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head="ffffffffffffffffffffffffffffffffffffffff",
            runner=runner,
        )
    assert exc.value.code == "ADOPT_HEAD_DRIFT"


def test_missing_pr_body_agent_ref_rejected() -> None:
    runner = _make_runner(pr=_pr_payload(body="no agent id here"))
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head=HEAD,
            runner=runner,
        )
    assert "PR body" in exc.value.message


def test_phantom_branch_rejected() -> None:
    runner = _make_runner(branch_404=True)
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head=HEAD,
            runner=runner,
        )
    assert exc.value.code == "ADOPT_GITHUB_QUERY_FAILED"


def test_branch_tip_drift_rejected() -> None:
    runner = _make_runner(tip="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head=HEAD,
            runner=runner,
        )
    assert exc.value.code == "ADOPT_PHANTOM_OR_DRIFT_BRANCH"


def test_idempotent_adoption_same_digest() -> None:
    runner = _make_runner()
    verified = verify_cursor_cloud_delivery(
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        expected_branch=BRANCH,
        runner=runner,
    )
    r1 = build_adoption_receipt(
        issue_number=4258,
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        expected_branch=BRANCH,
        verification=verified,
        repo_root=REPO_ROOT,
    )
    r2 = build_adoption_receipt(
        issue_number=4258,
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        expected_branch=BRANCH,
        verification=verified,
        repo_root=REPO_ROOT,
    )
    assert r1["canonical_digest"] == r2["canonical_digest"]
    assert r1["adoption_id"] == r2["adoption_id"]
    assert r1["adopted_delivery_id"] == r2["adopted_delivery_id"]
    assert compute_adoption_digest(r1) == r1["canonical_digest"]


def test_other_head_produces_drift_hold() -> None:
    runner = _make_runner()
    with pytest.raises(CursorAdoptError) as exc:
        verify_cursor_cloud_delivery(
            repository=REPO,
            cursor_agent_id=AGENT_ID,
            delivery_pr=PR,
            expected_head="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            runner=runner,
        )
    assert exc.value.code == "ADOPT_HEAD_DRIFT"


def test_original_and_adoption_ids_remain_separate() -> None:
    verified = verify_cursor_cloud_delivery(
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        runner=_make_runner(),
    )
    receipt = build_adoption_receipt(
        issue_number=4258,
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        verification=verified,
        repo_root=REPO_ROOT,
    )
    assert receipt["adoption_id"].startswith("cad-")
    assert receipt["adopted_delivery_id"].startswith("add-")
    assert receipt["adoption_id"] != receipt["adopted_delivery_id"]
    for run_id in IMMUTABLE_FAILED_RUN_IDS:
        assert run_id in receipt["original_cdb_run_ids"]
        assert run_id not in {
            receipt["adoption_id"],
            receipt["adopted_delivery_id"],
        }


def test_no_invented_dispatch_evidence_and_authority_limits() -> None:
    verified = verify_cursor_cloud_delivery(
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        runner=_make_runner(),
    )
    receipt = build_adoption_receipt(
        issue_number=4258,
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        verification=verified,
        repo_root=REPO_ROOT,
    )
    assert receipt["provider_dispatch_proven"] is False
    assert receipt["authority_limits"] == AUTHORITY_LIMITS
    assert all(v is False for v in receipt["authority_limits"].values())
    with pytest.raises(CursorAdoptError):
        bad = copy.deepcopy(receipt)
        bad["provider_dispatch_proven"] = True
        bad = {**bad, "canonical_digest": compute_adoption_digest(bad)}
        # re-attach would still fail validate
        from tools.agent_control.cursor_adopt_delivery import attach_adoption_digest

        bad = attach_adoption_digest(
            {k: v for k, v in bad.items() if k != "canonical_digest"}
        )
        bad["provider_dispatch_proven"] = True
        validate_adoption_receipt(bad, repo_root=REPO_ROOT)


def test_approval_context_exact_head_and_handoff(tmp_path: Path) -> None:
    result = adopt_cursor_delivery(
        issue_number=4258,
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        expected_branch=BRANCH,
        out_dir=tmp_path,
        runner=_make_runner(),
        repo_root=REPO_ROOT,
        build_approval=True,
    )
    receipt = result["adoption_receipt"]
    envelope = result["approval_context"]
    handoff = result["approval_handoff"]
    assert envelope["subject"]["head_sha"] == HEAD
    assert envelope["subject"]["pr_number"] == PR
    assert envelope["authority_limits"]["merge"] is False
    assert "APPROVED" not in (
        envelope.get("recommendation"),
        handoff.get("desired_state"),
    )
    assert handoff["verdict"] == "APPROVAL_HANDOFF_PREPARED_NOT_EXECUTED"
    assert handoff["bindings"]["adoption_digest"] == receipt["canonical_digest"]
    assert handoff["bindings"]["approval_context_digest"] == envelope["context_digest"]
    assert result["acceptance_matrix"]["final_verdict"] == (
        "PARTIAL_4258_ACCEPTANCE_L2_L3_PROVEN"
    )
    assert result["http_posts_to_cursor"] == 0
    assert result["github_writes"] == 0


def test_approval_head_drift_blocks_via_detect() -> None:
    from tools.agent_control.approval.evaluate import detect_stale_head

    reasons = detect_stale_head(
        {"pr_number": PR, "head_sha": HEAD, "base_sha": BASE},
        {
            "pr": {"number": PR, "head_sha": HEAD, "base_sha": BASE},
            "checks": [
                {
                    "name": "ci (Unit/Integration + Lint gesammelt)",
                    "mechanism": "check_run",
                    "status": "completed",
                    "conclusion": "success",
                    "app_id": None,
                    "source_sha": "cccccccccccccccccccccccccccccccccccccccc",
                }
            ],
        },
    )
    assert any("STALE" in r for r in reasons)


def test_wrong_issue_not_bound_in_handoff() -> None:
    verified = verify_cursor_cloud_delivery(
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        runner=_make_runner(),
    )
    receipt = build_adoption_receipt(
        issue_number=4258,
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        verification=verified,
        repo_root=REPO_ROOT,
    )
    handoff = build_approval_agent_handoff(
        approval_context={
            "subject": {"pr_number": PR, "head_sha": HEAD, "base_sha": BASE},
            "context_digest": "sha256:" + "a" * 64,
            "recommendation": "HOLD",
        },
        adoption_receipt=receipt,
    )
    assert handoff["bindings"]["issue_number"] == 4258
    assert handoff["bindings"]["issue_number"] != 4374


def test_failed_run_fixtures_unchanged() -> None:
    # Immutable constants must remain the historically documented run IDs.
    assert IMMUTABLE_FAILED_RUN_IDS == (
        "run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b",
        "run-c2c3898b-af9e-4f73-ad91-830f600561b9",
    )
    evidence = (
        REPO_ROOT
        / "docs"
        / "evidence"
        / "agent_control"
        / "CURSOR_CLOUD_DUAL_RUN_FAILURE_4258.md"
    )
    text = evidence.read_text(encoding="utf-8")
    for run_id in IMMUTABLE_FAILED_RUN_IDS:
        assert run_id in text


def test_no_secrets_in_receipt() -> None:
    verified = verify_cursor_cloud_delivery(
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        runner=_make_runner(),
    )
    receipt = build_adoption_receipt(
        issue_number=4258,
        repository=REPO,
        cursor_agent_id=AGENT_ID,
        delivery_pr=PR,
        expected_head=HEAD,
        verification=verified,
        repo_root=REPO_ROOT,
    )
    blob = json.dumps(receipt)
    assert "CURSOR_API_KEY" not in blob
    assert "ghp_" not in blob
    assert "-----BEGIN" not in blob
    assert "D:\\" not in blob
    assert "/Users/" not in blob


def test_cli_help_lists_adopt_command() -> None:
    # Smoke: parser accepts the subcommand (invalid args → non-zero).
    rc = cli_main(
        [
            "pilot",
            "cursor-adopt-delivery",
            "--issue",
            "4258",
            "--cursor-agent-id",
            "bad",
            "--delivery-pr",
            "4345",
            "--expected-head",
            HEAD,
            "--skip-approval",
        ]
    )
    assert rc != 0
