<!--
Canonical Skill Source: docs/skills/cdb-test-first/SKILL.md
Surface: opencode
Sync Status: mirrored-from-canon
Last Verified: 2026-08-09
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-test-first
description: >
  CDB test-first planning rules. Load when the task involves testing, test
  planning, validation, evidence generation, or any significant implementation
  that needs test coverage. Teaches test-first thinking, test type selection,
  metadata contract, SurrealDB test knowledge model, and MockExchange pattern
  recognition.
---

# CDB Test-First Skill

## Purpose

Every CDB test is a **knowledge building block**, not just a code checker.
Before writing any test, clarify what it protects, what type fits, which
decision it strengthens, how it is structured, and how its result becomes
machine-usable knowledge later.

---

## Verbindlicher Implementierungsvertrag

Für jede wesentliche Implementierung gilt ohne Phasenübersprung:

```text
DOCS -> TESTS -> TEST FREEZE -> IMPLEMENTATION -> CHECKS
```

Der kanonische Vertrag ist
`knowledge/testing/TEST_FIRST_PROCESSING_CONTRACT.md` §2. Dieser Skill wendet
ihn zusätzlich zu den bestehenden Testarten, Metadaten und Wissensregeln an.

### PHASE 1: DOCS_GATE

Vor Produktivcode muss kanonische Doku das gewünschte Verhalten ausreichend
bestimmen: akzeptierter Contract, Feature-/System-Spec, Issue-Acceptance
Criteria, Policy, API-/Schema-Vertrag oder andere explizit kanonische
Repo-Doku.

Fehlt diese Doku, widerspricht sie sich oder bleiben Acceptance Criteria
unklar, gilt `IMPLEMENTATION_BLOCKED_DOCUMENTATION_REQUIRED`. Kein
Produktivcode darf beginnen.

### PHASE 2: TEST_GATE

Aus der feststehenden Doku werden vor Produktivcode die relevanten Tests
geschrieben. Sie prüfen gewünschtes Verhalten, wichtige Fehlerfälle,
geschützte Regeln und betroffene Contracts gegen die Anforderung, nicht gegen
die aktuelle Implementierung. Neue Tests dürfen vor der Implementierung rot
sein; bereits unterstütztes Verhalten darf grün sein.

Fehlen erforderliche Tests, gilt `IMPLEMENTATION_BLOCKED_TESTS_REQUIRED`.

### PHASE 3: TEST_FREEZE

Sobald Produktivimplementierung beginnt, sind die zuvor festgelegten Tests
eingefroren. Nicht erlaubt sind Assertion-Abschwächung, Sollwert-Anpassung an
fehlerhaften Code, Test-Löschung, Skip, `xfail`, manipulierte Testdaten,
reduzierte Acceptance Criteria, entfernte Grenzfälle oder eine Neuinterpretation
nur zum Grünwerden.

### PHASE 4: IMPLEMENTATION_GATE

Nach dem Freeze gilt: `FROZEN TEST ROT -> CODE PRUEFEN UND KORRIGIEREN`.
Prüfreihenfolge ist neue Implementierung, direkt betroffener bestehender
Produktivcode und danach ihre Integration. Erst dann darf eine Vertrags- oder
Testinkonsistenz untersucht werden.

Wenn Test und kanonische Doku nachweisbar widersprechen, die Doku sich selbst
widerspricht, der Test technisch Unmögliches fordert oder Acceptance Criteria
nachweisbar falsch sind, gilt
`IMPLEMENTATION_BLOCKED_CONTRACT_OR_TEST_CONFLICT`. Der Agent meldet Test,
Doku, Widerspruch und empfohlene Änderung, ändert aber keinen Frozen-Test und
keinen Canon ohne explizite Freigabe.

### PHASE 5: CHECKS_GATE

Nach der Implementierung folgen neue Fokus-Tests, relevante Regressionstests
und vorgeschriebene Repo-Checks. Nur ein vollständig grüner Lauf ergibt
`IMPLEMENTATION_GREEN`; ein roter Frozen-Test ergibt
`IMPLEMENTATION_FAILED_CODE_NEEDS_FIX` und führt zurück zur Implementierung.

**Brandherd-Regel:** Vor der Implementierung sind Doku und Tests fest. Während
der Implementierung ist Produktivcode die primäre bewegliche Variable. Bewege
nicht gleichzeitig Doku, Test und Code, nur um einen roten Test zu beseitigen.

---

## 1. Test-First Thinking (R1)

Before writing a test, answer these five questions:

| Frage | Beispiel |
|---|---|
| **Welche Regel wird geschützt?** | INV-011: Risk-before-Execution |
| **Welche Testart passt?** | Schutz-Test |
| **Welche Entscheidung wird sicherer?** | Kill-Switch stoppt Execution zuverlässig |
| **Welche Metadaten braucht der Test?** | test_id, test_type, cdb_area, rule_ref, decision_ref, issue_ref, pr_ref, evidence_ref, security_relevant, live_relevant, profitability_relevant |
| **Wie wird das Ergebnis weiterverarbeitet?** | PASS -> SurrealDB-Record + Evidence, FAIL -> Issue |

Canon: `knowledge/testing/TEST_FIRST_PROCESSING_CONTRACT.md` §3

---

## 2. Testart-Auswahl (R2)

Jeder Test gehört zu genau einer der 15 Testarten. Die Testart folgt aus der
geprüften Regel:

| # | Testart | Prüft | Wann wählen |
|---|---------|-------|-------------|
| 1 | **Bauteil-Test** | Einzelne Funktion/Klasse isoliert | Immer. Jeder neue Code zuerst. |
| 2 | **Ketten-Test** | Service-übergreifende Kommunikation | Feature durchläuft mehrere Services |
| 3 | **Schutz-Test** | Sicherheitsgrenzen (Kill-Switch, Exposure, Fail-Closed) | Risk-, Governance-, Execution-Änderung |
| 4 | **Wirtschafts-Test** | Geldflüsse (Fees, Slippage, PnL, Reservierungen) | Fee-Modell, PSM, Portfolio-Änderung |
| 5 | **Betriebs-Test** | Neustart, Recovery, Langlauf, Chaos | Recovery-Logik, neuer Service, Startup-Reihenfolge |
| 6 | **Wissens-Test** | Doku-Code-Konsistenz | Docs, Contracts, SERVICE_CATALOG-Änderung |
| 7 | **Property-based** | Invariante mit Zufallseingaben | State-Machine, Order-Lifecycle, math. Berechnung |
| 8 | **Fuzzing** | Kaputte/extreme Daten an Parser/Schnittstelle | Datenempfänger (WS, REST), Parser |
| 9 | **Mutation Testing** | Testqualität (Code mutieren, Test muss failen) | Wichtige Schutz-Tests absichern |
| 10 | **Metamorphic Testing** | Beziehung zwischen Eingabe/Ausgabe | Skalierung, Proportionen, Fee-Verdopplung |
| 11 | **API-Fuzzing** | Kaputte API-Requests -> fail-closed | Neuer API-Endpunkt |
| 12 | **Security-Test** | Auth-Lücken, Secrets im Log, Injection | Auth-Änderung, neuer Endpunkt, Secrets-Logik |
| 13 | **Supply-Chain-Test** | Dependency-Sicherheit, CVEs, Lizenzen | Neue Library, Security-Scan |
| 14 | **Datenbank-Test** | Migrationen, Queries, Schema | Neue Migration, Schema-Änderung |
| 15 | **Agenten-Wissens-Test** | Agenten-Kenntnis von CDB-Regeln | Neue Policy, STOP-Zone, Governance-Dokument |

Canon: `knowledge/testing/TEST_FIRST_PROCESSING_CONTRACT.md` §5

---

## 3. Test-Metadaten (R3)

Jeder wichtige CDB-Test trägt diese 15 Felder als Docstring-Kopf oder
YAML-Block:

| Feld | Typ | Beispiel |
|---|---|---|
| `test_id` | string | `tc_kill_switch_001` |
| `test_name` | string | `kill_switch_blocks_all_orders` |
| `test_type` | string | `schutz` |
| `cdb_area` | string | `risk` |
| `rule_ref` | string | `INV-011` |
| `decision_ref` | string | `Kill-Switch stoppt Execution zuverlässig` |
| `issue_ref` | string | `#1492` |
| `pr_ref` | string | `#1550` |
| `evidence_ref` | string | `docs/evidence/risk/kill_switch_proof_001.md` |
| `code_area` | string | `services/risk/` |
| `security_relevant` | bool | `true` |
| `live_relevant` | bool | `true` |
| `profitability_relevant` | bool | `false` |
| `surrealdb_export` | bool | `true` |
| `ci_artifact` | bool | `false` |

Canon: `knowledge/testing/TEST_FIRST_PROCESSING_CONTRACT.md` §4

---

## 4. SurrealDB-Testwissen (R4)

Tests sind Wissensbausteine. Agenten planen Tests mit diesen Beziehungen:

```
(test_case) --prueft--> (rule)
(test_case) --betrifft--> (cdb_area)
(test_case) --gehoert_zu--> (issue)
(test_case) --gelandet_in--> (pull_request)
(test_case) --erzeugt--> (evidence)
(evidence) --belegt--> (decision)
(skill_rule) --lehrt_regel--> (test_type)
```

Das Feld `surrealdb_export: true` markiert Tests für den späteren Export.

Canon: `knowledge/testing/TEST_FIRST_PROCESSING_CONTRACT.md` §6

---

## 5. MockExchange-Muster (R5)

MockExchange liefert Testmuster ohne Integration. Erkennbare Muster:

| Muster | CDB-Übersetzung |
|---|---|
| **State-Convergence** | Jede Order endet genau einmal in FILLED/REJECTED/FAILED/CANCELLED |
| **No false fill** | Rejected orders erzeugen Null-Fill, kein Executor-Aufruf |
| **Fee/Slippage realism** | Netto-PnL = Brutto-PnL - Fees - Slippage, getrennt ausweisbar |

Canon: `knowledge/testing/MOCKEXCHANGE_CDB_TEST_MAP.md` § Practical Meaning

---

## 6. When to load this skill

- Before writing any test for a new feature, issue, or slice
- Before planning validation scope (`cdb-shadow-validation` path)
- During session start (`cdb-session-start`) when the task has test scope
- When reviewing whether test evidence is complete for a PR or closure
- When designing tests that will later feed SurrealDB evidence

## External Documentation Lookup

Test-first planning references external testing and linting tools:
- Load `cdb-external-docs` before planning tests that depend on pytest, Ruff, mypy, or Black.
- Look up `docs/external-docs/index.md` → Python / CI / Dev-Qualität section.
- Read official test framework docs when designing test patterns.
- If no internet is available, use local code patterns as fallback and flag the gap.

## Canon sources

- `knowledge/testing/TEST_FIRST_PROCESSING_CONTRACT.md` — full contract (15 test types, metadata, SurrealDB model)
- `knowledge/testing/MOCKEXCHANGE_CDB_TEST_MAP.md` — MockExchange pattern translations
- `knowledge/testing/SKILL_VALLEY_TEST_UPGRADE_PLAN.md` — upgrade plan (R1-R8)
- `knowledge/testing/README.md` — testing knowledge index

## PR-Routing Test Profiles

Für Router- und Batch-Flow-Änderungen zuerst Schutztests formulieren:

- **Bauteil-Test:** pure Routing-, Lock-, Marker-, Ledger- und Trigger-Engine.
- **Agenten-Wissens-Test:** Router-before-branch und Slice-Close ohne Merge.
- **Wissens-Test:** Canon-, Registry- und Mirror-Parität.
- **Contract-Test:** Commit Status versus Check Run sowie `gh api` Publisher.

Jeder Test benennt, ob er `slice` oder `final_batch_head` schützt. Slice-Tests
dürfen keine vollständige Fast-CI oder hosted Required Checks voraussetzen; der
finale Merge-Head muss beide verlangen.
