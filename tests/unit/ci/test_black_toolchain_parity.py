"""Toolchain parity: requirements-dev pin vs Dockerfile / ci.yml (#4206).

test_id: tc_ci_black_toolchain_parity_001
test_type: contract
cdb_area: ci
issue_ref: #4206
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ci.stages.lint import pinned_black_version

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
UNVERSIONED_RUFF_BLACK = re.compile(
    r"pip\s+install(?:\s+[^\n]*)?\s+(?:--no-cache-dir\s+)?ruff\s+black\b"
)


def test_requirements_dev_pins_expected_black() -> None:
    assert pinned_black_version(REPO_ROOT) == "26.5.1"
    text = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "ruff==0.16.6" in text


def test_dockerfile_has_no_unversioned_ruff_black_reinstall() -> None:
    text = (REPO_ROOT / "ci" / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements-dev.txt" in text
    assert UNVERSIONED_RUFF_BLACK.search(text) is None


def test_ci_workflow_has_no_unversioned_ruff_black_reinstall() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "requirements-dev.txt" in text
    assert UNVERSIONED_RUFF_BLACK.search(text) is None
    assert "pip install ruff black" not in text


def test_resources_yaml_timeout_default_is_300() -> None:
    text = (REPO_ROOT / "ci" / "config" / "resources.yaml").read_text(encoding="utf-8")
    assert "black_timeout_seconds: 300" in text
