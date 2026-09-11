"""Tests for trusted protection live attestation (#4505)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

import yaml

from tools.agent_control.approval.context import (
    build_approval_context,
    default_repo_paths,
)
from tools.agent_control.approval.protection_live_evidence import (
    EVIDENCE_MARKER,
    PRODUCER,
    ProtectionReadError,
    build_protection_live_envelope,
    format_protection_attestation_comment_body,
    resolve_protection_live_attestation,
)
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.snapshot_github import build_github_approval_snapshot
from tools.agent_control.paths import REPO_ROOT

BASE = "b" * 40
HEAD = "a" * 40
REPO = "jannekbuengener/Claire_de_Binare"
TRUST_POLICY = yaml.safe_load(
    (
        REPO_ROOT
        / "config/agent-control/policies/approval/acceptance_producer_trust.v1.yaml"
    ).read_text(encoding="utf-8")
)


def _protection_payload(*, contexts: list[str] | None = None) -> dict[str, Any]:
    names = contexts or [
        "ci (Unit/Integration + Lint gesammelt)",
        "policy-gate",
    ]
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": names,
            "checks": [{"context": name} for name in names],
        }
    }


def _attestation_comment(
    *,
    comment_id: int,
    base_sha: str = BASE,
    contexts: list[str] | None = None,
    trusted: bool = True,
    observed_at: str | None = None,
) -> dict[str, Any]:
    envelope = build_protection_live_envelope(
        repository=REPO,
        base_ref="main",
        base_sha=base_sha,
        protection_payload=_protection_payload(contexts=contexts),
        observed_at=observed_at,
    )
    body = format_protection_attestation_comment_body(envelope)
    user = {"login": "cdb-local-ci[bot]", "type": "Bot"}
    app = {"slug": "cdb-local-ci"} if trusted else None
    return {
        "id": comment_id,
        "body": body,
        "user": user,
        "performed_via_github_app": app,
    }


@pytest.mark.unit
def test_observed_check_run_does_not_substitute_protection_when_api_unreadable() -> (
    None
):
    """Negative case: observed hosted check on HEAD must not fake-green protection (#4505)."""
    pr_payload = {
        "head": {"sha": HEAD},
        "base": {"sha": BASE, "ref": "main"},
        "body": "",
        "draft": False,
    }
    read_error = ProtectionReadError(
        endpoint=f"repos/{REPO}/branches/main/protection",
        http_status=403,
        gh_exit_code=1,
        message="403 Forbidden",
        hint="administration read required",
    )

    def _side_effect(argv: list[str]) -> Any:
        path = argv[1] if len(argv) > 1 else ""
        if path == f"repos/{REPO}/pulls/1":
            return pr_payload
        if path == f"repos/{REPO}/issues/1/comments":
            return []
        if path == f"repos/{REPO}/commits/{HEAD}/check-runs":
            return {
                "check_runs": [
                    {
                        "name": "ci (Unit/Integration + Lint gesammelt)",
                        "status": "completed",
                        "conclusion": "success",
                        "head_sha": HEAD,
                        "app": {"id": 4410232},
                    }
                ]
            }
        if path == f"repos/{REPO}/commits/{HEAD}/status":
            return {"statuses": []}
        raise AssertionError(f"unexpected gh api: {argv}")

    with (
        patch(
            "tools.agent_control.approval.snapshot_github.gh_api_json",
            side_effect=_side_effect,
        ),
        patch(
            "tools.agent_control.approval.snapshot_github.probe_branch_protection_api",
            return_value=(None, read_error),
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_review_decision",
            return_value="APPROVED",
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_blocking_thread_count",
            return_value=(0, True),
        ),
    ):
        snap = build_github_approval_snapshot(
            pr_number=1, repository=REPO, repo_root=REPO_ROOT
        )

    assert snap["protection"]["required_checks"] == []
    assert snap.get("protection_source") is None
    assert "PROTECTION_READ_UNAVAILABLE" in snap["final_head_reason_codes"]
    assert "PROTECTION_INCOMPLETE" in snap["final_head_reason_codes"]
    env = build_approval_context(snap, default_repo_paths(REPO_ROOT))
    assert env["recommendation"] == "BLOCKED"
    assert "PROTECTION_READ_UNAVAILABLE" in env["reason_codes"]


@pytest.mark.unit
def test_trusted_attestation_used_when_branch_protection_api_unreadable() -> None:
    pr_payload = {
        "head": {"sha": HEAD},
        "base": {"sha": BASE, "ref": "main"},
        "body": "",
        "draft": False,
    }
    read_error = ProtectionReadError(
        endpoint=f"repos/{REPO}/branches/main/protection",
        http_status=403,
        gh_exit_code=1,
        message="403 Forbidden",
        hint="administration read required",
    )

    def _side_effect(argv: list[str]) -> Any:
        path = argv[1] if len(argv) > 1 else ""
        if path == f"repos/{REPO}/pulls/1":
            return pr_payload
        if path == f"repos/{REPO}/issues/1/comments":
            return [_attestation_comment(comment_id=99)]
        if path == f"repos/{REPO}/commits/{HEAD}/check-runs":
            return {"check_runs": []}
        if path == f"repos/{REPO}/commits/{HEAD}/status":
            return {"statuses": []}
        raise AssertionError(f"unexpected gh api: {argv}")

    with (
        patch(
            "tools.agent_control.approval.snapshot_github.gh_api_json",
            side_effect=_side_effect,
        ),
        patch(
            "tools.agent_control.approval.snapshot_github.probe_branch_protection_api",
            return_value=(None, read_error),
        ),
        patch(
            "tools.agent_control.approval.protection_live_evidence.load_producer_trust_policy",
            return_value=TRUST_POLICY,
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_review_decision",
            return_value="APPROVED",
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_blocking_thread_count",
            return_value=(0, True),
        ),
    ):
        snap = build_github_approval_snapshot(
            pr_number=1, repository=REPO, repo_root=REPO_ROOT
        )

    assert snap["protection_source"] == "trusted_attestation"
    assert snap["protection"]["required_checks"][0]["name"] == (
        "ci (Unit/Integration + Lint gesammelt)"
    )
    assert "strict" not in snap["protection"]
    assert snap["protection_read"]["strict"] is True
    assert "PROTECTION_READ_UNAVAILABLE" not in snap.get("final_head_reason_codes", [])
    assert "PROTECTION_INCOMPLETE" not in snap.get("final_head_reason_codes", [])


@pytest.mark.unit
def test_attested_protection_view_matches_api_fingerprint() -> None:
    from tools.agent_control.approval.drift import protection_view_fingerprint

    api_view = {
        "required_checks": [
            {
                "name": "ci (Unit/Integration + Lint gesammelt)",
                "app_id": None,
                "mechanism": "check_run",
            },
            {"name": "policy-gate", "app_id": None, "mechanism": "check_run"},
        ]
    }
    attested_view = {
        "required_checks": [
            {
                "name": "ci (Unit/Integration + Lint gesammelt)",
                "app_id": None,
                "mechanism": "check_run",
            },
            {"name": "policy-gate", "app_id": None, "mechanism": "check_run"},
        ]
    }
    assert protection_view_fingerprint(api_view) == protection_view_fingerprint(
        attested_view
    )


@pytest.mark.unit
def test_stale_attestation_observed_at_is_ignored() -> None:
    comments = [
        CommentRecord.from_github_issue_comment(
            _attestation_comment(
                comment_id=4,
                base_sha=BASE,
                observed_at="2020-01-01T00:00:00Z",
            )
        )
    ]
    with patch(
        "tools.agent_control.approval.protection_live_evidence.load_producer_trust_policy",
        return_value=TRUST_POLICY,
    ):
        resolved = resolve_protection_live_attestation(
            comments=comments,
            repository=REPO,
            live_base_sha=BASE,
            live_base_ref="main",
            repo_root=REPO_ROOT,
        )
    assert resolved is None


@pytest.mark.unit
def test_readable_incomplete_protection_does_not_use_attestation() -> None:
    pr_payload = {
        "head": {"sha": HEAD},
        "base": {"sha": BASE, "ref": "main"},
        "body": "",
        "draft": False,
    }

    def _side_effect(argv: list[str]) -> Any:
        path = argv[1] if len(argv) > 1 else ""
        if path == f"repos/{REPO}/pulls/1":
            return pr_payload
        if path == f"repos/{REPO}/issues/1/comments":
            return [_attestation_comment(comment_id=77)]
        if path == f"repos/{REPO}/commits/{HEAD}/check-runs":
            return {"check_runs": []}
        if path == f"repos/{REPO}/commits/{HEAD}/status":
            return {"statuses": []}
        raise AssertionError(f"unexpected gh api: {argv}")

    with (
        patch(
            "tools.agent_control.approval.snapshot_github.gh_api_json",
            side_effect=_side_effect,
        ),
        patch(
            "tools.agent_control.approval.snapshot_github.probe_branch_protection_api",
            return_value=({"required_status_checks": None}, None),
        ),
        patch(
            "tools.agent_control.approval.protection_live_evidence.load_producer_trust_policy",
            return_value=TRUST_POLICY,
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_review_decision",
            return_value="APPROVED",
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_blocking_thread_count",
            return_value=(0, True),
        ),
    ):
        snap = build_github_approval_snapshot(
            pr_number=1, repository=REPO, repo_root=REPO_ROOT
        )

    assert snap.get("protection_source") != "trusted_attestation"
    assert "PROTECTION_INCOMPLETE" in snap.get("final_head_reason_codes", [])
    assert "PROTECTION_READ_UNAVAILABLE" not in snap.get("final_head_reason_codes", [])


@pytest.mark.unit
def test_branch_not_protected_404_does_not_use_attestation() -> None:
    pr_payload = {
        "head": {"sha": HEAD},
        "base": {"sha": BASE, "ref": "main"},
        "body": "",
        "draft": False,
    }
    read_error = ProtectionReadError(
        endpoint=f"repos/{REPO}/branches/main/protection",
        http_status=404,
        gh_exit_code=1,
        message="Branch not protected",
        hint="enable branch protection or publish fresh attestation",
    )

    def _side_effect(argv: list[str]) -> Any:
        path = argv[1] if len(argv) > 1 else ""
        if path == f"repos/{REPO}/pulls/1":
            return pr_payload
        if path == f"repos/{REPO}/issues/1/comments":
            return [_attestation_comment(comment_id=88)]
        if path == f"repos/{REPO}/commits/{HEAD}/check-runs":
            return {"check_runs": []}
        if path == f"repos/{REPO}/commits/{HEAD}/status":
            return {"statuses": []}
        raise AssertionError(f"unexpected gh api: {argv}")

    with (
        patch(
            "tools.agent_control.approval.snapshot_github.gh_api_json",
            side_effect=_side_effect,
        ),
        patch(
            "tools.agent_control.approval.snapshot_github.probe_branch_protection_api",
            return_value=(None, read_error),
        ),
        patch(
            "tools.agent_control.approval.protection_live_evidence.load_producer_trust_policy",
            return_value=TRUST_POLICY,
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_review_decision",
            return_value="APPROVED",
        ),
        patch(
            "tools.agent_control.approval.snapshot_github._fetch_blocking_thread_count",
            return_value=(0, True),
        ),
    ):
        snap = build_github_approval_snapshot(
            pr_number=1, repository=REPO, repo_root=REPO_ROOT
        )

    assert snap.get("protection_source") != "trusted_attestation"
    assert "PROTECTION_INCOMPLETE" in snap.get("final_head_reason_codes", [])
    assert "PROTECTION_READ_UNAVAILABLE" not in snap.get("final_head_reason_codes", [])


@pytest.mark.unit
def test_stale_attestation_wrong_base_sha_is_ignored() -> None:
    comments = [
        CommentRecord.from_github_issue_comment(
            _attestation_comment(comment_id=1, base_sha="c" * 40)
        )
    ]
    resolved = resolve_protection_live_attestation(
        comments=comments,
        repository=REPO,
        live_base_sha=BASE,
        live_base_ref="main",
        repo_root=REPO_ROOT,
    )
    assert resolved is None


@pytest.mark.unit
def test_untrusted_user_attestation_is_ignored() -> None:
    raw = _attestation_comment(comment_id=2, trusted=False)
    raw["user"] = {"login": "jannekbuengener", "type": "User"}
    raw["performed_via_github_app"] = None
    comments = [CommentRecord.from_github_issue_comment(raw)]
    with patch(
        "tools.agent_control.approval.protection_live_evidence.load_producer_trust_policy",
        return_value=TRUST_POLICY,
    ):
        resolved = resolve_protection_live_attestation(
            comments=comments,
            repository=REPO,
            live_base_sha=BASE,
            live_base_ref="main",
            repo_root=REPO_ROOT,
        )
    assert resolved is None


@pytest.mark.unit
def test_trusted_attestation_resolves_for_cdb_local_ci_app() -> None:
    comments = [
        CommentRecord.from_github_issue_comment(_attestation_comment(comment_id=3))
    ]
    with patch(
        "tools.agent_control.approval.protection_live_evidence.load_producer_trust_policy",
        return_value=TRUST_POLICY,
    ):
        resolved = resolve_protection_live_attestation(
            comments=comments,
            repository=REPO,
            live_base_sha=BASE,
            live_base_ref="main",
            repo_root=REPO_ROOT,
        )
    assert resolved is not None
    assert (
        resolved.required_checks[0]["name"] == "ci (Unit/Integration + Lint gesammelt)"
    )


@pytest.mark.unit
def test_attestation_with_extra_required_context_is_authoritative() -> None:
    """When attestation lists an extra required check, evaluator must not fake-green."""
    envelope = build_protection_live_envelope(
        repository=REPO,
        base_ref="main",
        base_sha=BASE,
        protection_payload=_protection_payload(
            contexts=["ci (Unit/Integration + Lint gesammelt)", "extra-required-check"]
        ),
    )
    body = format_protection_attestation_comment_body(envelope)
    assert EVIDENCE_MARKER in body
    assert PRODUCER == envelope["producer"]
    checks = envelope["protection"]["required_checks"]
    assert len(checks) == 2
    assert {item["name"] for item in checks} == {
        "ci (Unit/Integration + Lint gesammelt)",
        "extra-required-check",
    }
