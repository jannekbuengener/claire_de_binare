"""Contract tests for CDB PR-acceptance policy and schema (#4207/#4208)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "config" / "governance" / "pr-acceptance-policy.v1.yaml"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "pr_acceptance_skill_family.v1.schema.json"
WIRING_SKILL = ROOT / "docs" / "skills" / "cdb-integration-wiring-audit" / "SKILL.md"
GAP_SKILL = ROOT / "docs" / "skills" / "cdb-pr-gap-classifier" / "SKILL.md"
COMPLETENESS_SKILL = (
    ROOT / "docs" / "skills" / "cdb-pr-completeness-review" / "SKILL.md"
)
CONDUCTOR_SKILL = ROOT / "docs" / "skills" / "cdb-batch-merge-conductor" / "SKILL.md"

SHA_RE = re.compile(r"^[a-f0-9]{40}$")
LIFECYCLE_STATES = [
    "ACCEPTING_SLICES",
    "SLICE_IN_REVIEW",
    "COMPLETENESS_REVIEW",
    "EXTENSION_REQUIRED",
    "MERGE_CANDIDATE",
    "FROZEN",
    "FINAL_VALIDATION",
    "FINAL_HEAD_READY_FOR_APPROVAL",
    "MERGED",
    "BLOCKED",
]
WIRING_VERDICTS = [
    "UNREACHABLE_IMPLEMENTATION",
    "BLOCKED_UNCLEAR_INTEGRATION",
    "WIRING_REQUIRED_IN_CURRENT_PR",
    "WIRING_FOLLOWUP_ALLOWED",
    "WIRED_AND_REACHABLE",
]
GAP_CLASSES = [
    "MUST_FIX_IN_CURRENT_PR",
    "FOLLOWUP_AFTER_MERGE",
    "SEPARATE_DEDICATED_PR",
    "PARKED_NOT_ACTIVE",
    "NOT_A_REAL_GAP",
]
PRODUCERS = [
    "cdb-integration-wiring-audit",
    "cdb-pr-gap-classifier",
    "cdb-pr-completeness-review",
    "cdb-batch-merge-conductor",
]


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_policy_parses_as_json_compatible_yaml() -> None:
    policy = _policy()
    assert policy["policy_id"] == "cdb-pr-acceptance-v1"
    assert policy["schema_version"] == "cdb-pr-acceptance-policy/v1"
    assert policy["evidence_marker"] == "<!-- cdb-pr-acceptance:v1 -->"


def test_lifecycle_states_and_transitions() -> None:
    policy = _policy()
    states = policy["lifecycle"]["states"]
    assert states == LIFECYCLE_STATES
    allowed = policy["lifecycle"]["allowed_transitions"]
    assert set(allowed) == set(LIFECYCLE_STATES)
    assert "MERGE_CANDIDATE" not in allowed["ACCEPTING_SLICES"]
    assert "COMPLETENESS_REVIEW" in allowed["ACCEPTING_SLICES"]
    forbidden = {tuple(pair) for pair in policy["lifecycle"]["forbidden_transitions"]}
    assert ("ACCEPTING_SLICES", "MERGE_CANDIDATE") in forbidden
    assert ("EXTENSION_REQUIRED", "MERGE_CANDIDATE") in forbidden
    note = policy["lifecycle"]["trigger_semantics"]
    assert "steward_state=merge_candidate" in note
    assert "COMPLETENESS_REVIEW" in note


def test_trigger_semantics_readiness_is_hosted_not_cdb_local_ci() -> None:
    note = _policy()["lifecycle"]["trigger_semantics"]
    assert "cdb-local-ci" not in note
    assert "ci (Unit/Integration + Lint gesammelt)" in note
    assert "policy-gate" in note


def test_steward_acceptance_mapping() -> None:
    mapping = _policy()["steward_acceptance_mapping"]
    assert mapping["accepting_slices"] == ["ACCEPTING_SLICES", "SLICE_IN_REVIEW"]
    assert mapping["merge_candidate"] == [
        "COMPLETENESS_REVIEW",
        "EXTENSION_REQUIRED",
        "MERGE_CANDIDATE",
    ]
    assert mapping["frozen"] == [
        "FROZEN",
        "FINAL_VALIDATION",
        "FINAL_HEAD_READY_FOR_APPROVAL",
    ]
    assert mapping["live_verified"] == ["MERGED"]
    assert ("FINAL_VALIDATION", "MERGED") in {
        tuple(p) for p in _policy()["lifecycle"]["forbidden_transitions"]
    }
    assert (
        "FINAL_HEAD_READY_FOR_APPROVAL"
        in _policy()["lifecycle"]["allowed_transitions"]["FINAL_VALIDATION"]
    )


def test_producers_and_dimension_states() -> None:
    policy = _policy()
    assert policy["producers"] == PRODUCERS
    assert policy["dimension_states"] == [
        "PASS",
        "FAIL",
        "NOT_APPLICABLE",
        "UNKNOWN",
    ]
    assert policy["dimension_rules"]["NOT_APPLICABLE_requires_reason"] is True
    assert policy["dimension_rules"]["UNKNOWN_blocks_MERGE_CANDIDATE"] is True
    assert policy["dimension_rules"]["head_or_base_drift_invalidates_evidence"] is True


def test_wiring_gap_completeness_and_conductor_enums() -> None:
    policy = _policy()
    assert len(policy["wiring_axes"]) == 10
    assert policy["wiring_verdict_precedence"] == WIRING_VERDICTS
    assert policy["gap_classes"] == GAP_CLASSES
    assert len(policy["completeness_dimensions"]) == 8
    assert "MERGE_CANDIDATE" in policy["completeness_verdicts"]
    assert "BLOCKED_SCOPE_OR_REVIEW" in policy["conductor_blockcodes"]
    assert "INVALIDATED_BY_DRIFT" in policy["block_codes"]


def test_schema_envelope_and_sha_rules() -> None:
    schema = _schema()
    assert schema["$defs"]["GitSha40"]["pattern"] == "^[a-f0-9]{40}$"
    assert schema["$defs"]["Subject"]["properties"]["head_sha"]["$ref"] == (
        "#/$defs/GitSha40"
    )
    assert schema["$defs"]["Subject"]["properties"]["base_sha"]["$ref"] == (
        "#/$defs/GitSha40"
    )
    assert "<!-- cdb-pr-acceptance:v1 -->" in schema["description"]
    producer_enum = schema["$defs"]["CommonEnvelopeBase"]["properties"]["producer"][
        "enum"
    ]
    assert producer_enum == PRODUCERS
    run_status = schema["$defs"]["CommonEnvelopeBase"]["properties"]["run_status"][
        "enum"
    ]
    assert run_status == ["COMPLETE", "BLOCKED", "INVALIDATED_BY_DRIFT"]


def test_forty_char_sha_and_drift_invalidation_helpers() -> None:
    policy = _policy()
    pattern = re.compile(policy["sha_rules"]["head_sha_pattern"])
    good = "a" * 40
    bad_short = "a" * 39
    bad_upper = "A" * 40
    assert pattern.fullmatch(good)
    assert not pattern.fullmatch(bad_short)
    assert not pattern.fullmatch(bad_upper)
    assert SHA_RE.fullmatch(good)
    assert policy["run_status"] == ["COMPLETE", "BLOCKED", "INVALIDATED_BY_DRIFT"]
    assert policy["dimension_rules"]["head_or_base_drift_invalidates_evidence"] is True


def test_enum_parity_policy_schema_and_skill_text() -> None:
    policy = _policy()
    schema = _schema()
    wiring_text = WIRING_SKILL.read_text(encoding="utf-8")
    gap_text = GAP_SKILL.read_text(encoding="utf-8")
    completeness_text = COMPLETENESS_SKILL.read_text(encoding="utf-8")
    conductor_text = CONDUCTOR_SKILL.read_text(encoding="utf-8")

    for axis in policy["wiring_axes"]:
        assert axis in wiring_text
    for verdict in policy["wiring_verdicts"]:
        assert verdict in wiring_text
    for gap_class in policy["gap_classes"]:
        assert gap_class in gap_text
    assert "BLOCKED_INSUFFICIENT_EVIDENCE" in gap_text
    assert "does not change the fachliche class" in gap_text or (
        "does **not** change the fachliche class" in gap_text
    )
    for dim in policy["completeness_dimensions"]:
        assert dim in completeness_text
    for verdict in policy["completeness_verdicts"]:
        assert verdict in completeness_text
    for code in policy["conductor_blockcodes"]:
        assert code in conductor_text
    assert "human_merge_authorization" in conductor_text
    assert "BLOCKED_HUMAN_AUTHORITY" in conductor_text

    wiring_enum = schema["$defs"]["WiringAuditResult"]["properties"]["verdict"]["enum"]
    assert wiring_enum == policy["wiring_verdicts"]
    gap_enum = schema["$defs"]["GapClassificationRow"]["properties"]["classification"][
        "enum"
    ]
    assert set(gap_enum) == set(policy["gap_classes"] + [None])
    assert (
        schema["$defs"]["WiringAxisRow"]["properties"]["dimension"]["enum"]
        == policy["wiring_axes"]
    )
    assert (
        schema["$defs"]["CompletenessReviewResult"]["properties"]["verdict"]["enum"]
        == policy["completeness_verdicts"]
    )
    assert (
        schema["$defs"]["CompletenessDimensionRow"]["properties"]["dimension"]["enum"]
        == policy["completeness_dimensions"]
    )
    assert (
        schema["$defs"]["BatchMergeConductorResult"]["properties"]["block_codes"][
            "items"
        ]["enum"]
        == policy["conductor_blockcodes"]
    )


def test_delegation_matrix_lists_all_producers() -> None:
    matrix = _policy()["delegation_matrix"]
    assert set(matrix) == set(PRODUCERS)
    assert "writes" in matrix["cdb-integration-wiring-audit"]["forbidden"]
    assert "finding_discovery" in matrix["cdb-pr-gap-classifier"]["forbidden"]
    assert (
        "cdb-integration-wiring-audit"
        in matrix["cdb-pr-completeness-review"]["delegates_to"]
    )
    assert "admin_merge" in matrix["cdb-batch-merge-conductor"]["forbidden"]
    assert "merge_execution" in matrix["cdb-batch-merge-conductor"]["forbidden"]
    assert "approve_pr" in matrix["cdb-batch-merge-conductor"]["forbidden"]
    roles = _policy()["final_head_roles"]
    assert roles["pr_approval_gate"]["role_id"] == "cdb_final_head_pr_approval_gate"
    assert roles["merge_executor"]["role_id"] == "cdb_final_head_merge_executor"
    assert roles["pr_approval_gate"]["merge_pr"] is False
    assert roles["merge_executor"]["approve_pr"] is False
    assert roles["merge_executor"]["admin_bypass"] is False


def test_session_status_mappings_present() -> None:
    mappings = _policy()["session_status_mappings"]
    assert "DONE_SLICE_ADDED_TO_BATCH_PR" in mappings
    assert "DONE_WIRING_SLICE_ADDED" in mappings
    assert "DONE_GAP_CLASSIFIER_SLICE_ADDED" in mappings
    assert "DONE_COMPLETENESS_SLICE_ADDED" in mappings
    assert "DONE_CONDUCTOR_SLICE_ADDED" in mappings
    assert "DONE_PR_ACCEPTANCE_SKILL_FAMILY_MERGED" in mappings
