from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest
import yaml

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "dependabot_autopilot_classifier.py"
)
ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "dependabot-autopilot-allowlist.yml"
)

SPEC = importlib.util.spec_from_file_location(
    "dependabot_autopilot_classifier", SCRIPT_PATH
)
assert SPEC is not None
classifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = classifier
assert SPEC.loader is not None
SPEC.loader.exec_module(classifier)

Facts = classifier.DependabotAutopilotFacts
RequiredCheckFact = classifier.RequiredCheckFact
Policy = classifier.parse_allowlist_policy

VALID_HEAD_SHA = "b366010aa9cbcfca440497dc64b6c8746c50ff55"


def _load_policy() -> classifier.AllowlistPolicy:
    raw = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    return Policy(raw)


def _checks(
    *,
    status: str = "COMPLETED",
    conclusion: str = "SUCCESS",
) -> tuple[RequiredCheckFact, ...]:
    """Build the live required merge checks on `main` (post-#4540).

    Both ``ci (Unit/Integration + Lint gesammelt)`` and ``policy-gate`` are
    hosted GitHub Actions Check Runs per
    docs/runbooks/merge_policy_ci_gate.md; they are the only merge-relevant
    required contexts.
    """
    return (
        RequiredCheckFact("ci (Unit/Integration + Lint gesammelt)", status, conclusion),
        RequiredCheckFact("policy-gate", status, conclusion),
    )


def _facts(**overrides: object) -> Facts:
    base = {
        "pr_author": "dependabot[bot]",
        "base_branch": "main",
        "head_branch": "dependabot/pip/ruff-0.15.21",
        "is_draft": False,
        "labels": (),
        "head_sha": VALID_HEAD_SHA,
        "commit_count": 1,
        "commit_authors": ("dependabot[bot]",),
        "changed_files": ("requirements-dev.txt",),
        "required_checks": _checks(),
        "branch_is_current": True,
        "merge_state": "CLEAN",
        "ecosystem": "pip",
        "package_name": "ruff",
        "dependency_type": "direct:development",
        "update_type": "version-update:semver-patch",
        "current_version": "0.15.20",
        "target_version": "0.15.21",
        "metadata_complete": True,
        "diff_verified": True,
        "range_change": False,
        "date_versioned": False,
        "api_error": False,
        "execution_mode": "report_only",
        "kill_switch_enabled": False,
    }
    base.update(overrides)
    return Facts(**base)


def test_allowlisted_ruff_patch_report_only_is_eligible_not_merge_authorized() -> None:
    result = classifier.classify_dependabot_pr(_facts(), _load_policy())

    assert result.classification == "ELIGIBLE"
    assert result.action == "REPORT_ONLY"
    assert result.merge_authorized is False
    assert classifier.REASON_ELIGIBLE in result.reason_codes
    assert classifier.REASON_REPORT_ONLY in result.reason_codes


def test_kill_switch_false_prevents_merge_authorization_in_phase_mode() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(execution_mode="phase1", kill_switch_enabled=False),
        _load_policy(),
    )

    assert result.classification == "ELIGIBLE"
    assert result.action == "REPORT_ONLY"
    assert result.merge_authorized is False
    assert classifier.REASON_AUTOMERGE_DISABLED in result.reason_codes


def test_phase1_with_kill_switch_true_yields_merge_candidate_only() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(execution_mode="phase1", kill_switch_enabled=True),
        _load_policy(),
    )

    assert result.classification == "ELIGIBLE"
    assert result.action == "MERGE_CANDIDATE"
    assert result.merge_authorized is True
    assert classifier.REASON_ELIGIBLE in result.reason_codes


def test_major_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(update_type="version-update:semver-major", target_version="1.0.0"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_UPDATE_TYPE in result.reason_codes


def test_minor_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(update_type="version-update:semver-minor", target_version="0.16.0"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_UPDATE_TYPE in result.reason_codes


def test_range_change_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(range_change=True), _load_policy()
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_RANGE in result.reason_codes


def test_date_version_boolean_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(date_versioned=True, target_version="2026.7.10"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DATE_VERSION in result.reason_codes


def test_date_version_detected_without_boolean_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            date_versioned=False,
            current_version="2026.6.4",
            target_version="2026.7.10",
            package_name="mcp-server-time",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DATE_VERSION in result.reason_codes


def test_docker_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            ecosystem="docker",
            package_name="postgres",
            changed_files=("services/risk/Dockerfile",),
            dependency_type="direct:production",
            update_type="version-update:semver-patch",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DOCKER in result.reason_codes


def test_database_compose_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            ecosystem="docker-compose",
            package_name="postgres",
            changed_files=("infrastructure/compose/docker-compose.yml",),
            dependency_type="direct:production",
            update_type="version-update:semver-patch",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DOCKER in result.reason_codes


def test_runtime_requirements_txt_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            package_name="redis",
            changed_files=("requirements.txt",),
            dependency_type="direct:production",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_RUNTIME in result.reason_codes


def test_github_actions_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            ecosystem="github-actions",
            package_name="actions/stale",
            changed_files=(".github/workflows/stale.yml",),
            dependency_type="direct:production",
            update_type="version-update:semver-patch",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_ACTIONS in result.reason_codes


def test_non_dependabot_author_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(pr_author="jannekbuengener"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_AUTHOR in result.reason_codes


def test_wrong_base_branch_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(base_branch="develop"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_BASE in result.reason_codes


def test_wrong_head_branch_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(head_branch="feature/ruff-bump"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_HEAD in result.reason_codes


def test_two_commits_hold() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(commit_count=2),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_COUNT in result.reason_codes


def test_zero_commits_hold() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(commit_count=0, commit_authors=()),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_COUNT in result.reason_codes


def test_empty_commit_authors_with_single_commit_count_hold() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(commit_count=1, commit_authors=()),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_AUTHOR in result.reason_codes


def test_two_commit_authors_with_single_commit_count_hold() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(commit_count=1, commit_authors=("dependabot[bot]", "human")),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_AUTHOR in result.reason_codes


def test_human_commit_author_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(commit_authors=("dependabot[bot]", "jannekbuengener"), commit_count=2),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_AUTHOR in result.reason_codes


def test_additional_changed_file_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(changed_files=("requirements-dev.txt", "pyproject.toml")),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_FILE in result.reason_codes


def test_diff_not_verified_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(diff_verified=False),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DIFF in result.reason_codes


def test_incomplete_metadata_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(metadata_complete=False),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_METADATA in result.reason_codes


def test_missing_required_check_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            required_checks=(
                RequiredCheckFact("unrelated-check", "COMPLETED", "SUCCESS"),
            )
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_CHECK_MISSING in result.reason_codes


def test_completed_with_failure_conclusion_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            required_checks=_checks(
                status="COMPLETED",
                conclusion="FAILURE",
            )
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_CHECK_FAIL in result.reason_codes


def test_in_progress_with_success_conclusion_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            required_checks=_checks(
                status="IN_PROGRESS",
                conclusion="SUCCESS",
            )
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_CHECK_FAIL in result.reason_codes


def test_duplicate_required_check_with_conflicting_results_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            required_checks=(
                RequiredCheckFact("ci (Unit/Integration + Lint gesammelt)", "COMPLETED", "SUCCESS"),
                RequiredCheckFact("ci (Unit/Integration + Lint gesammelt)", "COMPLETED", "FAILURE"),
            )
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_CHECK_AMBIGUOUS in result.reason_codes


def test_branch_not_current_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(branch_is_current=False),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_BRANCH in result.reason_codes


@pytest.mark.parametrize("merge_state", ["BEHIND", "BLOCKED", "DIRTY", "UNKNOWN"])
def test_non_clean_merge_state_holds(merge_state: str) -> None:
    result = classifier.classify_dependabot_pr(
        _facts(merge_state=merge_state),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_MERGE_STATE in result.reason_codes


def test_api_error_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(api_error=True),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_API in result.reason_codes


def test_unknown_package_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(package_name="unknown-package"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_PACKAGE in result.reason_codes


def test_unknown_package_allow_default_cannot_override_hold() -> None:
    policy = Policy(
        {
            "schema_version": 1,
            "default_mode": "report_only",
            "defaults": {"unknown_package": "ALLOW"},
            "entries": {
                "pip": {
                    "ruff": {
                        "dependency_type": "direct:development",
                        "allowed_update_types": ["version-update:semver-patch"],
                        "allowed_files": ["requirements-dev.txt"],
                    }
                }
            },
        }
    )
    assert policy.valid is False
    result = classifier.classify_dependabot_pr(
        _facts(package_name="not-listed"),
        policy,
    )
    assert result.classification == "HOLD"
    assert classifier.REASON_POLICY in result.reason_codes


def test_invalid_allowlist_holds() -> None:
    invalid = Policy({"schema_version": 99, "entries": {}})
    result = classifier.classify_dependabot_pr(_facts(), invalid)

    assert result.classification == "HOLD"
    assert classifier.REASON_POLICY in result.reason_codes


def test_non_numeric_schema_version_does_not_raise() -> None:
    invalid = Policy({"schema_version": "invalid", "entries": []})
    assert invalid.valid is False
    result = classifier.classify_dependabot_pr(_facts(), invalid)
    assert result.classification == "HOLD"
    assert classifier.REASON_POLICY in result.reason_codes


def test_empty_ecosystem_mapping_is_policy_invalid() -> None:
    invalid = Policy(
        {
            "schema_version": 1,
            "default_mode": "report_only",
            "defaults": {"unknown_package": "HOLD", "unknown_ecosystem": "HOLD"},
            "entries": {"pip": {}},
        }
    )
    assert invalid.valid is False
    result = classifier.classify_dependabot_pr(_facts(), invalid)
    assert result.classification == "HOLD"
    assert classifier.REASON_POLICY in result.reason_codes


def test_unsafe_allowlist_path_is_policy_invalid() -> None:
    invalid = Policy(
        {
            "schema_version": 1,
            "default_mode": "report_only",
            "defaults": {"unknown_package": "HOLD", "unknown_ecosystem": "HOLD"},
            "entries": {
                "pip": {
                    "ruff": {
                        "dependency_type": "direct:development",
                        "allowed_update_types": ["version-update:semver-patch"],
                        "allowed_files": [".github/workflows/ci.yml"],
                    }
                }
            },
        }
    )
    assert invalid.valid is False


def test_manual_review_label_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(labels=("dependencies:manual-review",)),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_MANUAL_REVIEW in result.reason_codes


def test_draft_pr_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(is_draft=True),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DRAFT in result.reason_codes


def test_unknown_execution_mode_with_kill_switch_true_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(execution_mode="auto", kill_switch_enabled=True),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_EXECUTION_MODE in result.reason_codes
    assert result.action == "HOLD"
    assert result.merge_authorized is False


def test_string_kill_switch_value_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(kill_switch_enabled="false", execution_mode="phase1"),  # type: ignore[arg-type]
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_FACTS_INVALID in result.reason_codes


def test_invalid_head_sha_empty_holds() -> None:
    result = classifier.classify_dependabot_pr(_facts(head_sha=""), _load_policy())

    assert result.classification == "HOLD"
    assert result.reason_codes == (classifier.REASON_FACTS_INVALID,)
    assert result.human_summary == classifier.FACTS_INVALID_SUMMARY


def test_invalid_head_sha_short_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(head_sha="abc123"), _load_policy()
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_HEAD_SHA in result.reason_codes


def test_identical_version_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(current_version="0.15.21", target_version="0.15.21"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_VERSION_TRANSITION in result.reason_codes


def test_downgrade_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(current_version="0.15.21", target_version="0.15.20"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_VERSION_TRANSITION in result.reason_codes


def test_non_consecutive_patch_bump_remains_eligible() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(current_version="0.15.20", target_version="0.15.22"),
        _load_policy(),
    )

    assert result.classification == "ELIGIBLE"


def test_wrong_minor_patch_jump_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(current_version="0.15.20", target_version="0.16.1"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_VERSION_TRANSITION in result.reason_codes


def test_repeated_evaluation_is_deterministic() -> None:
    policy = _load_policy()
    facts = _facts()
    first = classifier.classify_dependabot_pr(facts, policy)
    second = classifier.classify_dependabot_pr(facts, policy)

    assert first == second


def test_anonymized_live_regression_fixture_two_commits_holds() -> None:
    """Mirrors live #4049: ruff patch + merge commit + behind merge state."""
    result = classifier.classify_dependabot_pr(
        _facts(
            head_branch="dependabot/pip/ruff-0.15.21",
            commit_count=2,
            commit_authors=("dependabot[bot]", "jannekbuengener"),
            changed_files=("requirements-dev.txt",),
            branch_is_current=False,
            merge_state="BEHIND",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_COUNT in result.reason_codes
    assert classifier.REASON_COMMIT_AUTHOR in result.reason_codes
    assert classifier.REASON_BRANCH in result.reason_codes
    assert classifier.REASON_MERGE_STATE in result.reason_codes


MALFORMED_FACT_CASES = [
    pytest.param({"pr_author": 123}, id="pr_author_int"),
    pytest.param({"labels": (123,)}, id="labels_int"),
    pytest.param({"changed_files": (123,)}, id="changed_files_int"),
    pytest.param({"commit_authors": (None,)}, id="commit_authors_none"),  # type: ignore[list-item]
    pytest.param(
        {
            "required_checks": (
                RequiredCheckFact(None, "COMPLETED", "SUCCESS"),  # type: ignore[arg-type]
            )
        },
        id="required_check_name_none",
    ),
    pytest.param(
        {
            "required_checks": (
                RequiredCheckFact("ci (Unit/Integration + Lint gesammelt)", 123, "SUCCESS"),  # type: ignore[arg-type]
            )
        },
        id="required_check_status_int",
    ),
    pytest.param(
        {
            "required_checks": (
                RequiredCheckFact("ci (Unit/Integration + Lint gesammelt)", "COMPLETED", []),  # type: ignore[arg-type]
            )
        },
        id="required_check_conclusion_list",
    ),
    pytest.param({"execution_mode": None}, id="execution_mode_none"),  # type: ignore[dict-item]
    pytest.param({"kill_switch_enabled": "true"}, id="kill_switch_string"),  # type: ignore[dict-item]
    pytest.param({"commit_count": True}, id="commit_count_bool"),  # type: ignore[dict-item]
]


@pytest.mark.parametrize("overrides", MALFORMED_FACT_CASES)
def test_malformed_facts_fail_closed_without_exception(overrides: dict) -> None:
    result = classifier.classify_dependabot_pr(_facts(**overrides), _load_policy())

    assert result.classification == "HOLD"
    assert result.action == "HOLD"
    assert result.merge_authorized is False
    assert result.reason_codes == (classifier.REASON_FACTS_INVALID,)
    assert result.human_summary == classifier.FACTS_INVALID_SUMMARY


INVALID_FACTS_TOP_LEVEL_CASES = [
    pytest.param({"required_checks": None}, id="required_checks_none"),  # type: ignore[dict-item]
    pytest.param({"labels": None}, id="labels_none"),  # type: ignore[dict-item]
    pytest.param({"changed_files": None}, id="changed_files_none"),  # type: ignore[dict-item]
    pytest.param({"package_name": 123}, id="package_name_int"),  # type: ignore[dict-item]
]


@pytest.mark.parametrize("overrides", INVALID_FACTS_TOP_LEVEL_CASES)
def test_invalid_fact_fields_use_constant_summary(overrides: dict) -> None:
    result = classifier.classify_dependabot_pr(_facts(**overrides), _load_policy())

    assert result.classification == "HOLD"
    assert result.action == "HOLD"
    assert result.merge_authorized is False
    assert result.reason_codes == (classifier.REASON_FACTS_INVALID,)
    assert result.human_summary == classifier.FACTS_INVALID_SUMMARY
    assert "123" not in result.human_summary
    assert "None" not in result.human_summary


@pytest.mark.parametrize(
    "facts_value",
    [None, {}],
)
def test_non_dependabot_autopilot_facts_use_constant_summary(
    facts_value: object,
) -> None:
    result = classifier.classify_dependabot_pr(facts_value, _load_policy())  # type: ignore[arg-type]

    assert result.classification == "HOLD"
    assert result.action == "HOLD"
    assert result.merge_authorized is False
    assert result.reason_codes == (classifier.REASON_FACTS_INVALID,)
    assert result.human_summary == classifier.FACTS_INVALID_SUMMARY


def test_policy_default_mode_phase1_is_invalid() -> None:
    policy = Policy(
        {
            "schema_version": 1,
            "default_mode": "phase1",
            "defaults": {"unknown_package": "HOLD", "unknown_ecosystem": "HOLD"},
            "entries": {
                "pip": {
                    "ruff": {
                        "dependency_type": "direct:development",
                        "allowed_update_types": ["version-update:semver-patch"],
                        "allowed_files": ["requirements-dev.txt"],
                    }
                }
            },
        }
    )
    assert policy.valid is False
    result = classifier.classify_dependabot_pr(_facts(), policy)
    assert result.classification == "HOLD"
    assert classifier.REASON_POLICY in result.reason_codes


@pytest.mark.parametrize(
    "schema_version",
    [1.2, True, "1"],
)
def test_non_integer_schema_version_is_policy_invalid(schema_version: object) -> None:
    policy = Policy(
        {
            "schema_version": schema_version,
            "default_mode": "report_only",
            "defaults": {"unknown_package": "HOLD", "unknown_ecosystem": "HOLD"},
            "entries": {
                "pip": {
                    "ruff": {
                        "dependency_type": "direct:development",
                        "allowed_update_types": ["version-update:semver-patch"],
                        "allowed_files": ["requirements-dev.txt"],
                    }
                }
            },
        }
    )
    assert policy.valid is False


@pytest.mark.parametrize(
    "path",
    [
        ".github/scripts/example.py",
        ".github/actions/example/action.yml",
        ".github/workflows/ci.yml",
    ],
)
def test_changed_file_under_dot_github_is_control_plane_hold(path: str) -> None:
    result = classifier.classify_dependabot_pr(
        _facts(changed_files=(path,)),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_CONTROL_PLANE in result.reason_codes


@pytest.mark.parametrize(
    "current_version,target_version",
    [
        ("+1.2.3", "1.2.4"),
        ("1.-2.3", "1.2.4"),
        ("1.2", "1.2.3"),
        ("1.2.3.4", "1.2.5"),
        ("1..3", "1.2.4"),
        ("v1.2.3", "1.2.4"),
        ("0.15.21", "0.15.21"),
    ],
)
def test_invalid_semver_transition_holds(
    current_version: str, target_version: str
) -> None:
    result = classifier.classify_dependabot_pr(
        _facts(current_version=current_version, target_version=target_version),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_VERSION_TRANSITION in result.reason_codes


def test_allowlist_rejects_dot_github_scripts_path() -> None:
    policy = Policy(
        {
            "schema_version": 1,
            "default_mode": "report_only",
            "defaults": {"unknown_package": "HOLD", "unknown_ecosystem": "HOLD"},
            "entries": {
                "pip": {
                    "ruff": {
                        "dependency_type": "direct:development",
                        "allowed_update_types": ["version-update:semver-patch"],
                        "allowed_files": [".github/scripts/example.py"],
                    }
                }
            },
        }
    )
    assert policy.valid is False
