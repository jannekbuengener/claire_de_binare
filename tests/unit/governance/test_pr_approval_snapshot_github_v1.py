"""Tests for approval snapshot adapters and gh api helpers (#4505)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from tools.agent_control.approval.protection_live_evidence import ProtectionReadError

from tools.agent_control.approval.adapter_capabilities import (
    GITHUB_APPROVAL_SNAPSHOT_EXPORT,
    adapter_capability_fingerprint,
)
from tools.agent_control.approval.context import (
    build_approval_context,
    default_repo_paths,
)
from tools.agent_control.approval.gh_api import (
    merge_check_runs_payload,
    merge_comment_pages,
)
from tools.agent_control.approval.snapshot_github import (
    _parse_steward_state,
    build_github_approval_snapshot,
)
from tools.agent_control.paths import REPO_ROOT

FIX = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "approval"


@pytest.mark.unit
def test_merge_comment_pages_slurped_arrays() -> None:
    payload = [
        [{"id": 1, "body": "a", "user": {"login": "bot", "type": "Bot"}}],
        [{"id": 2, "body": "b", "user": {"login": "bot", "type": "Bot"}}],
    ]
    merged = merge_comment_pages(payload)
    assert len(merged) == 2
    assert merged[0]["id"] == 1


@pytest.mark.unit
def test_merge_check_runs_payload_slurped_pages() -> None:
    payload = [
        {"check_runs": [{"name": "ci", "status": "completed"}]},
        {"check_runs": [{"name": "policy-gate", "status": "completed"}]},
    ]
    merged = merge_check_runs_payload(payload)
    assert len(merged) == 2
    assert {item["name"] for item in merged} == {"ci", "policy-gate"}


@pytest.mark.unit
def test_live_snapshot_adapter_uses_observed_capability_fingerprint() -> None:
    pr_payload = {
        "head": {"sha": "a" * 40},
        "base": {"sha": "b" * 40, "ref": "main"},
        "body": "",
        "draft": False,
    }
    protection_payload = {
        "required_status_checks": {
            "contexts": ["ci (Unit/Integration + Lint gesammelt)", "policy-gate"],
            "checks": [
                {"context": "ci (Unit/Integration + Lint gesammelt)"},
                {"context": "policy-gate"},
            ],
        }
    }
    with (
        patch(
            "tools.agent_control.approval.snapshot_github.gh_api_json",
            side_effect=[
                pr_payload,
                [],
                {"check_runs": []},
                {"statuses": []},
            ],
        ),
        patch(
            "tools.agent_control.approval.snapshot_github.probe_branch_protection_api",
            return_value=(protection_payload, None),
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
            pr_number=1, repository="o/r", repo_root=REPO_ROOT
        )
    assert snap["protection_source"] == "branch_protection_api"
    baseline = json.loads(
        (
            REPO_ROOT
            / "config/agent-control/capability-baselines/approval-dashboard-export.redacted.v1.json"
        ).read_text(encoding="utf-8")
    )
    observed = adapter_capability_fingerprint()
    assert snap["adapter"]["capability_fingerprint"] == observed
    assert observed == baseline["capability_fingerprint"]
    env = build_approval_context(snap, default_repo_paths(REPO_ROOT))
    assert "ADAPTER" not in env["drift"].get("sources", [])


@pytest.mark.unit
def test_protection_api_unreadable_without_attestation_stays_incomplete() -> None:
    head = "a" * 40
    base = "b" * 40
    pr_payload = {
        "head": {"sha": head},
        "base": {"sha": base, "ref": "main"},
        "body": "",
        "draft": False,
    }
    read_error = ProtectionReadError(
        endpoint="repos/o/r/branches/main/protection",
        http_status=403,
        gh_exit_code=1,
        message="403 Forbidden",
        hint="administration read required",
    )

    def _side_effect(argv: list[str]) -> Any:
        path = argv[1] if len(argv) > 1 else ""
        if path == "repos/o/r/pulls/1":
            return pr_payload
        if path == "repos/o/r/issues/1/comments":
            return []
        if path == f"repos/o/r/commits/{head}/check-runs":
            return {"check_runs": []}
        if path == f"repos/o/r/commits/{head}/status":
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
            pr_number=1, repository="o/r", repo_root=REPO_ROOT
        )

    assert snap["protection"]["required_checks"] == []
    assert "PROTECTION_READ_UNAVAILABLE" in snap.get("final_head_reason_codes", [])
    assert "PROTECTION_INCOMPLETE" in snap.get("final_head_reason_codes", [])


@pytest.mark.unit
def test_adapter_capability_fingerprint_detects_export_drift() -> None:
    drifted = dict(GITHUB_APPROVAL_SNAPSHOT_EXPORT)
    drifted["observed_capabilities"] = {
        **drifted["observed_capabilities"],
        "operations": ["only_one_operation"],
    }
    assert adapter_capability_fingerprint(drifted) != adapter_capability_fingerprint()


@pytest.mark.unit
def test_parse_steward_state_reads_frozen_from_refs_body() -> None:
    body = f"""<!-- cdb-batch-pr:v1
policy_id: cdb-pr-routing-v1
batch_key: docs-governance
lane: docs-governance
base_branch: main
validation_profile: docs-governance-v1
merge_mode: batch
steward_state: frozen
objective_key: pr-flow
planned_issues: #4505
contract_keys: pr-routing
risk_flags: none
-->

## CDB Batch Ledger

| Issue | Status | Commit | Targeted Validation | Risk Class | Restunsicherheit |
| --- | --- | --- | --- | --- | --- |
| #4505 | SLICE_DELIVERED | {"a" * 40} | unit + contract | governance | none |

Refs #4505
"""
    assert _parse_steward_state(body) == "frozen"


@pytest.mark.unit
def test_parse_steward_state_none_without_batch_marker() -> None:
    assert _parse_steward_state("Refs #4505") is None


@pytest.mark.unit
def test_parse_steward_state_none_on_malformed_marker() -> None:
    body = """<!-- cdb-batch-pr:v1
policy_id: cdb-pr-routing-v1
steward_state: frozen
-->
"""
    assert _parse_steward_state(body) is None


@pytest.mark.unit
def test_live_snapshot_review_decision_none_blocks() -> None:
    snap = json.loads(
        (FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8")
    )
    snap["pr"]["review_decision"] = None
    env = build_approval_context(snap, default_repo_paths())
    assert env["recommendation"] != "APPROVE_RECOMMENDED"
    assert "UNKNOWN_REVIEW_DECISION" in env["reason_codes"]


@pytest.mark.unit
def test_live_snapshot_changes_requested_blocks() -> None:
    snap = json.loads(
        (FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8")
    )
    snap["pr"]["review_decision"] = "CHANGES_REQUESTED"
    env = build_approval_context(snap, default_repo_paths())
    assert env["recommendation"] == "REQUEST_CHANGES"


@pytest.mark.unit
def test_live_snapshot_unknown_threads_blocks() -> None:
    snap = json.loads(
        (FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8")
    )
    snap["pr"]["blocking_threads"] = None
    snap["review_thread_state"] = "unknown"
    env = build_approval_context(snap, default_repo_paths())
    assert env["recommendation"] == "UNKNOWN"
    assert "BLOCKING_THREAD_UNKNOWN" in env["reason_codes"]


@pytest.mark.unit
def test_trust_policy_fixture_is_fail_closed_by_default() -> None:
    data = yaml.safe_load(
        (FIX / "acceptance_producer_trust_test.v1.yaml").read_text(encoding="utf-8")
    )
    conductor = data["producers"]["cdb-batch-merge-conductor"]
    assert conductor["require_performed_via_github_app"] is True
    assert conductor["trusted_github_app_slugs"]


@pytest.mark.unit
def test_snapshot_pr_binding_rejects_mismatch() -> None:
    from tools.agent_control.approval.codes import ApprovalError
    from tools.agent_control.approval.context import validate_snapshot_pr_binding

    snap = json.loads(
        (FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8")
    )
    snap["pr"]["number"] = 99
    with pytest.raises(ApprovalError, match="APPROVAL_SNAPSHOT_PR_MISMATCH"):
        validate_snapshot_pr_binding(snap, 1)
    data = yaml.safe_load(
        (FIX / "acceptance_producer_trust_test.v1.yaml").read_text(encoding="utf-8")
    )
    conductor = data["producers"]["cdb-batch-merge-conductor"]
    assert conductor["require_performed_via_github_app"] is True
    assert conductor["trusted_github_app_slugs"]
