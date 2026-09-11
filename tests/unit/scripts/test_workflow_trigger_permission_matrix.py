"""Workflow trigger and permission matrix contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]
FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "workflow_contract"


def _matrix_for_dir(workflows_dir: Path) -> list[helpers.WorkflowTriggerPermissionRow]:
    return [
        helpers.build_trigger_permission_row(workflows_dir / filename)
        for filename in helpers.list_workflow_yaml_files(workflows_dir)
    ]


def test_no_workflow_declares_pull_request_target() -> None:
    offenders = [
        filename
        for filename in helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR)
        if helpers.workflow_declares_forbidden_trigger(helpers.WORKFLOWS_DIR / filename)
    ]
    assert offenders == []


def test_trigger_matrix_is_complete() -> None:
    rows = _matrix_for_dir(helpers.WORKFLOWS_DIR)
    assert rows == _matrix_for_dir(helpers.WORKFLOWS_DIR)
    assert len(rows) == 57


@pytest.mark.parametrize(
    "filename,expected_triggers",
    [
        ("ci.yml", ("pull_request", "push", "workflow_dispatch")),
        ("policy-gate.yml", ("pull_request",)),
        ("docs-conflict-guard.yml", ("push", "workflow_dispatch")),
        ("repository-canon-guard.yml", ("push", "workflow_dispatch")),
        ("codeql-python.yml", ("push", "schedule", "workflow_dispatch")),
        ("required-checks-audit.yml", ("workflow_dispatch",)),
        ("project_reconcile_daily.yml", ("schedule", "workflow_dispatch")),
    ],
)
def test_known_triggers(filename: str, expected_triggers: tuple[str, ...]) -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / filename)
    assert row.triggers == expected_triggers


@pytest.mark.parametrize(
    "filename,expected_permissions",
    [
        ("ci.yml", ()),
        ("policy-gate.yml", ()),
        ("stale.yml", ("issues:write", "pull-requests:write")),
        ("cdb-daily-delta-triage.yml", ("issues:write",)),
    ],
)
def test_known_write_permissions(
    filename: str, expected_permissions: tuple[str, ...]
) -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / filename)
    assert row.write_permissions == expected_permissions


def test_write_permissions_use_canonical_tokens() -> None:
    for row in _matrix_for_dir(helpers.WORKFLOWS_DIR):
        assert set(row.write_permissions) <= helpers.WRITE_PERMISSION_SCOPES


def test_fixture_flags_pull_request_target() -> None:
    row = helpers.build_trigger_permission_row(
        FIXTURES_ROOT / "forbidden_trigger" / "bad.yml"
    )
    assert row.forbidden_triggers == ("pull_request_target",)


def test_fixture_surfaces_missing_permissions() -> None:
    row = helpers.build_trigger_permission_row(
        FIXTURES_ROOT / "missing_permissions" / "implicit.yml"
    )
    assert row.has_explicit_permissions is False


def test_policy_gate_blocks_pull_request_target_pattern() -> None:
    content = (helpers.WORKFLOWS_DIR / "policy-gate.yml").read_text(encoding="utf-8")
    assert "contains pull_request_target" in content
