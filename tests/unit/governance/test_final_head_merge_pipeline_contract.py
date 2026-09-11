"""Negative/positive contract tests for Final-Head merge pipeline (#4411)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "config" / "governance" / "pr-acceptance-policy.v1.yaml"
APPROVAL = (
    ROOT / "config" / "agent-control" / "policies" / "approval" / "pr_approval.v1.yaml"
)
PIPELINE = ROOT / "docs" / "contracts" / "final_head_merge_pipeline.v1.md"
CONDUCTOR = ROOT / "docs" / "skills" / "cdb-batch-merge-conductor" / "SKILL.md"
MERGE_GATE = ROOT / "docs" / "runbooks" / "merge_policy_ci_gate.md"
CI_README = ROOT / "ci" / "README.md"
CHECKS_RULE = ROOT / ".cursor" / "rules" / "CDB-Checks-and-Merge-Rule.mdc"


def test_single_merge_executor_and_split_roles() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    pipeline = PIPELINE.read_text(encoding="utf-8")
    roles = policy["final_head_roles"]
    assert roles["merge_executor"]["role_id"] == "cdb_final_head_merge_executor"
    assert roles["pr_approval_gate"]["role_id"] == "cdb_final_head_pr_approval_gate"
    assert roles["pr_approval_gate"]["merge_pr"] is False
    assert roles["merge_executor"]["approve_pr"] is False
    assert "cdb_final_head_merge_executor" in pipeline
    assert "Exactly one canonical final merge executor" in pipeline


def test_conductor_and_merge_agent_do_not_both_own_merge() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    conductor = CONDUCTOR.read_text(encoding="utf-8")
    forbidden = policy["delegation_matrix"]["cdb-batch-merge-conductor"]["forbidden"]
    assert "merge_execution" in forbidden
    assert "FINAL_HEAD_READY_FOR_APPROVAL" in conductor
    assert "Execute regular squash-merge" not in conductor
    # Merge agent owns merge; conductor must not claim Phase MERGE
    assert "`MERGE` — regular" not in conductor


def test_merge_candidate_does_not_imply_merged() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    forbidden = {tuple(p) for p in policy["lifecycle"]["forbidden_transitions"]}
    assert ("MERGE_CANDIDATE", "MERGED") in forbidden
    assert ("FINAL_VALIDATION", "MERGED") in forbidden
    assert "FINAL_HEAD_READY_FOR_APPROVAL" in policy["lifecycle"]["states"]
    note = policy["lifecycle"]["trigger_semantics"]
    assert "never authorize merge" in note


def test_approval_requires_exact_head_sha_binding() -> None:
    approval = yaml.safe_load(APPROVAL.read_text(encoding="utf-8"))
    assert approval["authority"]["merge"] is False
    assert approval["rules"]["require_head_sha_binding"] is True
    assert approval["rules"]["approval_invalid_on_new_commit"] is True
    assert (
        approval["final_head_roles"]["github_approve_mutation_role"]
        == "cdb_final_head_pr_approval_gate"
    )
    fields = approval["github_approve_mutation"]["required_fields"]
    assert "HEAD_SHA" in fields
    assert approval["github_approve_mutation"]["decision_value"] == "APPROVE"
    assert approval["final_head_roles"]["local_cdb_context_required"] is False


def test_cdb_local_ci_not_commit_status_in_active_merge_canon() -> None:
    merge_gate = MERGE_GATE.read_text(encoding="utf-8")
    ci_readme = CI_README.read_text(encoding="utf-8")
    checks = CHECKS_RULE.read_text(encoding="utf-8")
    # Post-#4540: hosted required checks are primary; cdb-local-ci is optional preflight
    assert "ci (Unit/Integration + Lint gesammelt)" in merge_gate
    assert "policy-gate" in merge_gate
    assert "hosted Required" in merge_gate or "hosted Check Run" in merge_gate
    assert "optionaler" in merge_gate or "optional" in merge_gate.lower()
    assert "Default-Pfad bleiben Commit Status" not in ci_readme
    assert "capability-based autonomous merge that bypasses" in checks.lower() or (
        "bypass" in checks.lower() and "Merge Agent" in checks
    )


def test_cloud_path_does_not_require_cdb_context() -> None:
    approval = yaml.safe_load(APPROVAL.read_text(encoding="utf-8"))
    pipeline = PIPELINE.read_text(encoding="utf-8")
    assert approval["final_head_roles"]["context_mode"] == "repo-only"
    assert approval["final_head_roles"]["local_cdb_context_required"] is False
    assert "must not require local" in pipeline
    assert "cdb_context" in pipeline
