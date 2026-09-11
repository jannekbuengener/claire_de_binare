# CDB Skill Surface Registry

Status: kanonische Skill-Verwaltung (CDB only, kein Modusmono-Scope).
Single-Writer-Prinzip: jede Skill-Datei hat genau eine kanonische Quelle.

## 1. Executive Summary

CDB-Skills leben auf mehreren Agenten-Surfaces
(`.opencode/`, `.cursor/`, `.codex/`, `.claude/`, `docs/skills/`).
Ohne eine klare Registrierung entsteht Drift: identische Skills koennen
inhaltlich abweichen, die Source-of-Truth ist unklar, Agents wissen nicht,
wohin neue Skills gehoeren.

Dieses Dokument definiert:

- eine einzige kanonische Skill-Flaeche,
- alle aktiven und eingeschraenkten Surface-Adapter,
- die Pflicht-Header fuer jede Surface-Kopie,
- Drift-Regeln und Workflows (neu / update / deprecated).

Skopus ist **strikt CDB**. Modusmono-Repostrukturierung ist explizit
ausgeschlossen.

## 2. Warum eine Skill-Registry noetig ist

| Problem | Wirkung |
|---|---|
| Mehrere Surface-Pfade fuer dieselbe Datei | Drift zwischen den Kopien |
| Keine ausgewiesene Source of Truth | Agenten raten, wo sie schreiben sollen |
| Kein Sync-Status | Aenderungen werden nicht verifiziert |
| Kein Deprecation-Pfad | Veraltete Skills bleiben aktiv |
| Surface-READMEs koennen abweichen | Inkonsistente Skill-Listen |

PR #3569 (`cdb-github-api-ops`) hat diese Risiken sichtbar gemacht
und ist das erste Beispiel, fuer das diese Registry jetzt greift.

## 3. Kanonische Skill-Flaeche (Monopol)

`docs/skills/<skill-name>/SKILL.md` ist die kanonische Quelle.

Begruendung:

- `docs/` liegt versioniert im Repo und folgt der repository governance.
- `docs/skills/` enthaelt bereits erweiterte Skill-Dokumente
  (`gh-fix-ci/` mit `META.yaml`, `evals.json`, `DISCOVERY_REPORT.md`).
- `docs/` ist docs-only und nicht an einen Agent-Runtime-Loader gebunden,
  wodurch Schreibregeln klar bleiben.
- Diese Flaeche ist **Monopol im Sinne einer einzigen Source of Truth**:
  identische Skill-Dateien auf anderen Surfaces sind Adapter, nicht
  eigenstaendige Quellen.

Folgerung:

- Aenderungen am Skill-Inhalt passieren in `docs/skills/<name>/SKILL.md`.
- Surface-Adapter erhalten die Datei ueber den in Abschnitt 7 definierten
  Mirror-Workflow.

## 4. Aktive Skill-Surfaces

| Surface | Pfad | Rolle |
|---|---|---|
| Kanonisch | `docs/skills/<name>/SKILL.md` | Source of Truth (SSOT) |
| OpenCode | `.opencode/skills/<name>/SKILL.md` | Surface Adapter (mirrored) |
| Cursor | `.cursor/skills/<name>/SKILL.md` | Surface Adapter (mirrored) |
| Codex | `.codex/cdb_skills/<name>/SKILL.md` | Surface Adapter (mirrored) |
| Claude | `.claude/skills/<name>/SKILL.md` + `cdb-<name>.skill` Index | Surface Adapter (mirrored) |
| Docs (verweist) | `docs/skills/` Surface-README | Index/Quelle |

Alle aktiven Surfaces muessen dieselbe Skill-Datei spiegeln oder als
expliziter Adapter dokumentiert sein.

## 5. Eingeschraenkte / nicht-standardmaessige Surfaces

| Surface | Pfad | Status | Begruendung |
|---|---|---|---|
| Gemini | `.gemini/skills/` | Eingeschraenkt | Bewusst eingeschraenkter Surface-Set, Onboarding-only; nur 4 Skills deploybar (`cdb-external-docs`, `surrealdb-python`, `surrealdb-vector`, `surrealql`). Domain-Skills wie CDB-Workflow-Skills sind **nicht** auf Gemini-Surface vorgesehen. Aktivierungs-Policy: [`GEMINI_ACTIVATION_POLICY.md`](GEMINI_ACTIVATION_POLICY.md). |
| Skillforge assets | `.opencode/skills/skillforge/` | Tooling, nicht Skill | Skillforge ist Meta-Tool fuer Skill-Erstellung, kein Domain-Skill |
| Codex system | `.codex/cdb_skills/.system/` | Codex-spezifisch | Nur fuer Codex-Clients sichtbar |
| Archiv / Legacy | `docs/archive/...` | Read-only | Historische Referenz, kein aktiver Skill |

Regel: keine Skills auf `.gemini/` ohne explizite Surface-Entscheidung.
Details, Fail-Closed-Regeln und kuenftige Aktivierungs-Gates:
[`GEMINI_ACTIVATION_POLICY.md`](GEMINI_ACTIVATION_POLICY.md).

## 6. Surface-Adapter-Modell

Jede Surface-Kopie einer Skill-Datei ist ein **Adapter**.

Adapter-Typen:

| Typ | Bedeutung | Konsequenz |
|---|---|---|
| `mirrored` | Byte-faerbige Kopie der kanonischen Datei | Pflicht-Sync, kein abweichender Inhalt |
| `adapted` | Inhaltliche Variante mit Begruendung (z. B. Frontmatter-only) | Abweichung dokumentieren |
| `alias` | Verweist nur auf kanonische Datei | Minimaler Wrapper |
| `deprecated` | Veraltete Version, soll entfernt werden | EOL-Datum, Migrationshinweis |

Default-Typ fuer alle aktiven Skills: **`mirrored`**.

## 7. Referenzpflicht in jeder Surface-Kopie

Jede Surface-Kopie **muss** am Dateianfang folgenden Header-Traeger
enthalten (Markdown-Frontmatter oder erster Markdown-Block):

```text
<!--
Canonical Skill Source: docs/skills/<skill-name>/SKILL.md
Surface: <docs (canonical) | opencode | cursor | codex | claude>
Sync Status: <canonical | mirrored-from-canon | adapted | alias | deprecated>
Last Verified: <YYYY-MM-DD>
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
```

Kanonische Dateien verwenden `Surface: docs (canonical)` und
`Sync Status: canonical`. Aktive Adapter verwenden
`Sync Status: mirrored-from-canon` (Issue #3639, 2026-07-01).

Wird der Header weggelassen, gilt die Datei als **nicht-registriert**
und darf in der Surface-README nicht ohne Eintrag in dieser Registry
gelistet werden.

## 8. Drift Policy

- Surface-Adapter ohne Header = Drift-Verdacht, STOP-Review.
- Inhaltliche Abweichung nur wenn:
  - Adapter-Typ ist `adapted` oder `deprecated`
  - Begruendung in der kanonischen Datei dokumentiert
  - Cross-Reference in der Registry vorhanden
- `mirrored`-Adapter, die vom kanonischen Inhalt abweichen, sind kein
  gültiger Zustand und muessen sofort synchronisiert oder auf `adapted`
  umgestellt werden.
- Drift-Erkennung gehoert zum `cdb-drift-reconcile`-Workflow.

### 8.1 Skill Surface Mirror Drift Guard (Issue #3643, erweitert #4122)

Der Drift-Guard `tools/validate_skill_surface_mirror.py` prueft Canon-Body
gegen alle erwarteten Adapter (Header ignoriert), lokale Markdown-Links in
`SKILL.md`, Markdown-Anchors bei Fragmenten sowie Mirror-Paritaet fuer
skill-lokale Assets. Er ist read-only, macht keine Datei-, Netzwerk-,
GitHub-, DB- oder MCP-Aktionen.

```bash
python tools/validate_skill_surface_mirror.py          # human report
python tools/validate_skill_surface_mirror.py --json   # machine-readable
python tools/validate_skill_surface_mirror.py --skill <name>
```

- Exit codes: `0` = PASS, `1` = DRIFT_FOUND, `2` = BLOCKED.
- Prueft Body-Parity **und** den Pflicht-Header (`mirrored-from-canon` +
  korrekte Canon-Quelle je Adapter, siehe §7); ein Body-Match mit fehlendem
  Header ist Drift.
- Prueft zusaetzlich (#4122): relative lokale Linkziele (Datei/Verzeichnis),
  relevante fehlende Markdown-Anchors, Root-Escape ausserhalb des Repos,
  Mirror-Existenz und Inhaltsparitaet fuer skill-lokale referenzierte Assets.
- Fehlerklassen u. a.: `MISSING_LOCAL_TARGET`, `MISSING_MIRRORED_ASSET`,
  `ASSET_CONTENT_DRIFT`, `MISSING_ANCHOR`, `PATH_ESCAPES_REPO_ROOT`,
  `INVALID_ASSET_CLASS`, `INVALID_EXCEPTION` (mit Datei/Zeile wo sinnvoll).
- **Pflicht:** Nach jeder Aenderung an `docs/skills/<name>/SKILL.md` den
  Drift-Guard laufen lassen und Adapter nachziehen, bevor die Session als
  vollstaendig abgeschlossen gilt. Bei `DRIFT_FOUND` re-mirror im Scope oder
  dedupliziertes Re-Mirror-Follow-up-Issue anlegen (kein Auto-Merge ohne live
  hosted Required Checks (`ci (Unit/Integration + Lint gesammelt)`,
  `policy-gate`) im Scope; siehe `docs/runbooks/merge_policy_ci_gate.md`).
- Dokumentierte Ausnahmen (kein Drift): `cdb-onboarding` (codex-only Alias),
  `gh-fix-ci` Canon-Extras (`META.yaml`/`evals.json`/`scripts/`),
  `.claude/skills/*.skill`, `.gemini/skills/`.

### 8.2 Skill Asset Classes (Issue #4122)

Lokale Verweise aus `SKILL.md` werden einer Asset-Klasse zugeordnet:

| Klasse | Regel | Beispiele |
|---|---|---|
| `mirrored` | Relativ aus `SKILL.md` verlinkt und unter dem Skill-Verzeichnis aufgeloest → muss auf Canon **und** allen aktiven (nicht excludierten) Adaptern existieren; Inhalt nach Text-Normalisierung identisch | `references/*.md` |
| `canon_only` | Nur unter `docs/skills/<name>/`; Adapter spiegeln sie nicht; **keine** skill-lokalen relativen `SKILL.md`-Links darauf (stattdessen expliziter Canon-Pfad) | `META.yaml`, `evals.json`, `scripts/`, `DISCOVERY_REPORT.md` |
| `external` | `https:` / `http:` / `mailto:` — lokal nicht aufgeloest, kein Netzabruf | externe URLs |
| `excluded` | dokumentierte Surface-Ausnahme mit Reason | `cdb-onboarding` non-codex |

Regeln:

- Canon-first: Assets zuerst unter `docs/skills/<name>/` korrigieren, dann auf
  Adapter spiegeln (kein abweichender Mirror-Inhalt).
- Relative Links auf `canon_only`-Pfade sind ungueltig (`INVALID_ASSET_CLASS`),
  weil Body-Paritaet sonst tote Adapter-Links erzwingt.
- Links ausserhalb des Skill-Verzeichnisses, aber innerhalb des Repo-Roots,
  werden nur auf Existenz (und ggf. Anchor) je Quelldatei geprueft — keine
  Mirror-Pflicht.
- Leere Platzhalter nur zur Validator-Beruhigung sind verboten.

## 9. Skill-Neuanlage-Workflow

1. Skill-Inhalt in `docs/skills/<skill-name>/SKILL.md` anlegen.
2. Optional `META.yaml` und `evals.json` (nur fuer CDB, falls Pruefung noetig):
   Vertrag: [`SKILL_META_SCHEMA.md`](SKILL_META_SCHEMA.md);
   Starter: [`_templates/META.yaml`](_templates/META.yaml),
   [`_templates/evals.json`](_templates/evals.json).
   Meta-Artefakte und andere `canon_only`-Dateien bleiben im Canon.
   Relativ aus `SKILL.md` verlinkte skill-lokale Assets (z. B. `references/`)
   sind `mirrored` und muessen mitgespiegelt werden (Abschnitt 8.2).
3. Surface-Adapter-Header (Abschnitt 7) in der kanonischen Datei setzen.
4. Mirror auf alle aktiven Surfaces (Abschnitt 4): `SKILL.md` plus alle
   `mirrored` Assets.
5. `.claude/skills/cdb-<name>.skill` Index anlegen, falls Claude relevant.
6. Eintrag in `AGENTS.md` Skill-Tabelle (root pointer).
7. Eintrag in Surface-READMEs der aktiven Surfaces.
8. Drift-Check und `git diff --check`.

## 10. Skill-Update-Workflow

1. Aenderung in `docs/skills/<skill-name>/SKILL.md` (kanonisch).
2. `Last Verified` in allen Adaptern aktualisieren.
3. Falls Typ-Wechsel: Header in allen betroffenen Adaptern anpassen.
4. Adapter spiegeln (Copy + CRLF-Normalisierung auf Windows).
5. Surface-README-Eintraege nur anpassen, wenn Skill-Name oder Scope sich aendert.

## 11. Skill-Deprecation-Workflow

1. `Sync Status: deprecated` im Header aller Kopien setzen.
2. Eintrag in `docs/skills/<skill-name>/DEPRECATION.md` mit:
   - Deprecated date
   - Replacement (falls existent)
   - EOL date
3. Surface-Adapter bleiben bis EOL erhalten, danach entfernt.
4. Eintrag aus `AGENTS.md` Skill-Tabelle und Surface-READMEs takten.

## 12. Beispiel: `cdb-github-api-ops`

Eintrag in dieser Registry:

| Feld | Wert |
|---|---|
| Kanonische Datei | `docs/skills/cdb-github-api-ops/SKILL.md` |
| Eingefuehrt | PR #3569 |
| Surface-Adapter | opencode, cursor, codex, claude (alle `mirrored`) |
| `.gemini/`-Adapter | nicht aktiv |
| Drift-Status | nach erstem Mirror-Lauf konsistent |
| Cross-Refs | `docs/github/UNIFIED_GITHUB_STATUS_SNAPSHOT.md`, `gh-fix-ci`, `gh-address-comments`, `cdb-ci-cd-guard` |

Der Skill ist der erste offizielle Anwendungsfall dieser Registry. Er
dokumentiert das Routing-Muster fuer kuenftige Multi-Surface-Skills.

## 13. Zusammenhang zu PR #3569

PR #3569 hat `cdb-github-api-ops` als Multi-Surface-Skill eingefuehrt.
Dabei wurden die Surface-Kopien ohne explizite Source-Of-Truth-Doku
parallel angelegt. Diese Registry schliesst die Lucke:

- SSOT wird auf `docs/skills/` festgelegt
- Pflicht-Header auf den Spiegeldateien wird mit dieser Definition
  verbindlich
- Folge-Skills koennen sich an `cdb-github-api-ops` als Referenz
  orientieren

Folge-Issues koennen PR #3569 als Praezedenzfall referenzieren.

## 14. Externe / Plugin-Skills (Routing-SSOT, nicht mirrored)

Manche Skills leben **ausserhalb** des Repo-Mirror-Modells (z. B. Cursor Redis
Plugin, Gemini domain-expert). Fuer diese gilt:

| Dokument | Scope | Mirror |
|---|---|---|
| [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md) | Redis Core / Addon / Parking | **nein** — Routing-SSOT only |
| [`CDB.VERFUEGBARE.SKILLS_LISTE_2026-06-30.md`](CDB.VERFUEGBARE.SKILLS_LISTE_2026-06-30.md) | Verfuegbare Skills Index | **nein** — Index only |

Regeln:

- Externe Skills werden in `docs/skills/<routing-doc>.md` geroutet, nicht als
  `docs/skills/<name>/SKILL.md` gespiegelt, solange kein expliziter Mirror-Slice
  beschlossen ist.
- Redis Core Set: `redis-development`, `redis-core`, `redis-connections`,
  `redis-security`, `redis-observability` (Cursor Plugin).
- Redis Event/Runtime-Zusatz: `messaging-redis-streams`, `ctb-docker-stack`,
  `cdb-shadow-validation`.
- Parking-Lot (nicht Default): `redis-search`, `redis-semantic-cache`, RedisVL,
  LangCache, RQE-as-default, Vector Search als CDB-Brain-Ersatz.
- SurrealDB Context Intelligence bleibt Brain; Redis bleibt Runtime/Cache/Messaging.

## 15. Folge-Issues / naechste Slices

Nach Canon-Tree-Merge (2026-07-01):

- `[SKILLS] Mirror surface adapters from docs/skills canon` — **done** (Issue #3639; 25/25 canon, 99 adapter SKILL.md synced)
- `[SKILLS] Extend cdb-session-close with post-close follow-up issue intake` — **done** (Issue #3638)
- `[SKILLS] Extend cdb-session-close with Residual Work / Restunsicherheits-Intake` — **done** (PR #3645; merge afd98aa3)
- `[SKILLS] Apply Surface-Adapter-Header to all existing mirrored skills` — **done** (merged into #3639)
- `[SKILLS] Add drift-reconcile hook for skill surface adapters` — **done** (Issue #3643; `tools/validate_skill_surface_mirror.py` + tests, `cdb-drift-reconcile` §Skill Surface Mirror Drift)
- `[SKILLS] Add Skill-Meta Schema v1 (META.yaml + evals.json)` — **done** (Issue #3647; PR #3648; merge 6a6ef980)
- `[SKILLS] Document `.gemini/` activation policy if domain skills are ever needed` — **done** (Issue #3652; PR #3653; merge 52cd000)

Diese Issues werden dedupliziert und mit klarem Scope angelegt.

## 16. Aktives Skill-Inventar (2026-07-30)

Status nach Surface-Mirror-Slice (#3639), Drift-Guard (#3643), Debug-Skill-
Familie Slice 4 (`cdb-debug-handoff`), PR Router (#4202) und PR-Acceptance
Orchestrators (#4209/#4210) after Leaf-Primitives (#4207/#4208): **34/34**
Canon-Dateien; **133/133**
erwartete Adapter-`SKILL.md` mit `mirrored-from-canon` Header und body-parity zum
Canon-Body (minus Header). Verifiziert durch
`tools/validate_skill_surface_mirror.py` (`PASS`, 133 Adapter, 3 dokumentierte
`cdb-onboarding`-Ausnahmen). `docs/skills/` bleibt SSOT.

| Skill | Canon | opencode | cursor | codex | claude | Body-Drift |
|---|---|---|---|---|---|---|
| cdb-session-start | Y | sync | sync | sync | sync | — |
| cdb-pr-router | Y | sync | sync | sync | sync | — |
| cdb-integration-wiring-audit | Y | sync | sync | sync | sync | — |
| cdb-pr-gap-classifier | Y | sync | sync | sync | sync | — |
| cdb-pr-completeness-review | Y | sync | sync | sync | sync | — |
| cdb-batch-merge-conductor | Y | sync | sync | sync | sync | — |
| cdb-session-close | Y | sync | sync | sync | sync | — |
| cdb-control-intake | Y | sync | sync | sync | sync | — |
| cdb-issue-to-session-plan | Y | sync | sync | sync | sync | — |
| cdb-operator | Y | sync | sync | sync | sync | — |
| onboarding | Y | sync | sync | sync | sync | — |
| cdb-onboarding | Y | — | — | sync | — | alias; codex-only |
| cdb-test-first | Y | sync | sync | sync | sync | — |
| cdb-trading-core | Y | sync | sync | sync | sync | — |
| cdb-risk-governance | Y | sync | sync | sync | sync | — |
| cdb-exchange-adapters | Y | sync | sync | sync | sync | — |
| cdb-backtest-engine | Y | sync | sync | sync | sync | — |
| cdb-shadow-validation | Y | sync | sync | sync | sync | — |
| cdb-contract-evidence-gatekeeper | Y | sync | sync | sync | sync | — |
| cdb-drift-reconcile | Y | sync | sync | sync | sync | — |
| cdb-root-cause | Y | sync | sync | sync | sync | — |
| cdb-symptom-triage | Y | sync | sync | sync | sync | — |
| cdb-regression-gap | Y | sync | sync | sync | sync | — |
| cdb-debug-handoff | Y | sync | sync | sync | sync | — |
| cdb-docs-ops | Y | sync | sync | sync | sync | — |
| cdb-external-docs | Y | sync | sync | sync | sync | — |
| cdb-ci-cd-guard | Y | sync | sync | sync | sync | — |
| ctb-docker-stack | Y | sync | sync | sync | sync | — |
| gh-fix-ci | Y | sync | sync | sync | sync | canon-only: META.yaml, evals.json, scripts/, DISCOVERY_REPORT.md (Canon-Pfad-Link) |
| gh-address-comments | Y | sync | sync | sync | sync | — |
| cdb-github-api-ops | Y | sync | sync | sync | sync | — |
| surrealql | Y | sync | sync | sync | sync | — |
| surrealdb-vector | Y | sync | sync | sync | sync | — |
| surrealdb-python | Y | sync | sync | sync | sync | — |

**Bewusste Abweichungen (kein Body-Drift):**

| Skill | Abweichung | Begruendung |
|---|---|---|
| `cdb-onboarding` | Nur Codex-Adapter | Duenner Alias auf `onboarding`; andere Surfaces nutzen `onboarding` direkt |
| `gh-fix-ci` | Canon-Extras canon-only | `META.yaml`, `evals.json`, `scripts/`, `DISCOVERY_REPORT.md` bleiben `canon_only`; `SKILL.md` verlinkt den Discovery Report ueber den expliziten Canon-Pfad `../../../docs/skills/gh-fix-ci/DISCOVERY_REPORT.md` (#4122) |
| `cdb-contract-evidence-gatekeeper` | `references/` gespiegelt | Die drei Reference-Dateien sind `mirrored` Assets und muessen auf Canon und allen aktiven Adaptern liegen (#4122) |
| `.claude/skills/*.skill` | Nicht gespiegelt | Paket-/Aliasflaeche; out of scope #3639 |
| `.gemini/skills/` | Nicht gespiegelt | Eingeschraenkter Surface; kein CDB-Domain-Mirror |

**Nicht gezaehlt:** `skillforge` (Meta-Tool, gitignored), `mockexchange`
(kein SKILL.md), `codex-primary-runtime` (kein SKILL.md), Cursor Rules/Subagents,
Redis Plugin (routing-only), `.claude/skills/*.skill` (Alias).

**Mirror-Workflow:** Aenderungen starten in `docs/skills/<name>/SKILL.md`,
danach Adapter spiegeln (Header `mirrored-from-canon` + identischer Body) und
`python tools/validate_skill_surface_mirror.py` bis `PASS` laufen lassen
(siehe §8.1).

## Anti-Patterns

- Do NOT neue Skills direkt auf einer Surface ohne Eintrag in `docs/skills/`
- Do NOT Mirror-Kopien ohne Pflicht-Header aus Abschnitt 7
- Do NOT `adapted`-Typ verwenden, ohne Begruendung in der kanonischen Datei
- Do NOT `.gemini/` fuer CDB Domain-Skills ohne separate Surface-Entscheidung
- Do NOT Surface-READMEs divergieren lassen (immer synchron mit Registry)
- Do NOT Modusmono-Scope hier einziehen — dieses Dokument bleibt CDB-only
