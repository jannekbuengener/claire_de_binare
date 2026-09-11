"""Workflow inventory and register drift contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]
FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "workflow_contract"


def _fixture_dir(name: str) -> Path:
    return FIXTURES_ROOT / name


def _scan() -> helpers.WorkflowInventoryScan:
    return helpers.scan_workflow_inventory(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        control_plane_json_path=helpers.CONTROL_PLANE_REGISTER_JSON,
    )


def test_disk_and_markdown_register_are_complete() -> None:
    scan = _scan()
    assert len(scan.disk_workflows) == 57
    assert len(scan.register_workflows) == 57
    assert scan.unregistered_on_disk == ()
    assert scan.missing_on_disk == ()


def test_register_header_matches_disk() -> None:
    declared = helpers.parse_register_total_count_claim(helpers.WORKFLOW_REGISTER_MD)
    assert declared == len(helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR))


def test_control_plane_unit_register_paths_exist() -> None:
    scan = _scan()
    assert scan.control_plane_missing_on_disk == ()
    assert scan.control_plane_workflows


def test_control_plane_unit_register_remains_partial_by_design() -> None:
    payload = json.loads(
        helpers.CONTROL_PLANE_REGISTER_JSON.read_text(encoding="utf-8")
    )
    assert payload.get("coverage") == "partial"
    assert payload.get("catalog_scope") == "control-plane-sprint1"
    assert payload.get("unit_count", 0) < len(
        helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR)
    )


@pytest.mark.parametrize(
    "filename,expected_status",
    [
        ("ci.yml", "aktiv"),
        ("policy-gate.yml", "aktiv"),
        ("required-checks-audit.yml", "manual-only"),
        ("surrealdb-memory-proof.yml", "manual-only"),
    ],
)
def test_register_classifies_current_workflows(
    filename: str, expected_status: str
) -> None:
    assert (
        helpers.parse_register_status_map(helpers.WORKFLOW_REGISTER_MD)[filename]
        == expected_status
    )


def test_canonical_ci_is_active() -> None:
    workflow_path = helpers.WORKFLOWS_DIR / helpers.ACTIVE_CANONICAL_CI_WORKFLOW
    triggers = helpers.extract_on_triggers(helpers.load_workflow_yaml(workflow_path))
    # #4540: hosted Fast-CI emits the required check `ci (Unit/Integration + Lint
    # gesammelt)` on PRs to main now; it is no longer a post-merge-only mirror.
    assert {"push", "workflow_dispatch"} <= triggers
    assert "pull_request" in triggers


def test_fixture_detects_unregistered_workflow_drift() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=_fixture_dir("inventory_drift"),
        register_md_path=_fixture_dir("inventory_drift")
        / "GITHUB_WORKFLOW_REGISTER.md",
        control_plane_json_path=_fixture_dir("inventory_drift")
        / "workflow-register.json",
    )
    assert scan.unregistered_on_disk == ("orphan.yml",)


def test_fixture_detects_register_missing_file_drift() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=_fixture_dir("register_missing_file"),
        register_md_path=_fixture_dir("register_missing_file")
        / "GITHUB_WORKFLOW_REGISTER.md",
        control_plane_json_path=_fixture_dir("register_missing_file")
        / "workflow-register.json",
    )
    assert scan.missing_on_disk == ("ghost.yml",)
