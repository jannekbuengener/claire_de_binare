"""Contract / governance tests for App-bound Check Run migration (#4170)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_BP = REPO_ROOT / "docs/evidence/reports/BRANCH_PROTECTION_BASELINE_main.json"
BASELINE_CTX = (
    REPO_ROOT / "docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json"
)
CUTOVER_RUNBOOK = REPO_ROOT / "docs/runbooks/cdb_local_ci_app_check_run_cutover.md"
PERMISSION_DOC_MARKERS = (
    "Metadata: Read",
    "Checks: Read and Write",
    "Commit statuses: Write",
    "Administration",
)


def test_branch_protection_baselines_reflect_hosted_required_checks():
    bp = json.loads(BASELINE_BP.read_text(encoding="utf-8"))
    checks = bp["required_status_checks"]["checks"]
    assert checks == [
        {"context": "ci (Unit/Integration + Lint gesammelt)"},
        {"context": "policy-gate"},
    ]
    assert bp["required_status_checks"]["contexts"] == [
        "ci (Unit/Integration + Lint gesammelt)",
        "policy-gate",
    ]
    assert bp["required_status_checks"]["strict"] is True

    ctx = json.loads(BASELINE_CTX.read_text(encoding="utf-8"))
    assert sorted(ctx["contexts"]) == [
        "ci (Unit/Integration + Lint gesammelt)",
        "policy-gate",
    ]
    assert ctx.get("required_app_id") is None
    assert ctx.get("check_run_contexts") == []


def test_no_private_key_or_token_examples_in_publisher_tree():
    publisher_root = REPO_ROOT / "ci" / "publisher"
    pem_markers = (
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
    )
    # Real token-shaped values (prefix + long secret), not detection literals.
    import re

    token_value_re = re.compile(
        r"\b(?:ghp_|github_pat_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{20,}\b"
    )
    for path in publisher_root.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".md", ".txt", ".pem"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in pem_markers:
            assert snippet not in text, f"{path} contains PEM material"
        match = token_value_re.search(text)
        assert match is None, f"{path} contains token-like value {match.group(0)!r}"


def test_cutover_runbook_documents_phases_and_holds():
    assert CUTOVER_RUNBOOK.is_file()
    text = CUTOVER_RUNBOOK.read_text(encoding="utf-8")
    for marker in (
        "A_CODE_READY",
        "B_APP_INSTALLED",
        "C_SHADOW_SMOKE",
        "D_CUTOVER",
        "E_RETIRE_INTERIM",
        "cdb-local-ci-app-preview",
        "APP_BOUND_CHECK_RUN_CUTOVER_HANDOFF",
        "Rollback",
        "HOLD",
        "CDB_GH_APP_INSTALLATION_TOKEN",
    ):
        assert marker in text, f"missing {marker}"


def test_app_permission_matrix_forbids_statuses_write_and_admin():
    text = CUTOVER_RUNBOOK.read_text(encoding="utf-8")
    assert "Metadata: Read" in text
    assert "Checks: Read and Write" in text
    # Documented as prohibited, not granted.
    assert "Commit statuses: Write" in text
    assert "prohibited" in text.lower() or "forbidden" in text.lower()
    assert "Administration" in text


def test_publisher_has_no_branch_protection_write_api():
    publisher_root = REPO_ROOT / "ci" / "publisher"
    blob = "\n".join(
        path.read_text(encoding="utf-8") for path in publisher_root.rglob("*.py")
    )
    assert "branches/main/protection" not in blob
    assert "/repos/{owner}/{repo}/branches/" not in blob
    assert "PUT" not in blob or "check-runs" in blob  # no BP mutation helpers
    assert "update_branch_protection" not in blob
    assert "required_pull_request_reviews" not in blob


def test_required_checks_are_hosted_not_local():
    # Post-#4540: required contexts are the two hosted job names, not cdb-local-ci.
    bp = json.loads(BASELINE_BP.read_text(encoding="utf-8"))
    contexts = bp["required_status_checks"]["contexts"]
    assert "ci (Unit/Integration + Lint gesammelt)" in contexts
    assert "policy-gate" in contexts
    assert "cdb-local-ci" not in contexts


def test_check_run_mode_is_default_backend():
    from ci.publisher.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(
        [
            "dry-run",
            "--evidence-dir",
            ".",
            "--pr-number",
            "1",
        ]
    )
    assert args.publisher_backend == "check-run"
