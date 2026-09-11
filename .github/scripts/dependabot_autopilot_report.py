#!/usr/bin/env python3
"""Report-only Dependabot autopilot broker (read-only GitHub API adapter)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CLASSIFIER_PATH = (
    REPO_ROOT / ".github" / "scripts" / "dependabot_autopilot_classifier.py"
)
DEFAULT_ALLOWLIST = REPO_ROOT / ".github" / "dependabot-autopilot-allowlist.yml"

DEPENDABOT_LOGINS = frozenset({"dependabot[bot]", "app/dependabot"})
DEPENDABOT_HEAD_PREFIX = "dependabot/"

REQUIRED_CHECK_NAMES = (
    "ci (Unit/Integration + Lint gesammelt)",
    "policy-gate",
)
"""Live required merge checks per docs/runbooks/merge_policy_ci_gate.md.

These are hosted GitHub Actions Check Runs (`name`/`status`/`conclusion`) on
`main` (post-#4540). The local Fast-CI publisher (`cdb-local-ci`) is no longer
a required merge context and is not consulted here."""

ALLOWED_GET_ENDPOINT = re.compile(
    r"^repos/[^/]+/[^/]+/"
    r"(?:"
    r"pulls(?:/\d+(?:/(?:files|commits))?)?"
    r"|commits/[0-9a-f]{40}/check-runs"
    r"|compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40}"
    r")$"
)

PIP_REQ_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*([=<>~!]+)\s*(.+)$")
ACTIONS_USE_LINE = re.compile(r"^\s*uses:\s*([^\s@]+)@(.+?)\s*$", re.IGNORECASE)
# Accept optional digest pins (`image: name:tag@sha256:...`) used by Dependabot
# docker-compose updates in this repository.
DOCKER_IMAGE_LINE = re.compile(
    r"^\s*image:\s*"
    r"(?P<ref>[^\s@]+(?::[^\s@]+)?)"
    r"(?:@[A-Za-z0-9_+.:-]+)?"
    r"\s*$",
    re.IGNORECASE,
)

UPDATE_TYPE_UNKNOWN = "version-update:unknown"
DEPENDENCY_TYPE_UNKNOWN = "direct:unknown"
DOCKER_ECOSYSTEMS = frozenset({"docker", "docker-compose", "docker_compose"})

UPDATED_DEPENDENCY_BLOCK = re.compile(
    r"updated-dependencies:\s*\n"
    r"(?P<body>(?:"
    r"[ \t]*- dependency-name: .+\n"
    r"(?:[ \t]+(?:dependency-(?:version|type)|update-type): .+\n?)*"
    r")+)",
    re.MULTILINE,
)


class GitHubApiError(RuntimeError):
    """Raised when a read-only GitHub API call fails."""


class GlobalDiscoveryError(GitHubApiError):
    """Raised when PR discovery or repository metadata fetch fails."""


class GitHubReadTransport(Protocol):
    def get_json(
        self, endpoint: str, *, params: Mapping[str, str] | None = None
    ) -> Any:
        """Perform a paginated or single GET and return decoded JSON."""


_CLASSIFIER_MODULE: Any | None = None


def _load_classifier_module() -> Any:
    global _CLASSIFIER_MODULE
    if _CLASSIFIER_MODULE is not None:
        return _CLASSIFIER_MODULE

    module_name = "dependabot_autopilot_classifier"
    if module_name in sys.modules:
        _CLASSIFIER_MODULE = sys.modules[module_name]
        return _CLASSIFIER_MODULE

    spec = importlib.util.spec_from_file_location(module_name, CLASSIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load classifier from {CLASSIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _CLASSIFIER_MODULE = module
    return module


def _validate_get_endpoint(endpoint: str) -> None:
    normalized = endpoint.lstrip("/")
    if not ALLOWED_GET_ENDPOINT.fullmatch(normalized):
        raise GitHubApiError(
            f"endpoint not allowed for read-only transport: {endpoint}"
        )


def _iter_json_documents(raw: str) -> list[Any]:
    raw = raw.strip()
    if not raw:
        return []
    try:
        return [json.loads(raw)]
    except json.JSONDecodeError:
        documents: list[Any] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            documents.append(json.loads(line))
        return documents


def _merge_paginated_payload(documents: Sequence[Any]) -> Any:
    if not documents:
        return []
    if len(documents) == 1:
        return documents[0]

    if all(isinstance(doc, list) for doc in documents):
        merged: list[Any] = []
        for doc in documents:
            merged.extend(doc)
        return merged

    if all(isinstance(doc, Mapping) and "statuses" in doc for doc in documents):
        merged_statuses: list[Any] = []
        for doc in documents:
            merged_statuses.extend(doc.get("statuses") or [])
        return merged_statuses

    if all(isinstance(doc, Mapping) and "check_runs" in doc for doc in documents):
        merged_check_runs: list[Any] = []
        for doc in documents:
            merged_check_runs.extend(doc.get("check_runs") or [])
        return merged_check_runs

    return documents[-1]


class SubprocessGhTransport:
    """Production transport using `gh api --method GET` without shell=True."""

    def __init__(self, repo: str) -> None:
        self._repo = repo

    def get_json(
        self, endpoint: str, *, params: Mapping[str, str] | None = None
    ) -> Any:
        _validate_get_endpoint(endpoint)
        args = [
            "gh",
            "api",
            "--method",
            "GET",
            endpoint.lstrip("/"),
            "--paginate",
            "-H",
            "Accept: application/vnd.github+json",
        ]
        for key, value in (params or {}).items():
            args.extend(["-f", f"{key}={value}"])

        env = {**os.environ, "GH_REPO": self._repo}
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
            env=env,
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "").strip()
            raise GitHubApiError(
                f"gh api GET failed ({proc.returncode}) for {endpoint}: {stderr}"
            )

        try:
            documents = _iter_json_documents(proc.stdout or "")
        except json.JSONDecodeError as exc:
            raise GitHubApiError(
                f"malformed gh api paginated JSON for {endpoint}: {exc}"
            ) from exc
        payload = _merge_paginated_payload(documents)
        if isinstance(payload, Mapping) and "check_runs" in payload:
            return payload.get("check_runs") or []
        if isinstance(payload, Mapping) and "statuses" in payload:
            return payload.get("statuses") or []
        return payload


class InMemoryGhTransport:
    """Test transport keyed by endpoint prefix."""

    def __init__(self, routes: Mapping[str, Any]) -> None:
        self._routes = dict(routes)
        self.calls: list[str] = []

    def get_json(
        self, endpoint: str, *, params: Mapping[str, str] | None = None
    ) -> Any:
        _validate_get_endpoint(endpoint)
        self.calls.append(endpoint.lstrip("/"))
        normalized = endpoint.lstrip("/")
        for prefix in sorted(self._routes, key=len, reverse=True):
            prefix_norm = prefix.lstrip("/")
            if normalized == prefix_norm or normalized.startswith(f"{prefix_norm}/"):
                payload = self._routes[prefix]
                if callable(payload):
                    return payload(normalized, dict(params or {}))
                return payload
        raise GitHubApiError(f"no fixture for endpoint {endpoint}")


@dataclass(frozen=True)
class PullReportRow:
    pr_number: int
    head_branch: str
    package_name: str
    ecosystem: str
    classification: str
    action: str
    merge_authorized: bool
    reason_codes: tuple[str, ...]
    human_summary: str
    api_error: bool = False


@dataclass(frozen=True)
class ReportOutcome:
    rows: tuple[PullReportRow, ...]
    global_error: str | None = None
    exit_code: int = 0


def _normalize_login(value: str) -> str:
    return (value or "").strip().lower()


def _is_dependabot_login(login: str) -> bool:
    normalized = _normalize_login(login)
    return normalized in {_normalize_login(item) for item in DEPENDABOT_LOGINS}


_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TOKEN_PATTERNS = (
    re.compile(r"(?i)(gh[pousr]_[A-Za-z0-9_]{20,})"),
    re.compile(r"(?i)github_pat_[A-Za-z0-9_]{20,}"),
)
_BEARER_PATTERN = re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+")
_MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _redact_tokens(text: str) -> str:
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub("[REDACTED_TOKEN]", text)
    return _BEARER_PATTERN.sub("bearer [REDACTED]", text)


def _sanitize_markdown_table_cell(value: str) -> str:
    """Render dynamic summary values as safe single-line Markdown table cells."""
    text = _redact_tokens((value or "").strip())
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    text = re.sub(r"[\r\n]+", " ", text)
    text = _MARKDOWN_IMAGE_PATTERN.sub("[image]", text)
    text = _MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = _HTML_TAG_PATTERN.sub("", text)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("`", "'")
    return text.strip()


def _sanitize_summary_text(value: str) -> str:
    return _sanitize_markdown_table_cell(value)


def _infer_ecosystem_from_head_branch(head_branch: str) -> str:
    if not head_branch.startswith("dependabot/"):
        return ""
    segment = head_branch.removeprefix("dependabot/").split("/", 1)[0]
    return {
        "pip": "pip",
        "github_actions": "github-actions",
        "docker": "docker",
        "docker_compose": "docker-compose",
    }.get(segment, "")


def _fill_versions_from_metadata(
    dependabot_meta: Mapping[str, str],
    *,
    current_version: str,
    target_version: str,
) -> tuple[str, str]:
    target = target_version or str(dependabot_meta.get("dependency-version") or "")
    current = current_version
    if not current and target:
        current = target
    return current, target


def _parse_updated_dependencies(commit_messages: Sequence[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for message in commit_messages:
        match = UPDATED_DEPENDENCY_BLOCK.search(message or "")
        if not match:
            continue
        body = match.group("body")
        current: dict[str, str] = {}
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- dependency-name:"):
                if current.get("dependency-name"):
                    fields = {**fields, **current}
                current = {"dependency-name": stripped.split(":", 1)[1].strip()}
            elif stripped.startswith("dependency-version:"):
                current["dependency-version"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("dependency-type:"):
                current["dependency-type"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("update-type:"):
                current["update-type"] = stripped.split(":", 1)[1].strip()
        if current.get("dependency-name"):
            fields = {**fields, **current}
    return fields


def _parse_pip_patch(patch: str) -> dict[str, Any]:
    removed: dict[str, tuple[str, str]] = {}
    added: dict[str, tuple[str, str]] = {}
    if not patch:
        return {"verified": False, "reason": "missing_patch"}

    for line in patch.splitlines():
        if not line or line.startswith(("@@", "diff", "---", "+++", "index")):
            continue
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        body = line[1:].strip()
        match = PIP_REQ_LINE.match(body)
        if not match:
            continue
        package, op, version = match.group(1), match.group(2), match.group(3).strip()
        if line.startswith("-"):
            removed[package.lower()] = (op, version)
        else:
            added[package.lower()] = (op, version)

    if not removed or not added:
        return {"verified": False, "reason": "incomplete_patch"}

    packages = set(removed) & set(added)
    if len(packages) != 1:
        return {"verified": False, "reason": "ambiguous_package"}

    package = next(iter(packages))
    old_op, old_version = removed[package]
    new_op, new_version = added[package]
    return {
        "verified": True,
        "ecosystem": "pip",
        "package_name": package,
        "current_version": old_version,
        "target_version": new_version,
        "range_change": old_op != "==" or new_op != "==",
    }


def _parse_actions_patch(patch: str) -> dict[str, Any]:
    removed: dict[str, str] = {}
    added: dict[str, str] = {}
    if not patch:
        return {"verified": False, "reason": "missing_patch"}

    for line in patch.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        match = ACTIONS_USE_LINE.match(line[1:])
        if not match:
            continue
        action, ref = match.group(1), match.group(2)
        if line.startswith("-"):
            removed[action] = ref
        else:
            added[action] = ref

    if not removed or not added:
        return {"verified": False, "reason": "incomplete_patch"}
    actions = set(removed) & set(added)
    if len(actions) != 1:
        return {"verified": False, "reason": "ambiguous_action"}
    action = next(iter(actions))
    return {
        "verified": True,
        "ecosystem": "github-actions",
        "package_name": action,
        "current_version": removed[action],
        "target_version": added[action],
        "range_change": False,
    }


def _parse_docker_patch(patch: str) -> dict[str, Any]:
    removed: list[str] = []
    added: list[str] = []
    if not patch:
        return {"verified": False, "reason": "missing_patch"}

    for line in patch.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        match = DOCKER_IMAGE_LINE.match(line[1:])
        if not match:
            continue
        image_ref = match.group("ref")
        if line.startswith("-"):
            removed.append(image_ref)
        else:
            added.append(image_ref)

    if len(removed) != 1 or len(added) != 1:
        return {"verified": False, "reason": "ambiguous_docker_image"}
    old_image, new_image = removed[0], added[0]
    old_parts = old_image.rsplit(":", 1)
    new_parts = new_image.rsplit(":", 1)
    package = old_parts[0]
    return {
        "verified": True,
        "ecosystem": "docker-compose",
        "package_name": package,
        "current_version": old_parts[1] if len(old_parts) == 2 else "",
        "target_version": new_parts[1] if len(new_parts) == 2 else "",
        "range_change": False,
    }


def _path_is_compose_surface(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    if "compose" in normalized:
        return True
    return normalized.endswith(
        ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
    )


def _parse_file_patch(path: str, patch: str | None) -> dict[str, Any]:
    normalized = path.replace("\\", "/")
    if patch is None or patch == "":
        return {"verified": False, "reason": "missing_or_truncated_patch"}
    if normalized.endswith(".txt") or "requirements" in normalized:
        return _parse_pip_patch(patch)
    if normalized.startswith(".github/workflows/"):
        return _parse_actions_patch(patch)
    if _path_is_compose_surface(normalized):
        return _parse_docker_patch(patch)
    return {"verified": False, "reason": "unsupported_file"}


def _compatible_docker_facts(verified: Sequence[Mapping[str, Any]]) -> bool:
    if not verified:
        return False
    if not all(
        str(item.get("ecosystem") or "").lower() in DOCKER_ECOSYSTEMS
        for item in verified
    ):
        return False
    packages = {str(item.get("package_name") or "") for item in verified}
    currents = {str(item.get("current_version") or "") for item in verified}
    targets = {str(item.get("target_version") or "") for item in verified}
    return (
        len(packages) == 1
        and next(iter(packages)) != ""
        and len(currents) == 1
        and len(targets) == 1
    )


def _merge_patch_facts(file_entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    parsed: list[dict[str, Any]] = []
    changed_files: list[str] = []
    for entry in file_entries:
        path = str(entry.get("filename") or entry.get("path") or "")
        if not path:
            return {"verified": False, "reason": "missing_filename"}
        changed_files.append(path)
        parsed.append(_parse_file_patch(path, entry.get("patch")))

    if not parsed:
        return {"verified": False, "reason": "no_files", "changed_files": tuple()}

    verified = [item for item in parsed if item.get("verified")]
    if len(verified) == 1 and len(parsed) == 1:
        result = dict(verified[0])
        result["changed_files"] = tuple(changed_files)
        return result

    # Multi-file docker-compose bumps (same image across compose files) are a
    # single logical update and must classify as DOCKER_CHANGE, not FACTS_INVALID.
    if len(verified) == len(parsed) and _compatible_docker_facts(verified):
        result = dict(verified[0])
        result["changed_files"] = tuple(changed_files)
        return result

    reason = "ambiguous_or_multi_file"
    if not verified:
        reason = "unverified_patch"
    return {
        "verified": False,
        "reason": reason,
        "changed_files": tuple(changed_files),
    }


def _infer_update_type(current_version: str, target_version: str) -> str:
    """Best-effort semver update-type; empty when not deterministically inferable."""
    classifier = _load_classifier_module()
    current = classifier._parse_semver_triplet(current_version)
    target = classifier._parse_semver_triplet(target_version)
    if current is None or target is None:
        return ""
    if target[0] != current[0]:
        return "version-update:semver-major"
    if target[1] != current[1]:
        return "version-update:semver-minor"
    if target[2] != current[2]:
        return "version-update:semver-patch"
    return ""


def _identity_fields_present(
    *,
    ecosystem: str,
    package_name: str,
    current_version: str,
    target_version: str,
) -> bool:
    return all(
        isinstance(value, str) and value.strip()
        for value in (ecosystem, package_name, current_version, target_version)
    )


def _apply_fail_closed_metadata_defaults(
    *,
    dependency_type: str,
    update_type: str,
    current_version: str,
    target_version: str,
    identity_known: bool,
) -> tuple[str, str]:
    """Fill missing Dependabot metadata only when package identity is known.

    Incomplete identity stays empty so the classifier returns FACTS_INVALID.
    Known identity with missing update-/dependency-type becomes an explicit
    unknown sentinel that yields a concrete HOLD reason instead.
    """
    if not identity_known:
        return dependency_type, update_type

    resolved_dependency = dependency_type.strip() or DEPENDENCY_TYPE_UNKNOWN
    resolved_update = update_type.strip()
    if not resolved_update:
        resolved_update = (
            _infer_update_type(current_version, target_version) or UPDATE_TYPE_UNKNOWN
        )
    return resolved_dependency, resolved_update


def _normalize_merge_state(raw: str | None) -> str:
    value = (raw or "").strip().upper()
    if value == "CLEAN":
        return "CLEAN"
    if value in {"BEHIND", "BLOCKED", "DIRTY", "UNSTABLE", "UNKNOWN"}:
        return value
    return "UNKNOWN"


_STATUS_STATE_MAP: dict[str, tuple[str, str]] = {
    "success": ("COMPLETED", "SUCCESS"),
    "failure": ("COMPLETED", "FAILURE"),
    "error": ("COMPLETED", "FAILURE"),
    "pending": ("IN_PROGRESS", "PENDING"),
}

_CHECK_RUN_STATUS_MAP: dict[str, tuple[str, str]] = {
    "completed": ("COMPLETED", "SUCCESS"),
    "queued": ("IN_PROGRESS", "PENDING"),
    "in_progress": ("IN_PROGRESS", "PENDING"),
    "waiting": ("IN_PROGRESS", "PENDING"),
}


def _normalize_required_check_facts(
    statuses: Sequence[Mapping[str, Any]],
) -> list[Any]:
    """Map Check Run entries (`name`/`status`/`conclusion`) to RequiredCheckFact.

    The post-#4540 merge gate (`ci (Unit/Integration + Lint gesammelt)`,
    `policy-gate`) is published by hosted GitHub Actions as Check Runs, so the
    live payload shape is `name`/`status`/`conclusion`. Commit Status entries
    (`context`/`state`) are no longer consulted.
    """
    classifier = _load_classifier_module()
    facts: list[Any] = []
    for entry in statuses:
        name = str(entry.get("name") or "").strip()
        if name not in REQUIRED_CHECK_NAMES:
            continue
        raw_status = str(entry.get("status") or "").strip().lower()
        conclusion = str(entry.get("conclusion") or "").strip().lower()
        if raw_status == "completed":
            if conclusion == "success":
                status, normalized_conclusion = "COMPLETED", "SUCCESS"
            elif conclusion in (
                "failure",
                "cancelled",
                "timed_out",
                "action_required",
                "startup_failure",
                "stale",
            ):
                status, normalized_conclusion = "COMPLETED", "FAILURE"
            else:
                status, normalized_conclusion = "UNKNOWN", "UNKNOWN"
        elif raw_status in ("queued", "in_progress", "waiting"):
            status, normalized_conclusion = "IN_PROGRESS", "PENDING"
        else:
            status, normalized_conclusion = "UNKNOWN", "UNKNOWN"
        facts.append(classifier.RequiredCheckFact(name, status, normalized_conclusion))
    return facts


def _extract_commit_author_logins(commit: Mapping[str, Any]) -> list[str]:
    """Return GitHub login(s) for a pull commit payload.

    Live REST ``pulls/{n}/commits`` exposes a singular ``author.login``; tests
    may also supply a plural ``authors`` list.
    """
    logins: list[str] = []
    author = commit.get("author")
    if isinstance(author, Mapping):
        login = str(author.get("login") or "").strip()
        if login:
            logins.append(login)
    if logins:
        return logins
    for author_entry in commit.get("authors") or []:
        if isinstance(author_entry, Mapping):
            login = str(author_entry.get("login") or "").strip()
            if login:
                logins.append(login)
    return logins


def _compare_branch_current(
    transport: GitHubReadTransport, repo: str, base_sha: str, head_sha: str
) -> tuple[bool, bool]:
    endpoint = f"repos/{repo}/compare/{base_sha}...{head_sha}"
    try:
        payload = transport.get_json(endpoint)
    except GitHubApiError:
        return False, True
    if not isinstance(payload, Mapping):
        return False, True
    behind_by = payload.get("behind_by")
    if not isinstance(behind_by, int):
        return False, True
    return behind_by == 0, False


def _api_error_facts(classifier: Any, execution_mode: str) -> Any:
    return classifier.DependabotAutopilotFacts(
        pr_author="dependabot[bot]",
        base_branch="main",
        head_branch="dependabot/unknown",
        is_draft=False,
        labels=(),
        head_sha="0" * 40,
        commit_count=0,
        commit_authors=(),
        changed_files=(),
        required_checks=(),
        branch_is_current=False,
        merge_state="UNKNOWN",
        ecosystem="pip",
        package_name="unknown",
        dependency_type="direct:development",
        update_type="version-update:semver-patch",
        current_version="0.0.0",
        target_version="0.0.1",
        metadata_complete=False,
        diff_verified=False,
        range_change=False,
        date_versioned=False,
        api_error=True,
        execution_mode=execution_mode,
        kill_switch_enabled=False,
    )


def _build_facts_for_pull(
    transport: GitHubReadTransport,
    repo: str,
    pull: Mapping[str, Any],
    *,
    execution_mode: str,
) -> Any:
    classifier = _load_classifier_module()
    api_error = False

    try:
        pr_number = int(pull["number"])
        endpoint = f"repos/{repo}/pulls/{pr_number}"
        detail = transport.get_json(endpoint)
        commits = transport.get_json(f"{endpoint}/commits")
        files = transport.get_json(f"{endpoint}/files")
    except (GitHubApiError, KeyError, TypeError, ValueError):
        return _api_error_facts(classifier, execution_mode)

    author = ""
    user = detail.get("user") or {}
    if isinstance(user, Mapping):
        author = str(user.get("login") or "")

    base = detail.get("base") or {}
    head = detail.get("head") or {}
    base_branch = str(base.get("ref") or "")
    head_branch = str(head.get("ref") or "")
    base_sha = str(base.get("sha") or "")
    head_sha = str(head.get("sha") or "")

    labels = tuple(
        str(item.get("name") or "")
        for item in (detail.get("labels") or [])
        if isinstance(item, Mapping)
    )

    commit_items = commits if isinstance(commits, list) else []
    commit_authors: list[str] = []
    commit_messages: list[str] = []
    for commit in commit_items:
        if not isinstance(commit, Mapping):
            continue
        commit_obj = commit.get("commit") or {}
        if isinstance(commit_obj, Mapping):
            commit_messages.append(str(commit_obj.get("message") or ""))
        commit_authors.extend(_extract_commit_author_logins(commit))

    file_items = files if isinstance(files, list) else []
    patch_facts = _merge_patch_facts(file_items)

    required_check_entries: list[Mapping[str, Any]] = []
    if head_sha:
        try:
            payload = transport.get_json(
                f"repos/{repo}/commits/{head_sha}/check-runs",
                params={"per_page": "100"},
            )
            if isinstance(payload, Mapping):
                check_runs = payload.get("check_runs")
                payload = check_runs if isinstance(check_runs, list) else None
            if isinstance(payload, list):
                required_check_entries = [
                    item for item in payload if isinstance(item, Mapping)
                ]
        except GitHubApiError:
            api_error = True

    branch_is_current = False
    if base_sha and head_sha:
        branch_is_current, compare_api_error = _compare_branch_current(
            transport, repo, base_sha, head_sha
        )
        api_error = api_error or compare_api_error

    merge_state = _normalize_merge_state(str(detail.get("mergeable_state") or ""))

    dependabot_meta = _parse_updated_dependencies(commit_messages)
    diff_verified = bool(patch_facts.get("verified"))

    ecosystem = str(patch_facts.get("ecosystem") or "")
    package_name = str(patch_facts.get("package_name") or "")
    current_version = str(patch_facts.get("current_version") or "")
    target_version = str(patch_facts.get("target_version") or "")
    range_change = bool(patch_facts.get("range_change"))
    changed_files_tuple = tuple(patch_facts.get("changed_files") or ())
    if not changed_files_tuple and file_items:
        changed_files_tuple = tuple(
            str(item.get("filename") or item.get("path") or "")
            for item in file_items
            if isinstance(item, Mapping)
            and str(item.get("filename") or item.get("path") or "")
        )

    if not ecosystem:
        ecosystem = _infer_ecosystem_from_head_branch(head_branch)
    if not ecosystem and any(
        path.startswith(".github/workflows/") for path in changed_files_tuple
    ):
        ecosystem = "github-actions"
    if not ecosystem and any(
        _path_is_compose_surface(path) for path in changed_files_tuple
    ):
        ecosystem = "docker-compose"

    if dependabot_meta:
        if not package_name:
            package_name = dependabot_meta.get("dependency-name", "")
        current_version, target_version = _fill_versions_from_metadata(
            dependabot_meta,
            current_version=current_version,
            target_version=target_version,
        )

    metadata_complete = diff_verified
    if dependabot_meta:
        meta_name = dependabot_meta.get("dependency-name", "")
        if (
            diff_verified
            and package_name
            and meta_name
            and package_name.lower() != meta_name.lower()
        ):
            metadata_complete = False
            # Prefer the Dependabot metadata name when it contradicts a short
            # path-derived token so docker image refs stay aligned.
            if "/" in meta_name and "/" not in package_name:
                if package_name.lower() == meta_name.split("/")[-1].lower():
                    package_name = meta_name
                    metadata_complete = diff_verified
    elif not diff_verified:
        metadata_complete = False

    dependency_type = dependabot_meta.get("dependency-type", "")
    update_type = dependabot_meta.get("update-type", "")
    if diff_verified and (not dependency_type or not update_type):
        metadata_complete = False

    identity_known = _identity_fields_present(
        ecosystem=ecosystem,
        package_name=package_name,
        current_version=current_version,
        target_version=target_version,
    )
    dependency_type, update_type = _apply_fail_closed_metadata_defaults(
        dependency_type=dependency_type,
        update_type=update_type,
        current_version=current_version,
        target_version=target_version,
        identity_known=identity_known,
    )

    date_versioned = classifier._is_date_version(
        current_version
    ) or classifier._is_date_version(target_version)

    return classifier.DependabotAutopilotFacts(
        pr_author=author,
        base_branch=base_branch,
        head_branch=head_branch,
        is_draft=bool(detail.get("draft")),
        labels=labels,
        head_sha=head_sha,
        commit_count=len(commit_items),
        commit_authors=tuple(commit_authors),
        changed_files=changed_files_tuple,
        required_checks=tuple(_normalize_required_check_facts(required_check_entries)),
        branch_is_current=branch_is_current,
        merge_state=merge_state,
        ecosystem=ecosystem,
        package_name=package_name,
        dependency_type=dependency_type,
        update_type=update_type,
        current_version=current_version,
        target_version=target_version,
        metadata_complete=metadata_complete,
        diff_verified=diff_verified,
        range_change=range_change,
        date_versioned=date_versioned,
        api_error=api_error,
        execution_mode=execution_mode,
        kill_switch_enabled=False,
    )


def list_dependabot_pulls(
    transport: GitHubReadTransport, repo: str
) -> list[Mapping[str, Any]]:
    pulls = transport.get_json(f"repos/{repo}/pulls", params={"state": "open"})
    if not isinstance(pulls, list):
        raise GlobalDiscoveryError("pull list payload was not a list")

    selected: list[Mapping[str, Any]] = []
    for pull in pulls:
        if not isinstance(pull, Mapping):
            continue
        user = pull.get("user") or {}
        login = str(user.get("login") or "") if isinstance(user, Mapping) else ""
        head = pull.get("head") or {}
        head_ref = str(head.get("ref") or "") if isinstance(head, Mapping) else ""
        if _is_dependabot_login(login) or head_ref.startswith(DEPENDABOT_HEAD_PREFIX):
            selected.append(pull)
    selected.sort(key=lambda item: int(item.get("number") or 0))
    return selected


def classify_pulls(
    transport: GitHubReadTransport,
    repo: str,
    policy: Any,
    *,
    execution_mode: str = "report_only",
) -> ReportOutcome:
    classifier = _load_classifier_module()
    try:
        pulls = list_dependabot_pulls(transport, repo)
    except GitHubApiError as exc:
        return ReportOutcome((), global_error=str(exc), exit_code=1)

    rows: list[PullReportRow] = []
    for pull in pulls:
        pr_number = int(pull.get("number") or 0)
        head = pull.get("head") or {}
        head_branch = str(head.get("ref") or "") if isinstance(head, Mapping) else ""
        facts = _build_facts_for_pull(
            transport, repo, pull, execution_mode=execution_mode
        )
        result = classifier.classify_dependabot_pr(facts, policy)
        rows.append(
            PullReportRow(
                pr_number=pr_number,
                head_branch=head_branch,
                package_name=facts.package_name,
                ecosystem=facts.ecosystem,
                classification=result.classification,
                action=result.action,
                merge_authorized=result.merge_authorized,
                reason_codes=result.reason_codes,
                human_summary=result.human_summary,
                api_error=facts.api_error,
            )
        )
    return ReportOutcome(tuple(rows), None, 0)


def render_job_summary(
    outcome: ReportOutcome,
    *,
    execution_mode: str,
    repo: str,
) -> str:
    lines = [
        "## Dependabot Autopilot Report",
        "",
        f"- Mode: `{_sanitize_markdown_table_cell(execution_mode)}`",
        f"- Repository: `{_sanitize_markdown_table_cell(repo)}`",
        "- merge_authorized: `false` (report-only phase)",
        "",
    ]

    if outcome.global_error:
        lines.extend(
            [
                "### Global API Error",
                "",
                "- status: `API_ERROR`",
                f"- detail: `{_sanitize_markdown_table_cell(outcome.global_error)}`",
                "",
                "No Dependabot queue classification was produced.",
            ]
        )
        return "\n".join(lines) + "\n"

    if not outcome.rows:
        lines.extend(["No open Dependabot pull requests were discovered.", ""])
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "| PR | Classification | Action | merge_authorized | Reason Codes | Package | Ecosystem |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in outcome.rows:
        reasons = ", ".join(row.reason_codes)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"#{row.pr_number}",
                    f"`{_sanitize_markdown_table_cell(row.classification)}`",
                    f"`{_sanitize_markdown_table_cell(row.action)}`",
                    "`false`",
                    f"`{_sanitize_markdown_table_cell(reasons)}`",
                    f"`{_sanitize_markdown_table_cell(row.package_name or 'unknown')}`",
                    f"`{_sanitize_markdown_table_cell(row.ecosystem or 'unknown')}`",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def run_report(
    transport: GitHubReadTransport,
    repo: str,
    allowlist_path: Path,
    *,
    execution_mode: str = "report_only",
) -> ReportOutcome:
    classifier = _load_classifier_module()
    raw = yaml.safe_load(allowlist_path.read_text(encoding="utf-8"))
    policy = classifier.parse_allowlist_policy(raw)
    return classify_pulls(
        transport,
        repo,
        policy,
        execution_mode=execution_mode,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument(
        "--allowlist-path",
        type=Path,
        default=DEFAULT_ALLOWLIST,
    )
    parser.add_argument("--summary-file", type=Path, required=True)
    parser.add_argument("--execution-mode", default="report_only")
    args = parser.parse_args(argv)

    exit_code = 0
    outcome: ReportOutcome
    try:
        transport = SubprocessGhTransport(args.repo)
        outcome = run_report(
            transport,
            args.repo,
            args.allowlist_path,
            execution_mode=args.execution_mode,
        )
        exit_code = outcome.exit_code
    except Exception as exc:  # noqa: BLE001 - broker must surface failures in summary
        outcome = ReportOutcome((), global_error=str(exc), exit_code=1)
        exit_code = 1

    summary = render_job_summary(
        outcome,
        execution_mode=args.execution_mode,
        repo=args.repo,
    )
    args.summary_file.parent.mkdir(parents=True, exist_ok=True)
    args.summary_file.write_text(summary, encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
