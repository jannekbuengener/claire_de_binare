"""Shared helpers for workflow control-plane contract tests (#3844–#3852)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOW_REGISTER_MD = REPO_ROOT / "docs" / "runbooks" / "GITHUB_WORKFLOW_REGISTER.md"
CONTROL_PLANE_REGISTER_JSON = (
    REPO_ROOT / ".github" / "control-plane" / "generated" / "workflow-register.json"
)
REQUIRED_CHECKS_BASELINE = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "reports"
    / "REQUIRED_CHECK_CONTEXTS_BASELINE_main.json"
)

WRITE_PERMISSION_SCOPES = frozenset(
    {
        "issues:write",
        "pull-requests:write",
        "contents:write",
        "id-token:write",
    }
)

FORBIDDEN_TRIGGERS = frozenset({"pull_request_target"})

AUTOMATIC_TRIGGERS = frozenset(
    {
        "push",
        "pull_request",
        "schedule",
        "issues",
        "issue_comment",
        "pull_request_review_comment",
        "repository_dispatch",
        "workflow_run",
    }
)

PARKED_WORKFLOW_FILES: frozenset[str] = frozenset()

FROZEN_LEGACY_WORKFLOW_FILES: frozenset[str] = frozenset()

ACTIVE_CANONICAL_CI_WORKFLOW = "ci.yml"

REQUIRED_CHECK_CONTEXTS = frozenset(
    {
        "ci (Unit/Integration + Lint gesammelt)",
        "policy-gate",
    }
)
"""Hosted GitHub Actions required check contexts on `main` (post-#4540).

SSOT: docs/runbooks/merge_policy_ci_gate.md; live baseline snapshot at
docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json.
"""

NON_REQUIRED_GUARD_WORKFLOWS = frozenset(
    {
        "repository-canon-guard.yml",
        "docs-conflict-guard.yml",
    }
)

# Repo-true explicit findings: workflows on disk not listed in the markdown register.
# Tests surface these as findings; register correction is a separate follow-up.
KNOWN_UNREGISTERED_WORKFLOWS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class WorkflowInventoryFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class WorkflowInventoryScan:
    disk_workflows: tuple[str, ...]
    register_workflows: tuple[str, ...]
    control_plane_workflows: tuple[str, ...]
    unregistered_on_disk: tuple[str, ...]
    missing_on_disk: tuple[str, ...]
    control_plane_missing_on_disk: tuple[str, ...]
    findings: tuple[WorkflowInventoryFinding, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkflowTriggerPermissionRow:
    filename: str
    triggers: tuple[str, ...]
    write_permissions: tuple[str, ...]
    forbidden_triggers: tuple[str, ...]
    has_explicit_permissions: bool
    has_top_level_permissions: bool
    has_job_level_permissions: bool


def list_workflow_yaml_files(workflows_dir: Path) -> list[str]:
    if not workflows_dir.exists():
        return []
    files = [
        path.name
        for path in workflows_dir.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    ]
    return sorted(files)


def parse_register_table_workflows(register_path: Path) -> list[str]:
    text = register_path.read_text(encoding="utf-8")
    names = re.findall(r"\| `([^`]+\.(?:yml|yaml))` \|", text)
    return sorted(set(names))


def parse_control_plane_register_workflows(register_json_path: Path) -> list[str]:
    payload = json.loads(register_json_path.read_text(encoding="utf-8"))
    units = payload.get("units") or []
    paths: list[str] = []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        workflow_path = unit.get("workflow_path")
        if isinstance(workflow_path, str) and workflow_path.strip():
            paths.append(workflow_path.rsplit("/", 1)[-1])
    return sorted(set(paths))


def load_workflow_yaml(workflow_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Workflow YAML must be a mapping: {workflow_path}")
    return payload


def extract_on_triggers(workflow: dict[str, Any]) -> set[str]:
    on_section = workflow.get("on") or workflow.get(True)
    if on_section is None:
        return set()
    if isinstance(on_section, str):
        return {on_section}
    if isinstance(on_section, list):
        return {str(item) for item in on_section}
    if isinstance(on_section, dict):
        return {str(key) for key in on_section}
    return set()


def extract_top_level_permissions(workflow: dict[str, Any]) -> dict[str, str]:
    permissions = workflow.get("permissions")
    if permissions is None:
        return {}
    if permissions == {}:
        return {}
    if not isinstance(permissions, dict):
        return {}
    return {str(key): str(value) for key, value in permissions.items()}


def extract_job_level_permissions(workflow: dict[str, Any]) -> dict[str, str]:
    merged: dict[str, str] = {}
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return merged
    for job_def in jobs.values():
        if not isinstance(job_def, dict):
            continue
        perms = job_def.get("permissions")
        if not isinstance(perms, dict):
            continue
        for scope, level in perms.items():
            merged[str(scope)] = str(level)
    return merged


def extract_effective_permissions(workflow: dict[str, Any]) -> dict[str, str]:
    effective = dict(extract_top_level_permissions(workflow))
    effective.update(extract_job_level_permissions(workflow))
    return effective


def classify_write_permissions(permissions: dict[str, str]) -> set[str]:
    classified: set[str] = set()
    for scope, level in permissions.items():
        if str(level).lower() != "write":
            continue
        token = f"{scope}:write"
        if token in WRITE_PERMISSION_SCOPES:
            classified.add(token)
    return classified


def build_trigger_permission_row(workflow_path: Path) -> WorkflowTriggerPermissionRow:
    workflow = load_workflow_yaml(workflow_path)
    triggers = tuple(sorted(extract_on_triggers(workflow)))
    top_level = extract_top_level_permissions(workflow)
    job_level = extract_job_level_permissions(workflow)
    effective = extract_effective_permissions(workflow)
    write_permissions = tuple(sorted(classify_write_permissions(effective)))
    forbidden = tuple(sorted(FORBIDDEN_TRIGGERS.intersection(set(triggers))))
    return WorkflowTriggerPermissionRow(
        filename=workflow_path.name,
        triggers=triggers,
        write_permissions=write_permissions,
        forbidden_triggers=forbidden,
        has_explicit_permissions=bool(top_level or job_level),
        has_top_level_permissions=bool(top_level),
        has_job_level_permissions=bool(job_level),
    )


def scan_workflow_inventory(
    *,
    workflows_dir: Path,
    register_md_path: Path,
    control_plane_json_path: Path,
) -> WorkflowInventoryScan:
    disk = tuple(list_workflow_yaml_files(workflows_dir))
    register = tuple(parse_register_table_workflows(register_md_path))
    control_plane = tuple(
        parse_control_plane_register_workflows(control_plane_json_path)
    )

    disk_set = set(disk)
    register_set = set(register)
    control_plane_set = set(control_plane)

    unregistered = tuple(sorted(disk_set - register_set))
    missing_on_disk = tuple(sorted(register_set - disk_set))
    cp_missing = tuple(sorted(control_plane_set - disk_set))

    findings: list[WorkflowInventoryFinding] = []
    for name in unregistered:
        findings.append(
            WorkflowInventoryFinding(
                kind="unregistered_workflow",
                detail=f"{name} exists on disk but is missing from GITHUB_WORKFLOW_REGISTER.md",
            )
        )
    for name in missing_on_disk:
        findings.append(
            WorkflowInventoryFinding(
                kind="register_missing_file",
                detail=f"{name} is listed in GITHUB_WORKFLOW_REGISTER.md but missing on disk",
            )
        )
    for name in cp_missing:
        findings.append(
            WorkflowInventoryFinding(
                kind="control_plane_missing_file",
                detail=(
                    f"{name} is listed in workflow-register.json but missing on disk"
                ),
            )
        )

    return WorkflowInventoryScan(
        disk_workflows=disk,
        register_workflows=register,
        control_plane_workflows=control_plane,
        unregistered_on_disk=unregistered,
        missing_on_disk=missing_on_disk,
        control_plane_missing_on_disk=cp_missing,
        findings=tuple(findings),
    )


REGISTER_STATUS_TOKENS = frozenset(
    {
        "aktiv",
        "manual-only",
        "parked",
        "historisch",
        "**parked**",
    }
)


def parse_register_status_map(register_path: Path) -> dict[str, str]:
    text = register_path.read_text(encoding="utf-8")
    status_map: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("| `") or line.count("|") < 3:
            continue
        cols = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cols) < 2:
            continue
        filename = cols[0].strip("`")
        if not filename.endswith((".yml", ".yaml")):
            continue
        status = cols[1].lower()
        if status not in {token.lower() for token in REGISTER_STATUS_TOKENS}:
            continue
        status_map[filename] = status
    return status_map


def workflow_has_only_dispatch_trigger(workflow_path: Path) -> bool:
    workflow = load_workflow_yaml(workflow_path)
    triggers = extract_on_triggers(workflow)
    return triggers == {"workflow_dispatch"}


def workflow_declares_forbidden_trigger(workflow_path: Path) -> list[str]:
    workflow = load_workflow_yaml(workflow_path)
    triggers = extract_on_triggers(workflow)
    return sorted(FORBIDDEN_TRIGGERS.intersection(triggers))


def load_required_checks_baseline(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    contexts = payload.get("contexts") or []
    return sorted(
        {
            str(ctx).strip()
            for ctx in contexts
            if isinstance(ctx, str) and str(ctx).strip()
        }
    )


def load_commit_status_contexts(path: Path) -> list[str]:
    """Load non-workflow required contexts (App Check Run after #4170 Phase D).

    Prefers ``check_run_contexts``; falls back to legacy ``commit_status_contexts``
    / ``external_contexts`` keys for older baselines.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "check_run_contexts" in payload:
        raw = payload.get("check_run_contexts") or []
    elif "commit_status_contexts" in payload:
        raw = payload.get("commit_status_contexts") or []
    else:
        raw = payload.get("external_contexts") or []
    return sorted(
        {str(ctx).strip() for ctx in raw if isinstance(ctx, str) and str(ctx).strip()}
    )


# --- P1 scope (#3848–#3852) -------------------------------------------------

LABEL_CASCADE_WORKFLOW_FILES = frozenset(
    {
        "auto-milestone.yml",
        "auto-milestone-label-dispatch.yml",
        "project_status_sync.yml",
        "project_status_label_map.yml",
        "triage_guard.yml",
        "add_to_project.yml",
        "sync-labels.yml",
    }
)

ISSUES_LABELED_CASCADE_FILES = frozenset(
    {
        "auto-milestone-label-dispatch.yml",
        "project_status_label_map.yml",
    }
)

MILESTONE_DISPATCH_CASCADE = (
    (
        "auto-milestone-label-dispatch.yml",
        "auto_milestone_issue_label",
        "auto-milestone.yml",
    ),
)

PROJECT_API_MARKERS = (
    "gh api graphql",
    "projectV2",
    "addProjectV2ItemById",
    "updateProjectV2ItemFieldValue",
    "ensure_project_membership.py",
)

REUSABLE_GEMINI_WORKFLOW_FILES: frozenset[str] = frozenset()

REACHABLE_AGENT_AI_WORKFLOW_FILES = frozenset(
    {
        "opencode.yml",
        "copilot-setup-steps.yml",
        "copilot-housekeeping.yml",
        "ai-review-router.yml",
    }
)

SECURITY_WORKFLOW_FILES = frozenset(
    {
        "trivy.yml",
        "gitleaks.yml",
        "codeql-python.yml",
        "security-scan.yml",
        "security-alert-readout.yml",
    }
)

P1_SCHEDULED_WORKFLOW_FILES = frozenset(
    {
        "weekly_digest.yml",
        "weekly_digest_failure_alert.yml",
        "cdb-daily-delta-triage.yml",
        "cdb-weekly-control-hygiene-classifier.yml",
        "cdb-context-refresh-report.yml",
        "stale.yml",
        "python-compat.yml",
        "e2e.yml",
        "e2e-tests.yml",
        "e2e-happy-path.yaml",
    }
)

CONTROL_PLANE_COLLECTION_DIR = REPO_ROOT / ".github" / "control-plane" / "src"
CONTROL_PLANE_VALIDATOR = (
    REPO_ROOT / ".github" / "scripts" / "control_plane_validate.py"
)

MANIFEST_STATUS_VALUES = frozenset(
    {
        "active",
        "manual_only",
        "parked",
        "historical_unclear",
    }
)

FORBIDDEN_SECRET_PERSISTENCE_MARKERS = (
    "upload-artifact",
    "actions/cache/save",
    "persist_secret",
    "secrets.json",
)


@dataclass(frozen=True)
class LabelCascadeRow:
    filename: str
    triggers: tuple[str, ...]
    issues_types: tuple[str, ...]
    write_permissions: tuple[str, ...]
    uses_project_api: bool
    uses_repository_dispatch: bool
    has_noise_guard: bool


@dataclass(frozen=True)
class ScheduleEntry:
    filename: str
    crons: tuple[str, ...]
    has_workflow_dispatch: bool
    has_schedule: bool
    has_workflow_run: bool


@dataclass(frozen=True)
class SecurityWorkflowBoundary:
    filename: str
    triggers: tuple[str, ...]
    has_workflow_dispatch: bool
    has_schedule: bool
    write_permissions: tuple[str, ...]
    forbids_secret_artifact_upload: bool


def extract_issues_event_types(workflow: dict[str, Any]) -> tuple[str, ...]:
    on_section = workflow.get("on") or workflow.get(True)
    if not isinstance(on_section, dict):
        return ()
    issues_block = on_section.get("issues")
    if issues_block is None:
        return ()
    if isinstance(issues_block, dict):
        types = issues_block.get("types") or []
        return tuple(sorted(str(item) for item in types))
    if isinstance(issues_block, list):
        return tuple(sorted(str(item) for item in issues_block))
    return ()


def workflow_content_markers(path: Path, markers: tuple[str, ...]) -> bool:
    content = path.read_text(encoding="utf-8")
    return any(marker in content for marker in markers)


def workflow_uses_project_api(path: Path) -> bool:
    return workflow_content_markers(path, PROJECT_API_MARKERS)


def workflow_uses_repository_dispatch(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    return "createDispatchEvent" in content or "repository_dispatch" in content


def workflow_has_noise_guard(path: Path) -> bool:
    content = path.read_text(encoding="utf-8").lower()
    guard_tokens = (
        "concurrency:",
        "cancel-in-progress",
        "no-op",
        "skipping",
        "idempotent",
        "prune: false",
        "ambiguous",
        "if:",
        "startsWith(",
        "--retries",
    )
    return any(token in content for token in guard_tokens)


def build_label_cascade_row(workflow_path: Path) -> LabelCascadeRow:
    workflow = load_workflow_yaml(workflow_path)
    row = build_trigger_permission_row(workflow_path)
    return LabelCascadeRow(
        filename=workflow_path.name,
        triggers=row.triggers,
        issues_types=extract_issues_event_types(workflow),
        write_permissions=row.write_permissions,
        uses_project_api=workflow_uses_project_api(workflow_path),
        uses_repository_dispatch=workflow_uses_repository_dispatch(workflow_path),
        has_noise_guard=workflow_has_noise_guard(workflow_path),
    )


def build_label_cascade_map() -> dict[str, LabelCascadeRow]:
    return {
        filename: build_label_cascade_row(WORKFLOWS_DIR / filename)
        for filename in sorted(LABEL_CASCADE_WORKFLOW_FILES)
        if (WORKFLOWS_DIR / filename).is_file()
    }


def reusable_workflow_is_workflow_call_only(workflow_path: Path) -> bool:
    workflow = load_workflow_yaml(workflow_path)
    triggers = extract_on_triggers(workflow)
    automatic = triggers.intersection(AUTOMATIC_TRIGGERS)
    return triggers == {"workflow_call"} and not automatic


def extract_schedule_crons(workflow: dict[str, Any]) -> tuple[str, ...]:
    on_section = workflow.get("on") or workflow.get(True)
    if not isinstance(on_section, dict):
        return ()
    schedule_block = on_section.get("schedule")
    if schedule_block is None:
        return ()
    if not isinstance(schedule_block, list):
        return ()
    crons: list[str] = []
    for entry in schedule_block:
        if isinstance(entry, dict) and entry.get("cron"):
            crons.append(str(entry["cron"]).strip())
    return tuple(sorted(crons))


def build_schedule_entry(workflow_path: Path) -> ScheduleEntry:
    workflow = load_workflow_yaml(workflow_path)
    triggers = extract_on_triggers(workflow)
    return ScheduleEntry(
        filename=workflow_path.name,
        crons=extract_schedule_crons(workflow),
        has_workflow_dispatch="workflow_dispatch" in triggers,
        has_schedule="schedule" in triggers,
        has_workflow_run="workflow_run" in triggers,
    )


def build_p1_schedule_map() -> dict[str, ScheduleEntry]:
    entries: dict[str, ScheduleEntry] = {}
    for filename in sorted(P1_SCHEDULED_WORKFLOW_FILES):
        path = WORKFLOWS_DIR / filename
        if path.is_file():
            entries[filename] = build_schedule_entry(path)
    return entries


def find_cron_collisions(
    schedule_map: dict[str, ScheduleEntry],
) -> dict[str, tuple[str, ...]]:
    collisions: dict[str, list[str]] = {}
    for filename, entry in schedule_map.items():
        for cron in entry.crons:
            collisions.setdefault(cron, []).append(filename)
    return {
        cron: tuple(sorted(files))
        for cron, files in collisions.items()
        if len(files) > 1
    }


def build_security_boundary_row(workflow_path: Path) -> SecurityWorkflowBoundary:
    workflow = load_workflow_yaml(workflow_path)
    triggers = tuple(sorted(extract_on_triggers(workflow)))
    content = workflow_path.read_text(encoding="utf-8").lower()
    row = build_trigger_permission_row(workflow_path)
    forbids_upload = not any(
        marker in content for marker in FORBIDDEN_SECRET_PERSISTENCE_MARKERS
    )
    if workflow_path.name == "gitleaks.yml":
        forbids_upload = "upload-artifact" not in content
    if workflow_path.name == "security-scan.yml":
        forbids_upload = False
    return SecurityWorkflowBoundary(
        filename=workflow_path.name,
        triggers=triggers,
        has_workflow_dispatch="workflow_dispatch" in triggers,
        has_schedule="schedule" in triggers,
        write_permissions=row.write_permissions,
        forbids_secret_artifact_upload=forbids_upload,
    )


def list_manifest_unit_dirs(
    collection_dir: Path = CONTROL_PLANE_COLLECTION_DIR,
) -> list[Path]:
    if not collection_dir.exists():
        return []
    return sorted(
        path
        for path in collection_dir.iterdir()
        if path.is_dir() and (path / "manifest.yaml").is_file()
    )


def load_manifest_yaml(manifest_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be a mapping: {manifest_path}")
    return payload


def manifest_triggers_match_yaml(manifest: dict[str, Any], workflow_path: Path) -> bool:
    declared = {
        str(item).split(":")[0].strip()
        for item in (manifest.get("workflow") or {}).get("triggers") or []
    }
    workflow = load_workflow_yaml(workflow_path)
    actual = extract_on_triggers(workflow)
    return declared == actual


def manifest_permissions_match_yaml(
    manifest: dict[str, Any], workflow_path: Path
) -> bool:
    declared = (manifest.get("workflow") or {}).get("permissions") or {}
    if not isinstance(declared, dict):
        return False
    workflow = load_workflow_yaml(workflow_path)
    actual = extract_top_level_permissions(workflow)
    normalized_declared = {str(k): str(v) for k, v in declared.items()}
    return normalized_declared == actual


def control_plane_missing_unit_findings() -> tuple[str, ...]:
    cataloged: set[str] = set()
    for unit_dir in list_manifest_unit_dirs():
        manifest = load_manifest_yaml(unit_dir / "manifest.yaml")
        workflow_path = (manifest.get("workflow") or {}).get("path", "")
        if isinstance(workflow_path, str) and workflow_path.strip():
            cataloged.add(workflow_path.rsplit("/", 1)[-1])
    disk = set(list_workflow_yaml_files(WORKFLOWS_DIR))
    expected_catalog = {
        "cdb-control-followup-classifier.yml",
        "cdb-daily-delta-triage.yml",
        "cdb-post-merge-followup-scanner.yml",
    }
    missing = sorted(
        name for name in expected_catalog if name in disk and name not in cataloged
    )
    return tuple(missing)


# --- P2 scope (#3853–#3854) -------------------------------------------------

RUNBOOK_MD = REPO_ROOT / "docs" / "runbooks" / "GITHUB_CONTROL_PLANE_RUNBOOK.md"
GRAPH_MD = REPO_ROOT / "docs" / "runbooks" / "GITHUB_CONTROL_PLANE_GRAPH.md"
CONTROL_PLANE_ENTRYPOINT = REPO_ROOT / ".github" / "CONTROL_PLANE.md"
AGENT_WORKFLOW_MAP_JSON = (
    REPO_ROOT / ".github" / "control-plane" / "generated" / "agent-workflow-map.json"
)

# Post-#4540: required contexts are hosted GitHub Actions job names (ci/policy-gate),
# not a locally-published App Check Run.
REQUIRED_CHECK_PRODUCER_FILES: frozenset[str] = frozenset(
    {"ci.yml", "policy-gate.yml"}
)

RISKY_CASCADE_FAMILIES: dict[str, tuple[str, ...]] = {
    "label_event_cascade": tuple(sorted(LABEL_CASCADE_WORKFLOW_FILES)),
    "workflow_run_downstream": (
        "weekly_digest_failure_alert.yml",
        "auto-milestone-pr-apply.yml",
    ),
}

P2_DOCS_DRIFT_LIMITATIONS: tuple[str, ...] = (
    "Control-plane generated unit register is partial by design.",
    "Graph workflow references are relationship-focused, not a full inventory.",
    "Graph parser ignores issue-template and root-config backtick references.",
)

GRAPH_NON_WORKFLOW_REFERENCE_FILES = frozenset(
    {
        "cdb-control-followup.prompt.yml",
        ".github/prompts/cdb-control-followup.prompt.yml",
        "labels.json",
        "dependabot.yml",
        "emoji-config.yaml",
    }
)

KNOWN_DOCS_COUNT_DRIFTS: dict[str, tuple[int, str]] = {}


@dataclass(frozen=True)
class WorkflowDocsDriftFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class WorkflowDocsDriftScan:
    disk_count: int
    register_table_count: int
    register_header_count: int | None
    runbook_count_claim: int | None
    control_plane_entrypoint_count_claim: int | None
    graph_referenced_workflows: tuple[str, ...]
    graph_missing_on_disk: tuple[str, ...]
    limitations: tuple[str, ...]
    findings: tuple[WorkflowDocsDriftFinding, ...]


def parse_markdown_workflow_filenames(markdown_path: Path) -> set[str]:
    text = markdown_path.read_text(encoding="utf-8")
    return set(re.findall(r"`([^`]+\.(?:yml|yaml))`", text))


def parse_graph_workflow_inventory_references(graph_path: Path) -> set[str]:
    text = graph_path.read_text(encoding="utf-8")
    refs: set[str] = set()
    refs.update(re.findall(r"^\| `([^`]+\.(?:yml|yaml))` \|", text, flags=re.MULTILINE))
    refs.update(re.findall(r"\[[^\]]*?([a-zA-Z0-9_.-]+\.(?:yml|yaml))", text))
    for match in re.findall(r"\.github/workflows/([^\s`]+)", text):
        refs.add(match.rsplit("/", 1)[-1])
    return refs


def parse_runbook_workflow_count_claim(runbook_path: Path) -> int | None:
    text = runbook_path.read_text(encoding="utf-8")
    match = re.search(
        r"(\d+)\s+(?:workflow definitions|Workflow-Dateien)", text, flags=re.IGNORECASE
    )
    return int(match.group(1)) if match else None


def parse_control_plane_yaml_count_claim(entrypoint_path: Path) -> int | None:
    text = entrypoint_path.read_text(encoding="utf-8")
    match = re.search(
        r"(\d+)\s+(?:YAML workflow definitions|YAML-Dateien)", text, flags=re.IGNORECASE
    )
    return int(match.group(1)) if match else None


def parse_register_total_count_claim(register_path: Path) -> int | None:
    text = register_path.read_text(encoding="utf-8")
    match = re.search(
        r"\*\*(?:Total workflow definitions|Workflow-Dateien):\*\*\s*(\d+)", text
    )
    return int(match.group(1)) if match else None


def scan_workflow_docs_drift(
    *,
    workflows_dir: Path,
    register_md_path: Path,
    runbook_md_path: Path,
    graph_md_path: Path,
    control_plane_entrypoint_path: Path,
) -> WorkflowDocsDriftScan:
    disk = list_workflow_yaml_files(workflows_dir)
    disk_set = set(disk)
    register_table = parse_register_table_workflows(register_md_path)
    register_header = parse_register_total_count_claim(register_md_path)
    runbook_claim = parse_runbook_workflow_count_claim(runbook_md_path)
    entrypoint_claim = parse_control_plane_yaml_count_claim(
        control_plane_entrypoint_path
    )
    graph_refs = sorted(
        name
        for name in parse_graph_workflow_inventory_references(graph_md_path)
        if name not in GRAPH_NON_WORKFLOW_REFERENCE_FILES
    )
    graph_missing = tuple(sorted(set(graph_refs) - disk_set))

    findings: list[WorkflowDocsDriftFinding] = []
    if register_header is not None and register_header != len(disk):
        findings.append(
            WorkflowDocsDriftFinding(
                kind="register_header_count_drift",
                detail=(
                    f"Register header declares {register_header} workflows; "
                    f"disk has {len(disk)}"
                ),
            )
        )
    if runbook_claim is not None and runbook_claim != len(disk):
        findings.append(
            WorkflowDocsDriftFinding(
                kind="runbook_count_drift",
                detail=(
                    f"Runbook claims {runbook_claim} workflow definitions; "
                    f"disk has {len(disk)}"
                ),
            )
        )
    if entrypoint_claim is not None and entrypoint_claim != len(disk):
        findings.append(
            WorkflowDocsDriftFinding(
                kind="control_plane_entrypoint_count_drift",
                detail=(
                    f"CONTROL_PLANE.md claims {entrypoint_claim} YAML workflows; "
                    f"disk has {len(disk)}"
                ),
            )
        )
    graph_text = graph_md_path.read_text(encoding="utf-8")
    if re.search(r"\bfull\s+\d+-workflow register\b", graph_text, flags=re.IGNORECASE):
        findings.append(
            WorkflowDocsDriftFinding(
                kind="graph_stale_register_count_reference",
                detail=(
                    "Graph cross-link references a stale full-workflow-register count"
                ),
            )
        )
    for name in graph_missing:
        findings.append(
            WorkflowDocsDriftFinding(
                kind="graph_missing_on_disk",
                detail=f"{name} is referenced in graph docs but missing on disk",
            )
        )
    if len(register_table) != len(set(register_table)):
        findings.append(
            WorkflowDocsDriftFinding(
                kind="register_duplicate_rows",
                detail="Register table lists duplicate workflow filenames",
            )
        )

    return WorkflowDocsDriftScan(
        disk_count=len(disk),
        register_table_count=len(set(register_table)),
        register_header_count=register_header,
        runbook_count_claim=runbook_claim,
        control_plane_entrypoint_count_claim=entrypoint_claim,
        graph_referenced_workflows=tuple(graph_refs),
        graph_missing_on_disk=graph_missing,
        limitations=P2_DOCS_DRIFT_LIMITATIONS,
        findings=tuple(findings),
    )


def classify_workflow_operational_status(
    filename: str,
    *,
    workflows_dir: Path = WORKFLOWS_DIR,
    register_md_path: Path = WORKFLOW_REGISTER_MD,
) -> str:
    if filename in FROZEN_LEGACY_WORKFLOW_FILES:
        return "frozen"
    if filename in PARKED_WORKFLOW_FILES:
        return "parked"
    workflow_path = workflows_dir / filename
    if workflow_path.is_file() and reusable_workflow_is_workflow_call_only(
        workflow_path
    ):
        return "reusable"
    status_map = parse_register_status_map(register_md_path)
    register_status = status_map.get(filename, "")
    if "parked" in register_status:
        return "parked"
    if "manual" in register_status:
        return "manual_only"
    if "historisch" in register_status:
        return "frozen"
    if workflow_path.is_file() and workflow_has_only_dispatch_trigger(workflow_path):
        return "manual_only"
    return "active"


def classify_workflow_risk(
    filename: str,
    row: WorkflowTriggerPermissionRow,
    schedule_entry: ScheduleEntry,
) -> str:
    if row.forbidden_triggers:
        return "high"
    automatic = set(row.triggers).intersection(AUTOMATIC_TRIGGERS)
    if row.write_permissions and automatic:
        if (
            filename in LABEL_CASCADE_WORKFLOW_FILES
            or filename in ISSUES_LABELED_CASCADE_FILES
        ):
            return "high"
        return "medium"
    if schedule_entry.has_schedule and row.write_permissions:
        return "medium"
    if filename in RISKY_CASCADE_FAMILIES["workflow_run_downstream"]:
        return "medium"
    if row.write_permissions:
        return "medium"
    if schedule_entry.has_schedule:
        return "low"
    return "low"


def build_agent_workflow_map_entry(
    filename: str,
    *,
    workflows_dir: Path = WORKFLOWS_DIR,
    register_md_path: Path = WORKFLOW_REGISTER_MD,
) -> dict[str, Any]:
    workflow_path = workflows_dir / filename
    workflow = load_workflow_yaml(workflow_path)
    row = build_trigger_permission_row(workflow_path)
    schedule_entry = build_schedule_entry(workflow_path)
    register_set = set(parse_register_table_workflows(register_md_path))
    return {
        "file": filename,
        "name": str(workflow.get("name") or filename),
        "purpose": str(workflow.get("name") or filename),
        "triggers": list(row.triggers),
        "permissions": (
            list(row.write_permissions) if row.write_permissions else ["read-only"]
        ),
        "writes_github": bool(row.write_permissions),
        "has_schedule": schedule_entry.has_schedule,
        "status": classify_workflow_operational_status(
            filename, workflows_dir=workflows_dir, register_md_path=register_md_path
        ),
        "required_check_producer": filename in REQUIRED_CHECK_PRODUCER_FILES,
        "registered_in_markdown_register": filename in register_set,
        "risk": classify_workflow_risk(filename, row, schedule_entry),
    }


def build_full_schedule_collision_map(
    workflows_dir: Path = WORKFLOWS_DIR,
) -> dict[str, tuple[str, ...]]:
    schedule_map: dict[str, ScheduleEntry] = {}
    for filename in list_workflow_yaml_files(workflows_dir):
        path = workflows_dir / filename
        entry = build_schedule_entry(path)
        if entry.has_schedule:
            schedule_map[filename] = entry
    return find_cron_collisions(schedule_map)


def build_agent_workflow_map(
    *,
    workflows_dir: Path = WORKFLOWS_DIR,
    register_md_path: Path = WORKFLOW_REGISTER_MD,
) -> dict[str, Any]:
    disk = list_workflow_yaml_files(workflows_dir)
    register_set = set(parse_register_table_workflows(register_md_path))
    unregistered = sorted(set(disk) - register_set)
    entries = [
        build_agent_workflow_map_entry(
            filename, workflows_dir=workflows_dir, register_md_path=register_md_path
        )
        for filename in disk
    ]
    collisions = build_full_schedule_collision_map(workflows_dir)
    return {
        "schema_version": "1",
        "coverage": "complete",
        "catalog_scope": "workflow-inventory",
        "limitations": list(P2_DOCS_DRIFT_LIMITATIONS),
        "required_check_contexts": sorted(REQUIRED_CHECK_CONTEXTS),
        "unregistered_on_disk": unregistered,
        "risky_schedule_collisions": {
            cron: list(files) for cron, files in sorted(collisions.items())
        },
        "risky_cascade_families": {
            key: list(value) for key, value in RISKY_CASCADE_FAMILIES.items()
        },
        "entry_count": len(entries),
        "disk_workflow_count": len(disk),
        "register_table_count": len(register_set),
        "entries": entries,
    }
