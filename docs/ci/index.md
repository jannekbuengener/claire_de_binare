# CI Index

## Local Docker CI (Phase 1)

- Entry: [`ci/README.md`](../../ci/README.md)
- Front door (Windows): `pwsh -File ci/scripts/run_all.ps1`
- Make: `make ci-local` / `ci-local-stage` / `ci-local-report` / `ci-local-clean`
- Local evidence under `ci/artifacts/<run_id>/` is **not** a GitHub Required Check.
- Branch Protection and GitHub workflows remain unchanged in Phase 1.
- See [merge_policy_ci_gate.md](../runbooks/merge_policy_ci_gate.md) § Local Docker CI Phase 1.

## Local status publisher (optionaler Preflight; nicht länger Required)

- Doc: [`local-status-publisher.md`](local-status-publisher.md)
- Cutover runbook: [`cdb_local_ci_app_check_run_cutover.md`](../runbooks/cdb_local_ci_app_check_run_cutover.md)
- Entry: `python -m ci.publisher` / `pwsh -File ci/scripts/publish_status.ps1`
- Make: `ci-local-publish-dry-run` / `ci-local-publish` / `ci-local-publish-inspect`
- Publiziert optional den App Check Run `cdb-local-ci` (`app_id=4410232`)
  nach fail-closed evidence validation (`--publisher-backend check-run`).
- Seit #4540 ist `cdb-local-ci` **kein** Required Context; der lokale
  Preflight ist Diagnose/Entwicklungs-Ebene, kein Merge-Gate.
- Preferred preview/shadow context: `cdb-local-ci-app-preview`.

## Kanonischer PR-Merge-Vertrag

SSOT: [`merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md). Die
merge-relevanten Required Contexts auf `main` sind die hosted Check Runs
`ci (Unit/Integration + Lint gesammelt)` und `policy-gate` (exakter
PR-Head-SHA), live verifizierbar via `gh api` Check Runs — nicht via Commit
Status.

| Quelle | Check-Kontext | Typ |
|---|---|---|
| `ci.yml` (Job `ci`) | `ci (Unit/Integration + Lint gesammelt)` | Hosted Check Run (GitHub Actions) |
| `policy-gate.yml` (Job `policy-gate`) | `policy-gate` | Hosted Check Run (GitHub Actions) |

| Workflow | Rolle | Trigger |
|---|---|---|
| [`ci.yml`](../../.github/workflows/ci.yml) | Hosted Fast-CI, Required Check `ci (Unit/Integration + Lint gesammelt)` | gefilterter `push`, `pull_request` (main), `workflow_dispatch` |
| [`policy-gate.yml`](../../.github/workflows/policy-gate.yml) | Hosted lightweight PR policy gate, Required Check `policy-gate` | `pull_request` |

Seit #4540 sind `ci (Unit/Integration + Lint gesammelt)` und `policy-gate`
branch-protection-required; `cdb-local-ci` ist kein Required Context mehr.
Der optionale `cdb-local-ci`-Preflight ersetzt die hosted Required Checks
nicht. Ein rotes/blockiertes Hosted-Actions-Billing-/Runner-Lock ist eine
Infrastruktur-Bedingung, kein Code-Fehler, und darf nicht mit einem
fehlenden/roten hosted Required Check verwechselt werden.

## Ergänzende Prüfungen

| Bereich | Workflows |
|---|---|
| Verträge/Kompatibilität | `contracts.yml`, `python-compat.yml` |
| E2E | `e2e.yml`, `e2e-tests.yml`, `e2e-happy-path.yaml` |
| Security | `gitleaks.yml`, `trivy.yml`, `security-scan.yml`, `codeql-python.yml` |
| Guards | `repository-canon-guard.yml`, `docs-conflict-guard.yml`, `core-guard.yml` |
| Audit | `required-checks-audit.yml`, `governance-audit.yml` |

Diese Prüfungen können Fehler oder Findings liefern, sind aber keine
Ersatzquelle für die branch-protected hosted Required Checks.

## Einstieg bei Fehlern

1. Hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` und
   `policy-gate` live für den exakten PR-Head-SHA prüfen (`gh api`), nicht
   aus veralteten Tabellen ableiten.
2. Job- und Step-Logs des konkreten Runs (Hosted Actions) lesen.
3. [Merge-Policy-Runbook](../runbooks/merge_policy_ci_gate.md) anwenden.
4. Bei Inventar- oder Trigger-Drift das
   [Workflow-Register](../runbooks/GITHUB_WORKFLOW_REGISTER.md) prüfen.
