"""Contract tests for cdb-batch-merge-conductor (#4210 / #4411)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "config" / "governance" / "pr-acceptance-policy.v1.yaml"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "pr_acceptance_skill_family.v1.schema.json"
SKILL = ROOT / "docs" / "skills" / "cdb-batch-merge-conductor" / "SKILL.md"

PHASES = [
    "FREEZE",
    "MAIN_INTEGRATION",
    "FINAL_VALIDATION",
    "HANDOFF_APPROVAL",
    "HANDOFF_SESSION_CLOSE",
]
BLOCKCODES = [
    "BLOCKED_SCOPE_OR_REVIEW",
    "BLOCKED_HEAD_BASE_DRIFT",
    "BLOCKED_LOCAL_VALIDATION",
    "BLOCKED_REQUIRED_STATUS",
    "BLOCKED_AUTH_PUBLISHER",
    "BLOCKED_MERGE_METHOD",
    "BLOCKED_ISSUE_CLOSEOUT",
]
DELEGATES = [
    "cdb-pr-completeness-review",
    "cdb-ci-cd-guard",
]


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_no_separate_merge_go_or_human_authority_fields() -> None:
    text = _skill()
    assert "human_merge_authorization" in text
    assert "No field `human_merge_authorization`" in text
    assert "BLOCKED_HUMAN_AUTHORITY" in text
    assert "No status `BLOCKED_HUMAN_AUTHORITY`" in text
    assert "No separate Human" in text
    assert "allowed status `BLOCKED_HUMAN_AUTHORITY`" not in text
    assert "requires human_merge_authorization" not in text.lower()


def test_final_head_ready_not_merge_executor() -> None:
    text = _skill()
    assert "FINAL_HEAD_READY_FOR_APPROVAL" in text
    assert "cdb_final_head_pr_approval_gate" in text
    assert "merge_policy_ci_gate.md" in text
    assert "DONE_PR_OPEN_MERGE_HANDOFF" in text
    assert "--admin" in text
    # Conductor must not execute merge itself
    assert "Execute regular squash-merge" not in text
    assert "4. `MERGE`" not in text
    assert "merge_executed" not in text


def test_freeze_prevents_new_slices() -> None:
    text = _skill()
    assert "FREEZE" in text
    assert "no further slices" in text.lower() or "reject new slices" in text.lower()
    assert "FROZEN" in text


def test_main_integration_rebinds_sha_and_drift_forces_completeness() -> None:
    text = _skill()
    assert "MAIN_INTEGRATION" in text
    assert "origin/main" in text or "current main" in text.lower()
    assert "cdb-pr-completeness-review" in text
    assert "invalidates" in text.lower() or "forces a fresh" in text


def test_app_check_run_publish_and_no_admin() -> None:
    text = _skill()
    assert "policy-gate" in text
    assert "hosted Required" in text
    assert "--admin" in text
    assert "Fake-Green" in text


def test_missing_capability_handoff_not_admin() -> None:
    text = _skill()
    assert "DONE_PR_OPEN_MERGE_HANDOFF" in text
    assert "never `--admin`" in text or "never --admin" in text.replace("`", "")
    forbidden = _policy()["delegation_matrix"]["cdb-batch-merge-conductor"]["forbidden"]
    assert "admin_merge" in forbidden
    assert "human_merge_authorization_field" in forbidden
    assert "merge_execution" in forbidden
    assert "approve_pr" in forbidden


def test_no_closure_of_undelivered_ledger_rows() -> None:
    text = _skill()
    assert "SLICE_DELIVERED" in text
    assert "undelivered" in text.lower()
    assert "cdb-session-close" in text


def test_delegation_to_ci_guard_not_session_close_as_merge_owner() -> None:
    policy = _policy()
    text = _skill()
    delegates = policy["delegation_matrix"]["cdb-batch-merge-conductor"]["delegates_to"]
    assert delegates == DELEGATES
    for name in DELEGATES:
        assert name in text
    assert (
        policy["delegation_matrix"]["cdb-batch-merge-conductor"]["success_decision"]
        == "FINAL_HEAD_READY_FOR_APPROVAL"
    )
    assert (
        policy["delegation_matrix"]["cdb-batch-merge-conductor"]["handoff_role"]
        == "cdb_final_head_pr_approval_gate"
    )


def test_phases_and_blockcodes_parity_policy_schema_skill() -> None:
    policy = _policy()
    schema = _schema()
    text = _skill()
    assert policy["conductor_blockcodes"] == BLOCKCODES
    assert policy["conductor_phases"] == PHASES
    phase_enum = schema["$defs"]["BatchMergeConductorResult"]["properties"]["phase"][
        "enum"
    ]
    assert phase_enum == PHASES
    for phase in PHASES:
        assert phase in text
    for code in BLOCKCODES:
        assert code in text
    block_enum = schema["$defs"]["BatchMergeConductorResult"]["properties"][
        "block_codes"
    ]["items"]["enum"]
    assert block_enum == BLOCKCODES
    assert "HOLD_SCOPE_OR_REVIEW" in text
    assert "HOLD_MAIN_OR_HEAD_DRIFT" in text
    assert (
        "merge_executed"
        not in schema["$defs"]["BatchMergeConductorResult"]["properties"]
    )


def test_canonical_header_present() -> None:
    text = _skill()
    assert "Surface: docs (canonical)" in text
    assert "Sync Status: canonical" in text
    assert "cdb-batch-merge-conductor" in text
    assert "<!-- cdb-pr-acceptance:v1 -->" in text
