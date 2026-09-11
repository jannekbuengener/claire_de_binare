#!/usr/bin/env python3
"""Fail-closed Dependabot autopilot classifier (pure decision core, no I/O)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

Classification = Literal["ELIGIBLE", "HOLD"]
Action = Literal["REPORT_ONLY", "MERGE_CANDIDATE", "HOLD"]

SUPPORTED_SCHEMA_VERSION = 1
DEFAULT_BASE_BRANCH = "main"
DEFAULT_HEAD_PREFIX = "dependabot/"

ALLOWED_EXECUTION_MODES = frozenset({"report_only", "phase1"})
ALLOWED_DEFAULT_VALUES = frozenset({"HOLD"})
SCHEMA_V1_ECOSYSTEM = "pip"
SCHEMA_V1_DEPENDENCY_TYPE = "direct:development"
SCHEMA_V1_UPDATE_TYPE = "version-update:semver-patch"

DEPENDABOT_AUTHOR_LOGINS = frozenset(
    {
        "dependabot[bot]",
        "app/dependabot",
    }
)

MANUAL_REVIEW_LABELS = frozenset(
    {
        "dependencies:manual-review",
        "manual-approval",
        "status:blocked",
    }
)

REQUIRED_CHECK_NAMES = (
    "ci (Unit/Integration + Lint gesammelt)",
    "policy-gate",
)
"""Live required merge checks on `main` (post-#4540).

SSOT: docs/runbooks/merge_policy_ci_gate.md; live baseline snapshot at
docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json.
These are hosted GitHub Actions Check Runs (name/status/conclusion).
"""

CHECK_STATUS_COMPLETED = "COMPLETED"
CHECK_CONCLUSION_SUCCESS = "SUCCESS"

HEAD_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SEMVER_TRIPLET_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

POLICY_DEFAULT_MODE = "report_only"

DOCKER_PATH_MARKERS = (
    "/dockerfile",
    "docker-compose",
    "compose/",
    "infrastructure/compose/",
)

GITHUB_ACTIONS_ECOSYSTEMS = frozenset({"github-actions", "github_actions"})
DOCKER_ECOSYSTEMS = frozenset({"docker", "docker-compose", "docker_compose"})

PATCH_UPDATE_TYPE = "version-update:semver-patch"
MINOR_UPDATE_TYPE = "version-update:semver-minor"
MAJOR_UPDATE_TYPE = "version-update:semver-major"

REASON_ELIGIBLE = "ELIGIBLE_ALLOWLISTED_PATCH"
REASON_REPORT_ONLY = "REPORT_ONLY"
REASON_AUTOMERGE_DISABLED = "AUTOMERGE_DISABLED"
REASON_AUTHOR = "AUTHOR_NOT_DEPENDABOT"
REASON_BASE = "BASE_BRANCH_NOT_ALLOWED"
REASON_HEAD = "HEAD_BRANCH_NOT_DEPENDABOT"
REASON_DRAFT = "PR_IS_DRAFT"
REASON_MANUAL_REVIEW = "MANUAL_REVIEW_REQUIRED"
REASON_COMMIT_COUNT = "COMMIT_COUNT_NOT_ONE"
REASON_COMMIT_AUTHOR = "COMMIT_AUTHOR_NOT_DEPENDABOT"
REASON_DIFF = "DIFF_NOT_VERIFIED"
REASON_FILE = "CHANGED_FILE_NOT_ALLOWED"
REASON_CONTROL_PLANE = "CONTROL_PLANE_CHANGE"
REASON_METADATA = "METADATA_INCOMPLETE"
REASON_UPDATE_TYPE = "UPDATE_TYPE_NOT_PATCH"
REASON_DEP_TYPE = "DEPENDENCY_TYPE_NOT_ALLOWED"
REASON_PACKAGE = "PACKAGE_NOT_ALLOWLISTED"
REASON_ECOSYSTEM = "ECOSYSTEM_NOT_ALLOWED"
REASON_RANGE = "RANGE_CHANGE"
REASON_DATE_VERSION = "DATE_VERSION_UNSUPPORTED"
REASON_POLICY = "POLICY_INVALID"
REASON_CHECK_MISSING = "REQUIRED_CHECK_MISSING"
REASON_CHECK_FAIL = "REQUIRED_CHECK_NOT_SUCCESS"
REASON_CHECK_AMBIGUOUS = "REQUIRED_CHECK_AMBIGUOUS"
REASON_BRANCH = "BRANCH_NOT_CURRENT"
REASON_MERGE_STATE = "MERGE_STATE_NOT_CLEAN"
REASON_API = "API_ERROR"
REASON_RUNTIME = "RUNTIME_DEPENDENCY_CHANGE"
REASON_DOCKER = "DOCKER_CHANGE"
REASON_ACTIONS = "GITHUB_ACTIONS_CHANGE"
REASON_FACTS_INVALID = "FACTS_INVALID"
FACTS_INVALID_SUMMARY = "HOLD: FACTS_INVALID"
REASON_EXECUTION_MODE = "EXECUTION_MODE_INVALID"
REASON_HEAD_SHA = "HEAD_SHA_INVALID"
REASON_VERSION_TRANSITION = "VERSION_TRANSITION_INVALID"

HOLD_EVALUATION_ORDER = (
    REASON_FACTS_INVALID,
    REASON_POLICY,
    REASON_EXECUTION_MODE,
    REASON_API,
    REASON_AUTHOR,
    REASON_BASE,
    REASON_HEAD,
    REASON_DRAFT,
    REASON_MANUAL_REVIEW,
    REASON_COMMIT_COUNT,
    REASON_COMMIT_AUTHOR,
    REASON_HEAD_SHA,
    REASON_DIFF,
    REASON_METADATA,
    REASON_RANGE,
    REASON_DATE_VERSION,
    REASON_VERSION_TRANSITION,
    REASON_UPDATE_TYPE,
    REASON_CONTROL_PLANE,
    REASON_ACTIONS,
    REASON_DOCKER,
    REASON_RUNTIME,
    REASON_ECOSYSTEM,
    REASON_PACKAGE,
    REASON_DEP_TYPE,
    REASON_FILE,
    REASON_CHECK_AMBIGUOUS,
    REASON_CHECK_MISSING,
    REASON_CHECK_FAIL,
    REASON_BRANCH,
    REASON_MERGE_STATE,
)


@dataclass(frozen=True)
class RequiredCheckFact:
    name: str
    status: str
    conclusion: str


@dataclass(frozen=True)
class DependabotAutopilotFacts:
    pr_author: str
    base_branch: str
    head_branch: str
    is_draft: bool
    labels: tuple[str, ...]
    head_sha: str
    commit_count: int
    commit_authors: tuple[str, ...]
    changed_files: tuple[str, ...]
    required_checks: tuple[RequiredCheckFact, ...]
    branch_is_current: bool
    merge_state: str
    ecosystem: str
    package_name: str
    dependency_type: str
    update_type: str
    current_version: str
    target_version: str
    metadata_complete: bool
    diff_verified: bool
    range_change: bool
    date_versioned: bool
    api_error: bool
    execution_mode: str
    kill_switch_enabled: bool


@dataclass(frozen=True)
class AllowlistPackageRule:
    dependency_type: str
    allowed_update_types: frozenset[str]
    allowed_files: frozenset[str]


@dataclass(frozen=True)
class AllowlistPolicy:
    schema_version: int
    default_mode: str
    entries: Mapping[str, Mapping[str, AllowlistPackageRule]]
    defaults: Mapping[str, str]
    valid: bool
    validation_errors: tuple[str, ...]


@dataclass(frozen=True)
class ClassificationResult:
    classification: Classification
    action: Action
    merge_authorized: bool
    reason_codes: tuple[str, ...]
    human_summary: str


def _normalize_login(value: str) -> str:
    login = (value or "").strip().lower()
    if login.startswith("app/"):
        return login
    return login


def _is_dependabot_login(login: str) -> bool:
    normalized = _normalize_login(login)
    return normalized in {_normalize_login(item) for item in DEPENDABOT_AUTHOR_LOGINS}


def _normalize_check_token(value: str) -> str:
    return (value or "").strip().upper()


def _path_is_control_plane(path: str) -> bool:
    if not isinstance(path, str):
        return True
    normalized = path.replace("\\", "/").lower()
    return normalized.startswith(".github/")


def _path_is_docker_surface(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    if "dockerfile" in normalized:
        return True
    return any(marker in normalized for marker in DOCKER_PATH_MARKERS)


def _path_is_runtime_surface(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    if normalized == "requirements.txt":
        return True
    return normalized.startswith("services/") and normalized.endswith(
        ("requirements.txt", "/requirements.txt")
    )


def _is_date_version(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    parts = text.split(".")
    if len(parts) != 3:
        return False
    if not all(part.isdigit() for part in parts):
        return False
    return len(parts[0]) == 4 and int(parts[0]) >= 1900


def _parse_semver_triplet(value: str) -> tuple[int, int, int] | None:
    text = (value or "").strip()
    if not text or _is_date_version(text):
        return None
    match = SEMVER_TRIPLET_PATTERN.fullmatch(text)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _version_transition_valid(current_version: str, target_version: str) -> bool:
    if _is_date_version(current_version) or _is_date_version(target_version):
        return False
    current = _parse_semver_triplet(current_version)
    target = _parse_semver_triplet(target_version)
    if current is None or target is None:
        return False
    if current[0] != target[0] or current[1] != target[1]:
        return False
    return target[2] > current[2]


def _is_valid_head_sha(value: str) -> bool:
    return bool(HEAD_SHA_PATTERN.match((value or "").strip().lower()))


def _is_safe_allowlist_path(path: str) -> bool:
    normalized = (path or "").strip()
    if not normalized:
        return False
    if "\\" in normalized:
        return False
    if normalized.startswith("/"):
        return False
    if ".." in normalized.split("/"):
        return False
    if _path_is_control_plane(normalized):
        return False
    if _path_is_docker_surface(normalized):
        return False
    if _path_is_runtime_surface(normalized):
        return False
    return True


def _ordered_unique(codes: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code in seen:
            continue
        seen.add(code)
        ordered.append(code)
    return tuple(ordered)


def _sort_hold_codes(codes: Sequence[str]) -> tuple[str, ...]:
    rank = {code: index for index, code in enumerate(HOLD_EVALUATION_ORDER)}
    return tuple(
        sorted(_ordered_unique(codes), key=lambda code: rank.get(code, len(rank)))
    )


def _safe_schema_version(value: Any) -> int | None:
    if type(value) is not int:
        return None
    return value


def _validate_default_mapping(defaults: Mapping[str, str], errors: list[str]) -> None:
    for key in ("unknown_package", "unknown_ecosystem", "additional_file"):
        raw = defaults.get(key, "HOLD")
        if raw not in ALLOWED_DEFAULT_VALUES:
            errors.append(f"defaults.{key} must be HOLD in schema v1")
    for key, value in defaults.items():
        if value not in ALLOWED_DEFAULT_VALUES:
            errors.append(f"defaults.{key} has unsupported value {value!r}")


def _validate_schema_v1_package_rule(
    eco_key: str,
    pkg_key: str,
    dependency_type: str,
    update_types: Sequence[str],
    allowed_files: Sequence[str],
    errors: list[str],
) -> None:
    if eco_key != SCHEMA_V1_ECOSYSTEM:
        errors.append(f"entries.{eco_key} is not allowed in schema v1")
    if dependency_type != SCHEMA_V1_DEPENDENCY_TYPE:
        errors.append(
            f"entries.{eco_key}.{pkg_key}.dependency_type must be "
            f"{SCHEMA_V1_DEPENDENCY_TYPE!r}"
        )
    if set(update_types) != {SCHEMA_V1_UPDATE_TYPE}:
        errors.append(
            f"entries.{eco_key}.{pkg_key}.allowed_update_types must contain only "
            f"{SCHEMA_V1_UPDATE_TYPE!r}"
        )
    for path in allowed_files:
        if not _is_safe_allowlist_path(path):
            errors.append(f"entries.{eco_key}.{pkg_key}.allowed_files has unsafe path")


def parse_allowlist_policy(raw: Mapping[str, Any] | None) -> AllowlistPolicy:
    errors: list[str] = []
    if raw is None:
        return AllowlistPolicy(
            0, "report_only", {}, {}, False, ("policy payload missing",)
        )

    if not isinstance(raw, Mapping):
        return AllowlistPolicy(
            0, "report_only", {}, {}, False, ("policy payload must be a mapping",)
        )

    schema_version_raw = raw.get("schema_version")
    schema_version = _safe_schema_version(schema_version_raw)
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {schema_version_raw!r}")

    default_mode = raw.get("default_mode", POLICY_DEFAULT_MODE)
    if default_mode != POLICY_DEFAULT_MODE:
        errors.append(
            f"default_mode must be {POLICY_DEFAULT_MODE!r} in schema v1; "
            f"got {default_mode!r}"
        )
        default_mode = POLICY_DEFAULT_MODE

    defaults_raw = raw.get("defaults") or {}
    if not isinstance(defaults_raw, Mapping):
        errors.append("defaults must be a mapping")

    defaults: dict[str, str] = {}
    if isinstance(defaults_raw, Mapping):
        for key, value in defaults_raw.items():
            defaults[str(key)] = str(value)
    _validate_default_mapping(defaults, errors)

    entries_raw = raw.get("entries")
    if isinstance(entries_raw, list):
        errors.append("entries must be a mapping")
        entries_raw = {}
    elif entries_raw is None:
        entries_raw = {}
    elif not isinstance(entries_raw, Mapping):
        errors.append("entries must be a mapping")
        entries_raw = {}

    parsed_entries: dict[str, dict[str, AllowlistPackageRule]] = {}
    seen_rules: set[tuple[str, str]] = set()

    for ecosystem, packages in entries_raw.items():
        if not isinstance(packages, Mapping):
            errors.append(f"entries.{ecosystem} must be a mapping")
            continue
        eco_key = str(ecosystem)
        parsed_entries.setdefault(eco_key, {})
        if not packages:
            errors.append(f"entries.{eco_key} must contain at least one package rule")
        for package_name, rule_raw in packages.items():
            if not isinstance(rule_raw, Mapping):
                errors.append(f"entries.{eco_key}.{package_name} must be a mapping")
                continue
            pkg_key = str(package_name)
            dedupe_key = (eco_key, pkg_key)
            if dedupe_key in seen_rules:
                errors.append(f"duplicate allowlist rule for {eco_key}/{pkg_key}")
                continue
            seen_rules.add(dedupe_key)

            dependency_type = str(rule_raw.get("dependency_type", "")).strip()
            if not dependency_type:
                errors.append(
                    f"entries.{eco_key}.{pkg_key}.dependency_type is required"
                )

            update_types_raw = rule_raw.get("allowed_update_types")
            if not isinstance(update_types_raw, list) or not update_types_raw:
                errors.append(
                    f"entries.{eco_key}.{pkg_key}.allowed_update_types must be a non-empty list"
                )
                update_types: list[str] = []
            else:
                update_types = [str(item) for item in update_types_raw]

            files_raw = rule_raw.get("allowed_files")
            if not isinstance(files_raw, list) or not files_raw:
                errors.append(
                    f"entries.{eco_key}.{pkg_key}.allowed_files must be a non-empty list"
                )
                allowed_files: list[str] = []
            else:
                allowed_files = [str(item) for item in files_raw]

            if schema_version == SUPPORTED_SCHEMA_VERSION:
                _validate_schema_v1_package_rule(
                    eco_key,
                    pkg_key,
                    dependency_type,
                    update_types,
                    allowed_files,
                    errors,
                )

            parsed_entries[eco_key][pkg_key] = AllowlistPackageRule(
                dependency_type=dependency_type,
                allowed_update_types=frozenset(update_types),
                allowed_files=frozenset(allowed_files),
            )

    package_rule_count = sum(len(pkgs) for pkgs in parsed_entries.values())
    if package_rule_count == 0:
        errors.append("entries must contain at least one valid package rule")

    valid = not errors and package_rule_count > 0
    return AllowlistPolicy(
        schema_version=schema_version if schema_version is not None else 0,
        default_mode=default_mode,
        entries=parsed_entries,
        defaults=defaults,
        valid=valid,
        validation_errors=tuple(errors),
    )


def _validate_facts(facts: DependabotAutopilotFacts) -> list[str]:
    reasons: list[str] = []

    required_strings = (
        facts.pr_author,
        facts.base_branch,
        facts.head_branch,
        facts.head_sha,
        facts.merge_state,
        facts.ecosystem,
        facts.package_name,
        facts.dependency_type,
        facts.update_type,
        facts.current_version,
        facts.target_version,
        facts.execution_mode,
    )
    if any(
        not isinstance(value, str) or not value.strip() for value in required_strings
    ):
        reasons.append(REASON_FACTS_INVALID)

    bool_fields = (
        facts.is_draft,
        facts.metadata_complete,
        facts.diff_verified,
        facts.range_change,
        facts.date_versioned,
        facts.api_error,
        facts.branch_is_current,
        facts.kill_switch_enabled,
    )
    if any(not isinstance(value, bool) for value in bool_fields):
        reasons.append(REASON_FACTS_INVALID)

    if not isinstance(facts.commit_count, int) or isinstance(facts.commit_count, bool):
        reasons.append(REASON_FACTS_INVALID)
    elif facts.commit_count < 0:
        reasons.append(REASON_FACTS_INVALID)

    if not isinstance(facts.labels, tuple) or any(
        not isinstance(label, str) for label in facts.labels
    ):
        reasons.append(REASON_FACTS_INVALID)

    if not isinstance(facts.commit_authors, tuple) or any(
        not isinstance(author, str) for author in facts.commit_authors
    ):
        reasons.append(REASON_FACTS_INVALID)

    if not isinstance(facts.changed_files, tuple) or any(
        not isinstance(path, str) for path in facts.changed_files
    ):
        reasons.append(REASON_FACTS_INVALID)

    if not isinstance(facts.required_checks, tuple):
        reasons.append(REASON_FACTS_INVALID)
    else:
        for check in facts.required_checks:
            if not isinstance(check, RequiredCheckFact):
                reasons.append(REASON_FACTS_INVALID)
                break
            if not isinstance(check.name, str) or not check.name.strip():
                reasons.append(REASON_FACTS_INVALID)
                break
            if not isinstance(check.status, str) or not isinstance(
                check.conclusion, str
            ):
                reasons.append(REASON_FACTS_INVALID)
                break
            if not check.status.strip() or not check.conclusion.strip():
                reasons.append(REASON_FACTS_INVALID)
                break

    return list(_ordered_unique(reasons))


def _execution_mode_valid(mode: str) -> bool:
    return (mode or "").strip() in ALLOWED_EXECUTION_MODES


def _lookup_package_rule(
    policy: AllowlistPolicy, ecosystem: str, package_name: str
) -> AllowlistPackageRule | None:
    eco_rules = policy.entries.get(ecosystem)
    if eco_rules is None:
        return None
    return eco_rules.get(package_name)


def _evaluate_required_checks(
    checks: Sequence[RequiredCheckFact],
) -> list[str]:
    reasons: list[str] = []
    grouped: dict[str, list[tuple[str, str]]] = {
        name: [] for name in REQUIRED_CHECK_NAMES
    }

    for check in checks:
        name = (check.name or "").strip()
        if name not in REQUIRED_CHECK_NAMES:
            continue
        status = _normalize_check_token(check.status)
        conclusion = _normalize_check_token(check.conclusion)
        grouped[name].append((status, conclusion))

    for required_name in REQUIRED_CHECK_NAMES:
        entries = grouped[required_name]
        if not entries:
            reasons.append(REASON_CHECK_MISSING)
            continue
        if len(entries) != 1:
            reasons.append(REASON_CHECK_AMBIGUOUS)
            continue
        status, conclusion = entries[0]
        if status != CHECK_STATUS_COMPLETED or conclusion != CHECK_CONCLUSION_SUCCESS:
            reasons.append(REASON_CHECK_FAIL)

    return reasons


def _collect_hold_reasons(
    facts: DependabotAutopilotFacts, policy: AllowlistPolicy
) -> list[str]:
    reasons: list[str] = []

    if not policy.valid:
        reasons.append(REASON_POLICY)
        return _ordered_unique(reasons)  # type: ignore[return-value]

    execution_mode = (facts.execution_mode or "").strip()
    if not _execution_mode_valid(execution_mode):
        reasons.append(REASON_EXECUTION_MODE)
    if not _execution_mode_valid(policy.default_mode):
        reasons.append(REASON_EXECUTION_MODE)

    if facts.api_error:
        reasons.append(REASON_API)

    if not _is_dependabot_login(facts.pr_author):
        reasons.append(REASON_AUTHOR)

    if facts.base_branch != DEFAULT_BASE_BRANCH:
        reasons.append(REASON_BASE)

    if not facts.head_branch.startswith(DEFAULT_HEAD_PREFIX):
        reasons.append(REASON_HEAD)

    if facts.is_draft:
        reasons.append(REASON_DRAFT)

    label_set = {label.lower() for label in facts.labels}
    if label_set.intersection({label.lower() for label in MANUAL_REVIEW_LABELS}):
        reasons.append(REASON_MANUAL_REVIEW)

    if facts.commit_count != 1:
        reasons.append(REASON_COMMIT_COUNT)

    if len(facts.commit_authors) != 1:
        reasons.append(REASON_COMMIT_AUTHOR)
    elif not _is_dependabot_login(facts.commit_authors[0]):
        reasons.append(REASON_COMMIT_AUTHOR)

    if not _is_valid_head_sha(facts.head_sha):
        reasons.append(REASON_HEAD_SHA)

    if not facts.diff_verified:
        reasons.append(REASON_DIFF)

    if not facts.metadata_complete:
        reasons.append(REASON_METADATA)

    if facts.range_change:
        reasons.append(REASON_RANGE)

    if (
        facts.date_versioned
        or _is_date_version(facts.current_version)
        or _is_date_version(facts.target_version)
    ):
        reasons.append(REASON_DATE_VERSION)

    if not _version_transition_valid(facts.current_version, facts.target_version):
        reasons.append(REASON_VERSION_TRANSITION)

    update_type = (facts.update_type or "").strip()
    if update_type in {MINOR_UPDATE_TYPE, MAJOR_UPDATE_TYPE}:
        reasons.append(REASON_UPDATE_TYPE)
    elif update_type != PATCH_UPDATE_TYPE:
        reasons.append(REASON_UPDATE_TYPE)

    changed_files = [path.replace("\\", "/") for path in facts.changed_files]
    if any(_path_is_control_plane(path) for path in changed_files):
        reasons.append(REASON_CONTROL_PLANE)

    ecosystem = (facts.ecosystem or "").strip().lower()
    if ecosystem in GITHUB_ACTIONS_ECOSYSTEMS or any(
        path.startswith(".github/workflows/") for path in changed_files
    ):
        reasons.append(REASON_ACTIONS)

    if ecosystem in DOCKER_ECOSYSTEMS or any(
        _path_is_docker_surface(path) for path in changed_files
    ):
        reasons.append(REASON_DOCKER)

    if any(_path_is_runtime_surface(path) for path in changed_files):
        reasons.append(REASON_RUNTIME)

    package_rule = _lookup_package_rule(policy, ecosystem, facts.package_name)
    if package_rule is None:
        reasons.append(REASON_ECOSYSTEM)
        reasons.append(REASON_PACKAGE)
    else:
        if facts.dependency_type != package_rule.dependency_type:
            reasons.append(REASON_DEP_TYPE)
        if update_type not in package_rule.allowed_update_types:
            reasons.append(REASON_UPDATE_TYPE)
        if changed_files and not all(
            path in package_rule.allowed_files for path in changed_files
        ):
            reasons.append(REASON_FILE)
        if len(changed_files) != len(package_rule.allowed_files):
            reasons.append(REASON_FILE)

    reasons.extend(_evaluate_required_checks(facts.required_checks))

    if not facts.branch_is_current:
        reasons.append(REASON_BRANCH)

    merge_state = (facts.merge_state or "").strip().upper()
    if merge_state != "CLEAN":
        reasons.append(REASON_MERGE_STATE)

    return list(_ordered_unique(reasons))


def _build_summary(
    classification: Classification,
    action: Action,
    merge_authorized: bool,
    reason_codes: Sequence[str],
    facts: DependabotAutopilotFacts,
) -> str:
    pkg = facts.package_name or "unknown-package"
    eco = facts.ecosystem or "unknown-ecosystem"
    if classification == "HOLD":
        primary = reason_codes[0] if reason_codes else REASON_POLICY
        return (
            f"HOLD for {eco}/{pkg}: {primary} "
            f"(head={facts.head_branch}, checks={len(facts.required_checks)})"
        )
    merge_hint = "merge authorized" if merge_authorized else "merge not authorized"
    return (
        f"ELIGIBLE {eco}/{pkg} patch via {action.lower().replace('_', ' ')}; "
        f"{merge_hint}"
    )


def _facts_invalid_hold_result() -> ClassificationResult:
    return ClassificationResult(
        classification="HOLD",
        action="HOLD",
        merge_authorized=False,
        reason_codes=(REASON_FACTS_INVALID,),
        human_summary=FACTS_INVALID_SUMMARY,
    )


def classify_dependabot_pr(
    facts: DependabotAutopilotFacts,
    policy: AllowlistPolicy,
) -> ClassificationResult:
    """Pure fail-closed classifier. Same inputs always yield the same decision."""
    if not isinstance(facts, DependabotAutopilotFacts):
        return _facts_invalid_hold_result()

    fact_errors = _validate_facts(facts)
    if fact_errors:
        return _facts_invalid_hold_result()

    hold_reasons = _collect_hold_reasons(facts, policy)
    if hold_reasons:
        codes = _sort_hold_codes(hold_reasons)
        return ClassificationResult(
            classification="HOLD",
            action="HOLD",
            merge_authorized=False,
            reason_codes=codes,
            human_summary=_build_summary("HOLD", "HOLD", False, codes, facts),
        )

    reason_codes: list[str] = [REASON_ELIGIBLE]
    execution_mode = (facts.execution_mode or "").strip()
    if execution_mode == "report_only":
        reason_codes.append(REASON_REPORT_ONLY)
        return ClassificationResult(
            classification="ELIGIBLE",
            action="REPORT_ONLY",
            merge_authorized=False,
            reason_codes=_ordered_unique(reason_codes),
            human_summary=_build_summary(
                "ELIGIBLE", "REPORT_ONLY", False, reason_codes, facts
            ),
        )

    if facts.kill_switch_enabled is not True:
        reason_codes.append(REASON_AUTOMERGE_DISABLED)
        return ClassificationResult(
            classification="ELIGIBLE",
            action="REPORT_ONLY",
            merge_authorized=False,
            reason_codes=_ordered_unique(reason_codes),
            human_summary=_build_summary(
                "ELIGIBLE", "REPORT_ONLY", False, reason_codes, facts
            ),
        )

    return ClassificationResult(
        classification="ELIGIBLE",
        action="MERGE_CANDIDATE",
        merge_authorized=True,
        reason_codes=_ordered_unique(reason_codes),
        human_summary=_build_summary(
            "ELIGIBLE", "MERGE_CANDIDATE", True, reason_codes, facts
        ),
    )


def load_allowlist_policy_from_mapping(raw: Mapping[str, Any]) -> AllowlistPolicy:
    """Parse and validate an allowlist mapping."""
    return parse_allowlist_policy(raw)
