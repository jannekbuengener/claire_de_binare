"""Static contract for hosted Required Checks sentinel semantics (#4202/#4540)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "required-checks-audit.yml"


def test_sentinel_reads_check_runs_not_commit_status() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "/commits/$SHA/check-runs?per_page=100" in text
    assert 'required_type="github-check-run"' in text
    assert 'required_check="commit_status"' not in text.lower()
    assert "/commits/$SHA/status" not in text


def test_cdb_local_ci_not_used_as_required_check() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "ci (Unit/Integration + Lint gesammelt)" in text
    assert "policy-gate" in text
    assert 'required_check="cdb-local-ci"' not in text
