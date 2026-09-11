# GitHub Workflow Register

**Repo:** Claire de Binare  
**Stand:** 2026-09-11 (#4540 hosted Required Checks)
**Workflow-Dateien:** 57  
**Entfernungs-Scope:** 13 Workflow-Dateien plus 5 exklusive Support-Dateien  
**Daten-Datei im Workflow-Ordner:** `labels.json` (kein Workflow)

Dieses Register bildet den aktuellen Bestand unter `.github/workflows/` ab. Die am
2026-07-16 entfernten Alt-, Stub- und unerreichbaren Workflows werden nur noch in
historischen Evidence- und Session-Unterlagen erwähnt.

## Status

| Status | Anzahl |
|---|---:|
| Aktiv | 48 |
| Manual-only | 9 |
| Parked / frozen / historisch | 0 |
| **Gesamt** | **57** |

## Merge-relevante Checks

SSOT: [`merge_policy_ci_gate.md`](merge_policy_ci_gate.md). Die merge-relevanten
Required Contexts auf `main` sind die hosted Check Runs `ci (Unit/Integration +
Lint gesammelt)` und `policy-gate`, live verifizierbar via `gh api`, nicht aus
dieser Tabelle.

| Quelle | Check-Kontext | Typ |
|---|---|---|
| `ci.yml` (Job `ci`) | `ci (Unit/Integration + Lint gesammelt)` | Hosted Check Run (GitHub Actions) |
| `policy-gate.yml` (Job `policy-gate`) | `policy-gate` | Hosted Check Run (GitHub Actions) |

| Workflow | Rolle |
|---|---|
| `ci.yml` | Hosted Actions, Required Check `ci (Unit/Integration + Lint gesammelt)`, `pull_request` (main), push, workflow_dispatch (#4540) |
| `policy-gate.yml` | Hosted Actions, Required Check `policy-gate` (PR Safety-Gate) |

Seit #4540 sind `ci (Unit/Integration + Lint gesammelt)` und `policy-gate`
Branch-Protection-Required-Checks. `cdb-local-ci` (Local CI Status Publisher,
App Check Run `app_id=4410232`) ist seit #4540 **kein** Required Context mehr,
sondern optionaler Developer-Preflight/Diagnose. Andere Workflows liefern
ergänzende Prüfungen, Reports oder Automatisierung, ersetzen aber die hosted
Required Checks nicht.

## Vollständiges Inventar

| Datei | Status | Trigger | Schreibrechte | Risiko |
|---|---|---|---|---|
| `add_to_project.yml` | aktiv | issues | read-only | low |
| `ai-review-router.yml` | aktiv | schedule, workflow_dispatch | pull-requests:write | medium |
| `auto-milestone-label-dispatch.yml` | aktiv | issues | contents:write | high |
| `auto-milestone-pr-apply.yml` | aktiv | workflow_run | issues:write | medium |
| `auto-milestone-pr-intent.yml` | aktiv | pull_request | read-only | low |
| `auto-milestone.yml` | aktiv | issues, repository_dispatch, workflow_dispatch | issues:write | high |
| `branch-policy.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `cdb-backlog-anomaly-escalation.yml` | aktiv | workflow_dispatch, workflow_run | issues:write | medium |
| `cdb-backlog-curation.yml` | aktiv | issues | issues:write | medium |
| `cdb-context-refresh-report.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `cdb-control-followup-classifier.yml` | manual-only | workflow_dispatch | issues:write | medium |
| `cdb-daily-delta-triage.yml` | aktiv | schedule, workflow_dispatch | issues:write | medium |
| `cdb-dependabot-autopilot.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `cdb-post-merge-followup-scanner.yml` | aktiv | pull_request, workflow_dispatch | issues:write | medium |
| `cdb-weekly-control-hygiene-classifier.yml` | aktiv | schedule, workflow_dispatch | issues:write | medium |
| `ci.yml` | aktiv | push, pull_request (main), workflow_dispatch | read-only | low |
| `codeql-python.yml` | aktiv | push, schedule, workflow_dispatch | read-only | low |
| `contracts.yml` | aktiv | push, schedule, workflow_dispatch | read-only | low |
| `control_board_upsert.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `copilot-housekeeping.yml` | aktiv | schedule, workflow_dispatch | issues:write, pull-requests:write | medium |
| `copilot-setup-steps.yml` | aktiv | push, workflow_dispatch | read-only | low |
| `core-guard.yml` | aktiv | push, schedule, workflow_dispatch | read-only | low |
| `delivery-gate.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `docker-publish.yml` | aktiv | push, workflow_dispatch | read-only | low |
| `docs-conflict-guard.yml` | aktiv | push, workflow_dispatch | read-only | low |
| `repository-canon-guard.yml` | aktiv | push, workflow_dispatch | read-only | low |
| `e2e-happy-path.yaml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `e2e-tests.yml` | aktiv | schedule, workflow_dispatch | issues:write | medium |
| `e2e.yml` | aktiv | push, schedule, workflow_dispatch | read-only | low |
| `emoji-bot.yml` | aktiv | issue_comment, workflow_dispatch | contents:write, issues:write | medium |
| `emoji-filter.yml` | manual-only | workflow_dispatch | contents:write, issues:write | medium |
| `gitleaks.yml` | aktiv | push, schedule, workflow_dispatch | read-only | low |
| `governance-audit.yml` | manual-only | workflow_dispatch | read-only | low |
| `label-bootstrap.yml` | manual-only | workflow_dispatch | issues:write, pull-requests:write | medium |
| `lr021_replay_smoke.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `mcp_runtime.yml` | manual-only | workflow_dispatch | read-only | low |
| `milestone_stage_label_sync.yml` | aktiv | issues | read-only | low |
| `opencode.yml` | aktiv | issue_comment, pull_request_review_comment | id-token:write | medium |
| `performance-monitor.yml` | manual-only | workflow_dispatch | read-only | low |
| `policy-gate.yml` | aktiv | pull_request | read-only | low |
| `project_reconcile_daily.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `project_status_label_map.yml` | aktiv | issues | read-only | low |
| `project_status_sync.yml` | aktiv | issues | read-only | low |
| `python-compat.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `required-checks-audit.yml` | manual-only | workflow_dispatch | read-only | low |
| `root-session-hygiene-warning.yml` | manual-only | workflow_dispatch | read-only | low |
| `security-alert-readout.yml` | aktiv | schedule, workflow_dispatch | issues:write, pull-requests:write | medium |
| `security-scan.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `shadow-soak-evidence.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `smart-insights.yml` | aktiv | schedule, workflow_dispatch | read-only | low |
| `stale.yml` | aktiv | schedule, workflow_dispatch | issues:write, pull-requests:write | medium |
| `surrealdb-memory-proof.yml` | manual-only | workflow_dispatch | read-only | low |
| `sync-labels.yml` | aktiv | push, workflow_dispatch | issues:write | high |
| `triage_guard.yml` | aktiv | issues | read-only | low |
| `trivy.yml` | aktiv | push, schedule, workflow_dispatch | read-only | low |
| `weekly_digest_failure_alert.yml` | aktiv | workflow_dispatch, workflow_run | issues:write | medium |
| `weekly_digest.yml` | aktiv | schedule, workflow_dispatch | read-only | low |

## Wartungsregeln

1. Neue oder entfernte Workflow-Dateien müssen in diesem Register und in
   `.github/control-plane/generated/agent-workflow-map.json` im selben PR
   nachgezogen werden.
2. Ein `workflow_call`-Workflow gilt nur dann als aktiv, wenn mindestens ein
   repo-interner Aufrufer dokumentiert und getestet ist.
3. Placeholder-, Diagnose- und Deprecation-Stubs werden nicht dauerhaft im
   Workflow-Ordner aufbewahrt.
4. Historische Evidence bleibt unverändert; operative Dokumente dürfen keine
   entfernten Workflows als aktuell darstellen.

## Verwandte Dokumente

- [Control-Plane-Einstieg](../../.github/CONTROL_PLANE.md)
- [Control-Plane-Runbook](GITHUB_CONTROL_PLANE_RUNBOOK.md)
- [Control-Plane-Graph](GITHUB_CONTROL_PLANE_GRAPH.md)
- [CI-Einstieg](../ci/index.md)
