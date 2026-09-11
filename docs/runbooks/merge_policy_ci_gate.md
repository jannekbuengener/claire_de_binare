# Merge Policy and CI Gate

## Delivery slices versus merge candidates

Ein normaler Issue-Slice wird in den durch `cdb-pr-router` bestimmten PR
geliefert. Targeted Tests, betroffener Lint/Format-Scope und
`git diff --check` reichen für den Slice-Handoff; Full Fast-CI, Merge und
Issue-Closure sind dabei `false`.

### Slice Validation vs Merge Acceptance (#4204)

| Oberfläche | Zweck | Merge-Evidence? |
|---|---|---|
| **Slice Validation** (`--profile slice` / `--slice`) | Deterministische, path-/lane-/profile-basierte Testgruppen für schnelle Entwicklungsprüfungen. Policy: `ci/config/slice_validation_policy.v1.yaml`. Report: `reports/slice_selection.json` mit `merge_evidence=false`. | **Nein** — Publisher lehnt `merge_evidence=false` und `profile=slice` ab. |
| **Final-Head / Fast-CI** (`--profile fast`) | Unveränderter vollständiger Unit-Selektor `pytest -q -k "not test_mcp_time_server_runtime"` plus lint/docs/governance. | Nur als published hosted Check Run auf exaktem Head über die `ci.yml`-Jobkette `ci (Unit/Integration + Lint gesammelt)` + `policy-gate` (siehe Branch Protection). |

Fail-closed: unbekannte/nicht klassifizierte Pfade, Policy-/Schema-/Parsefehler
oder Runtime-/Risk-/Docker-Pfade erzwingen automatisch das vollständige
Fast-CI-Unit-Profil. Marker dürfen ergänzend dokumentiert sein, sind aber
keine alleinige Auswahlgrundlage. Slice-Grün ersetzt niemals Final-Head-
Abdeckung.

Transport-`steward_state=merge_candidate` startet die Acceptance-Phase
`COMPLETENESS_REVIEW` (`cdb-pr-completeness-review`). Nur ein schema-valides
Completeness-Verdikt `MERGE_CANDIDATE` darf in die Conductor-Phase
(`cdb-batch-merge-conductor`: Freeze → Main-Integration → Final Validation →
`FINAL_HEAD_READY_FOR_APPROVAL`). Conductor mergt nicht. Danach folgen
HEAD-gebundenes APPROVE durch `cdb_final_head_pr_approval_gate` und regulärer
Merge durch `cdb_final_head_merge_executor`
(SSOT: `docs/contracts/final_head_merge_pipeline.v1.md`). Slice-Evidence darf
nie als Final-Head-Evidence wiederverwendet werden. Der finale Nachweis bindet
sowohl PR-Head als auch den integrierten Base-SHA. Head-/Base-Drift erzwingt
erneute Completeness Review und invalidiert Approval.

## Verbindlicher Vertrag

Für Pull Requests auf `main` gelten genau zwei merge-relevante Required
Contexts (Branch Protection, live via `gh api`):

| Quelle | Context | Typ |
|---|---|---|
| `ci.yml` (hosted Fast-CI, Job `ci`) | `ci (Unit/Integration + Lint gesammelt)` | GitHub-hosted Check Run (Actions) |
| `policy-gate.yml` (Job `policy-gate`) | `policy-gate` | GitHub-hosted Check Run (Actions) |

Seit #4540 ist `cdb-local-ci` **kein** Required Context mehr. Der lokale CI
Status Publisher und sein App-gebundener Check Run bleiben als optionaler
Developer-Preflight/Diagnose-Pfad bestehen, sind aber nicht
branch-protection-required und autorisieren keinen Merge. `ci.yml` startet
ab #4540 wieder auf jedem `pull_request` (Target `main`) und liefert den
Required Check `ci (Unit/Integration + Lint gesammelt)` auf exaktem Head.

Branch Protection (live, Zielbild #4540):

```powershell
gh api repos/<owner>/<repo>/branches/main/protection
```

erwartet `required_status_checks.strict: true` und
`required_status_checks.checks` mit den beiden hosted Checks
`ci (Unit/Integration + Lint gesammelt)` und `policy-gate`, **ohne** festes
`app_id` (Hosted GitHub Actions App, keine lokale App-Bindung).

Lint/Format (orchestrator stage `lint`, Issue #4206): Black und Ruff kommen
ausschließlich aus dem Pin in `requirements-dev.txt`. Black läuft als
`python -m black --check` auf dem Changed-File-Satz mit hartem Timeout
(Default 300s); Timeout und Toolauflösungsfehler sind Stage-`FAIL` mit Reason
Code, niemals Fake-Green. Details: `ci/README.md` § Black toolchain SSOT.

## Merge-Gates

Vor einem Merge müssen `ci (Unit/Integration + Lint gesammelt)` und
`policy-gate` für den aktuellen PR-Head-SHA erfolgreich gesetzt sein. Alte
grüne Runs auf anderen Heads, lokale Tests ohne Publish oder der optionale
`cdb-local-ci`-Check ersetzen diese Required Contexts nicht.

Der on-demand Workflow `required-checks-audit.yml` prüft die Konfiguration
und die live Check Runs, erzeugt selbst aber keinen merge-relevanten
Ersatzcheck.

## Sicherheitsmodell

- Untrusted Fork-Code darf nicht auf privilegierten self-hosted Runnern laufen.
- `pull_request_target` darf keinen untrusted Checkout ausführen
  (`policy-gate.yml` prüft das weiterhin).
- Code-Owner- und Review-Signale bleiben wichtig, auch wenn die aktuelle Branch
  Protection keine Mindestzahl genehmigender Reviews erzwingt.
- Der lokale Preflight-Publish (`cdb-local-ci`) erzwingt `--pr-number > 0` und
  den lokalen Policy-Gate-Mirror (`tools/ci/policy_gate_local.py`); er ist
  Diagnose-Evidence, kein Merge-Gate.

## Diagnose

1. PR-Head-SHA ermitteln.
2. Hosted Check Runs für exakt diesen SHA prüfen
   (`gh api repos/.../commits/<sha>/check-runs`): `ci (Unit/Integration +
   Lint gesammelt)` und `policy-gate` beide `completed`/`success` (bzw. von
   `required-checks-audit.yml` verifiziert).
3. Fehlenden Check Run von einem fehlgeschlagenen Check Run unterscheiden.
4. Publisher-Evidence und Policy-Gate-Fail prüfen, falls zusätzlich der
   optionale `cdb-local-ci`-Preflight laufen soll.
5. Erst nach erfolgreichen aktuellen hosted Required Checks mergen.

## Final-Head Approval and Merge Pipeline

There is exactly one canonical final merge executor:
`cdb_final_head_merge_executor` (Cursor display: Merge Agent).
Capability alone does **not** authorize any session to bypass
PR Reviewer → Merge Agent.

Required sequence after Completeness `MERGE_CANDIDATE`:

1. `cdb-batch-merge-conductor` prepares Final Head (freeze, integrate main,
   Full Fast-CI) and stops at `FINAL_HEAD_READY_FOR_APPROVAL`. Hosted
   Required Checks (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`)
   müssen auf dem finalen Head grün sein.
2. `cdb_final_head_pr_approval_gate` (PR Reviewer) issues GitHub APPROVE
   bound to the exact final `HEAD_SHA` (Risk LOW, no blockers). Cannot merge.
3. `cdb_final_head_merge_executor` re-verifies approval HEAD binding, drift,
   required Checks, reviews, and mergeability, then runs
   `gh pr merge <PR> --squash --delete-branch`. Cannot approve. Never `--admin`.
4. `cdb-session-close` verifies live MERGED and closes only eligible
   `SLICE_DELIVERED` issues.

Cloud Reviewer/Merger are repo-only; they consume hosted Check Run evidence
and must not require local `cdb_context` or fabricate CI.

`--admin` is **never** a bypass for missing/red/stale required checks.
Fake-green claims and merging an untested head are forbidden.

### Honest handoff when Final-Head readiness is missing

If Conductor cannot verify the hosted required Checks or Final-Head gates
fail: leave the PR open, do not use `--admin`, do not loop the same blocked
attempt, and report `DONE_PR_OPEN_MERGE_HANDOFF` with the exact missing
capability. See `.cursor/rules/CDB-Checks-and-Merge-Rule.mdc` for the status
taxonomy (`DONE_MERGED_CLOSED`, `DONE_PR_OPEN_MERGE_HANDOFF`,
`BLOCKED_REQUIRED_STATUS`, `BLOCKED_AUTH_PUBLISHER`, `HOLD_SCOPE_OR_REVIEW`,
`HOLD_MAIN_OR_HEAD_DRIFT`).

### Auth token override for the publisher

The optional local publisher (`ci.publisher`, see
[`local-status-publisher.md`](../ci/local-status-publisher.md)) reads its
token only from the environment, in this order: `GITHUB_TOKEN`, then
`GH_TOKEN`, else falling back to `gh auth token`. A fine-grained PAT with
**Commit statuses: Write** is sufficient; no admin, branch-protection, or
contents-write scope is required or should be granted for publishing.
Never pass a token as a CLI argument or commit it to the repo.

### Merge waves

When merging multiple PRs in sequence: after each squash merge, rebase the
next PR onto the updated `main` and fully revalidate — rerun local Fast-CI
and confirm the hosted Required Checks (`ci (Unit/Integration + Lint
gesammelt)`, `policy-gate`) are green on the new head — before merging the
next PR in the wave. Do not batch-merge later PRs on evidence collected
before the wave started; treat `main` movement mid-wave as
`HOLD_MAIN_OR_HEAD_DRIFT` until revalidated.

### Anti-repush

After `gh pr merge --squash --delete-branch`, do not automatically re-push,
recreate, or resurrect the deleted remote branch. If follow-up work is
needed on the same topic, open a new branch explicitly instead of reviving
the merged/deleted one.

## Dokumentationspflicht

Änderungen an Check-Namen, Triggern oder Branch Protection müssen gemeinsam in
`docs/ci/index.md`, diesem Runbook, dem Workflow-Register und den
Required-Check-Contract-Tests aktualisiert werden.

## Local CI + Status Publisher (optionale Preflight-Ebene)

Lokale CI unter `ci/` (siehe [`ci/README.md`](../../ci/README.md)) und
Publisher (siehe [`docs/ci/local-status-publisher.md`](../ci/local-status-publisher.md)):

- Lokale Evidence allein autorisiert keinen Merge; merge-relevant sind nur
  die hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` und
  `policy-gate`.
- Der App-gebundene `cdb-local-ci`-Check Run ist optionaler
  Developer-Preflight/Diagnose und nicht branch-protection-required.
- Branch Protection (Zielbild): contexts `ci (Unit/Integration + Lint
  gesammelt)` + `policy-gate`, `checks[]` ohne festes `app_id`, `strict: true`.
- Dirty worktree ⇒ lokale Evidence `BLOCKED` und kein Preflight-Publish.
- Publish-Pfad erzwingt Policy-Gate-Mirror (Parität zu
  `.github/workflows/policy-gate.yml`).
- Kein Fake-Green: dirty, stale, SHA-Mismatch, Hash-Mismatch, required SKIPPED,
  Anti-Replay, fehlende PR-Nummer oder Policy-Gate-Fails blockieren Publish.
- Lokales CodeQL/SARIF ersetzt nicht den GitHub Security-Tab.

Live Branch-Protection-Hinweis (reverify with `gh api`):
`required_status_checks.checks` = beide hosted Contexts, `strict: true`,
kein `app_id` gesetzt.

Windows front door (lokale Preflight-Ebene):

```powershell
pwsh -File ci/scripts/run_all.ps1 -Profile fast
python -m ci.publisher publish `
  --publisher-backend check-run `
  --evidence-dir ci/artifacts/<run_id> `
  --commit-sha <exact_pr_head> `
  --pr-number <n>
```