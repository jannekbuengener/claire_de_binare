---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md
  downstream:
    - agents/AGENTS.md
    - docs/skills/cdb-pr-router/SKILL.md
    - tools/agent_control/
  status: canonical
  tags: [agents, control-plane, authority, lifecycle, evidence]
---

# CDB Agent Control Plane

Status: Canonical  
Version: `cdb-agent-control-plane/v1`  
Issue: `#4250`  
Parent: `#4249`  
Authority class: Architecture and governance contract (docs/canon)

## Owner Ratification Record

| Field | Value |
| --- | --- |
| Owner | Jannek Büngener |
| Decision | `RATIFY` |
| Declared | `Ratifizieren` |
| Decided at | 2026-08-01 (Europe/Berlin) |
| Ratified artifact | `knowledge/governance/CDB_AGENT_CONTROL_PLANE.md` |
| Ratified version commit | `c691a8d0469924cf233fd72965bb77b7f98bb9db` |
| Effect | The corrected authority-order / demotion-safe Fassung at that commit is ratified as the binding CDB Agent Control Plane Canon. |
| Limits | No merge authority; no `cdb-local-ci` publish; no Live/Echtgeld-Go; no weakening of existing governance; no automatic ratification of later material changes |

Later **material** changes to this document require a fresh Owner ratification
(`HOLD_OWNER_RE_RATIFICATION_REQUIRED`). Purely editorial, non-normative
pointer/status sync after this record is allowed.

## 1. Zweck, Scope und Nicht-Ziele

### 1.1 Zweck

Die **CDB Agent Control Plane (ACP)** ist der provider-neutrale Steuerrahmen
für governed Agentenläufe im Claire-de-Binare-Repository. CDB bleibt die
Autorität für Routing, Contracts, Gates und Merge. Ausführungsprovider
(zuerst Cursor) führen zugewiesene Arbeit aus, autorisieren aber weder Merge
noch Live-Trading.

### 1.2 Scope dieses Canon-Dokuments

Dieses Dokument definiert:

- Architektur und Systemgrenzen der ACP
- Authority Matrix je Komponente
- Governed Run Lifecycle inkl. terminaler Semantik
- Evidence-Grenzen (Brain vs. Agent Run vs. Targeted Slice vs. Final CI)
- Zero-Click-/Bootstrap-Regeln und Capability-Drift
- Lineage zu bestehenden Routing-, Delivery-/Merge- und Final-CI-Verträgen

### 1.3 Nicht-Ziele (verbindlich)

- Kein Dispatcher-, Registry- oder Provider-Adapter-Code in diesem Canon-Dokument
  (Follow-ups `#4252`–`#4257`; Execution-Contract-Schema liegt in `#4251` /
  `cdb.agent_execution.v1`, nicht hier)
- Kein Ersatz und keine Umbenennung der **GitHub Workflow Control Plane**
  (`.github/CONTROL_PLANE.md`, `#1640`/`#1644`-Lineage)
- Kein neuer Merge-Prozess und kein Bypass der hosted Required Checks
  (`ci (Unit/Integration + Lint gesammelt)` + `policy-gate`)
- Kein Live-/Echtgeld-GO; LR bleibt `NO-GO`; Board-Stage `trade-capable` ist
  kein Live-Go
- Keine Runtime-, Trading-, Risk-, Execution-, produktive DB- oder MCP-Mutation
- Keine privaten Cursor-APIs und kein UI-Scraping als Kernpfad
- Keine Secrets im Klartext in Docs, Issues, Prompts oder Evidence

## 2. Abgrenzung: Agent Control Plane ≠ GitHub Workflow Control Plane

| Fläche | Autorität | Zweck |
| --- | --- | --- |
| **Agent Control Plane** (dieses Dokument) | CDB Governance + Agenten-Skills/Tools | Issue → Route → Contract → Dispatch → Provider-Run → Review → Delivery/Merge-Handoff |
| **GitHub Workflow Control Plane** | `.github/` Automation | CI/Security/Repo-Automation, Workflow-Register, Manifeste, Seal |

Die GitHub Workflow Control Plane bleibt unverändert unter:

- [`.github/CONTROL_PLANE.md`](../../.github/CONTROL_PLANE.md)
- [`docs/governance/GITHUB_CONTROL_PLANE_SEAL.md`](../../docs/governance/GITHUB_CONTROL_PLANE_SEAL.md)
- [`docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md`](../../docs/runbooks/GITHUB_CONTROL_PLANE_GRAPH.md)
- [`docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md`](../../docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md)

Historische Issues `#1640`/`#1644` beschreiben ausschließlich diese Workflow-
Fläche. Sie dürfen weder umbenannt, ersetzt noch mit der ACP vermischt werden.

## 3. Provider-neutrale Architektur

```text
Issue / Human-GO
    │
    ▼
CDB Governance (Policy, Write-Gates, LR/Safety)
    │
    ▼
PR Router (read-only route) ──► existing/new PR lane
    │
    ▼
Agent Execution Contract (handoff payload; schema in #4251)
    │
    ▼
Dispatcher (state machine; #4253) ──► Provider Adapter (#4254+)
    │                                      │
    │                                      ▼
    │                               Cursor (first provider)
    │                                      │
    ▼                                      ▼
Agent Run Evidence ◄────────────── Approval Agent (review only)
    │
    ▼
Delivery Slice in routed PR
    │
    ▼  (separate Merge session)
Completeness Review → Batch Merge Conductor (Final-Head prep) →
hosted Required Checks (`ci` + `policy-gate`) → PR Reviewer APPROVE → Merge Agent → session-close
```

Regeln:

1. **Provider-neutral:** ACP-Verträge sprechen von Provider-Adapter und
   Environments, nicht von Cursor-Dashboard-Klicks.
2. **Cursor first:** Cursor ist der erste Ausführungsprovider; weitere Provider
   dürfen folgen, ohne Authority Matrix oder Lifecycle zu ändern.
3. **Delivery ≠ Merge:** Normale Issue-Sessions enden mit
   `DONE_SLICE_ADDED_TO_BATCH_PR`. Merge bleibt eine getrennte Session unter
   [`docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md`](../../docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md).
4. **Fail-closed:** Fehlender Contract, unsichere Route, ungeeignet Environment
   oder fehlende Evidence stoppt den Lauf; kein implizites Weiterlaufen.

## 4. Authority Matrix

Für jede Komponente gilt genau eine primäre Verantwortung. Spalten:

- **Entscheidet** — setzt verbindliche Auswahl/Policy
- **Darf ausführen** — mutierende oder startende Aktion
- **Darf prüfen** — read-only Bewertung / Gate-Evidence
- **Darf stoppen** — HOLD/BLOCKED/CANCEL auslösen
- **Darf ausdrücklich nicht autorisieren** — harte Negativliste

| Komponente | Entscheidet | Darf ausführen | Darf prüfen | Darf stoppen | Darf ausdrücklich nicht autorisieren |
| --- | --- | --- | --- | --- | --- |
| **CDB Governance** | Policy, Write-Gates, Safety/LR-Grenzen, Canon | Canon-/Policy-Writes nur mit Human-GO und Session-Gates | Governance-Drift, Policy-Verletzungen | STOP bei Safety-/Canon-Verletzung | Live-Go, Echtgeld, produktive DB/MCP-Writes ohne eigenen Gate |
| **PR Router** | Ziel-PR / Branch / Lane / Validation Profile | nichts (read-only) | Kompatibilität, Locks, Inventar | `HOLD_*` bei unsicherer Route | Branch/Worktree/PR-Erstellung, Merge, Status-Publish |
| **Agent Execution Contract** | Handoff-Inhalt und Pflichtfelder (`cdb.agent_execution.v1`, `#4251`) | nichts | Contract-Vollständigkeit gegen Schema | Fail-closed bei fehlendem/ungültigem Contract | Merge, Live-Go, Provider-Start ohne Dispatcher |
| **Dispatcher** | Run-Start und erlaubte Lifecycle-Übergänge | Provider-Dispatch gemäß Contract + Route + Environment | Preflight (Contract/Route/Env) | HOLD/BLOCKED/FAILED bei Preflight- oder Lauf-Fehler | Merge, Approval ersetzen, Final-CI vortäuschen |
| **Provider Adapter** | Provider-spezifische Aufrufabbildung | Provider-API/CLI/SDK laut öffentlicher Capability | Capability Probe / Drift gegen Registry | STOP wenn Capability fehlt oder Drift kritisch | Private API / UI-Scraping als Kern; Merge; Secrets speichern |
| **Cursor** | nichts in CDB-Authority | Zugewiesene Delivery-Arbeit im Provider-Environment | Provider-lokale Logs/Status an Adapter | Provider-seitiger Abbruch melden | Merge, `cdb-local-ci`, Issue-Close, Live-Go, Governance-Override |
| **PR Reviewer (`cdb_final_head_pr_approval_gate`)** | GitHub APPROVE gebunden an exakten Final-Head SHA | APPROVE-Review gemäß Final-Head Pipeline | Diff/Evidence/hosted Required Checks gegen Contract und Safety | HOLD bei Policy-/Safety-/Drift-Findings | Merge, Code ändern, Final-CI publishen, Branch Protection, Live-Go |
| **Agent Run Evidence** | nichts | Evidence-Bundle schreiben (Schema später `#4256`) | Vollständigkeit/Integrität des Run-Bundles | BLOCKED bei fehlender Pflicht-Evidence | Brain-Evidence ersetzen; Final-CI vortäuschen; Merge |
| **Final CI / hosted Required Checks** | Merge-relevante Check-Run-Wahrheit: `ci (Unit/Integration + Lint gesammelt)` + `policy-gate` (GitHub-hosted, exakter Head); SSOT [`docs/runbooks/merge_policy_ci_gate.md`](../../docs/runbooks/merge_policy_ci_gate.md) | Publish nur durch `ci.yml`/`policy-gate.yml` (Hosted GitHub Actions) | Fast-CI/Evidence-Bindung an Head SHA | BLOCKED_REQUIRED_STATUS bei missing/red/stale | Slice-Validation als Final-CI zählen; Admin-Bypass; lokalen `cdb-local-ci` Preflight als Merge-Gate zählen |
| **Completeness Review** | `MERGE_CANDIDATE` / Nicht-Kandidat (read-only Aggregat) | nichts | Acht Dimensionen der PR-Completeness | HOLD bei Lücken/Scope-/Wiring-Findings | Merge ausführen; Delivery-Session ersetzen |
| **Batch Merge Conductor** | Freeze, Final-Validation-Orchestrierung, `FINAL_HEAD_READY_FOR_APPROVAL` | Freeze, Rebase/Integrate nach Canon, hosted Required Checks verifizieren | Final-Head-Evidence, Main-Drift | HOLD bei Drift/Capability-/Gate-Fehlern | APPROVE; Merge; Delivery-Slice mergen ohne Freeze; `--admin`; Fake-Green |
| **Merge Agent (`cdb_final_head_merge_executor`)** | Regular Merge nach HEAD-gebundenem APPROVE | `gh pr merge --squash --delete-branch` nach Re-Verify | Approval-HEAD, Drift, required Check Run, Mergeability | HOLD/Re-Review bei Drift/stale Approval | APPROVE; Code ändern; `--admin`; Fake-Green |

### 4.1 Kurzform Authority

- **CDB entscheidet.** Router weist zu. Contract beschreibt. Dispatcher startet.
  Provider führt aus. Completeness bewertet Merge-Reife. Conductor bereitet
  Final Head vor. PR Reviewer APPROVEd den exakten Head. Merge Agent mergt.
- **PR Reviewer APPROVE ≠ Mergefreigabe durch Conductor/Delivery.**
- **Delivery-Agenten und Conductor dürfen nicht mergen.** Nur
  `cdb_final_head_merge_executor` mergt.
- **Hosted Required Checks `ci (Unit/Integration + Lint gesammelt)` + `policy-gate`
  bleiben die merge-relevanten Required Contexts**
  (SSOT: [`docs/runbooks/merge_policy_ci_gate.md`](../../docs/runbooks/merge_policy_ci_gate.md)).

## 5. Governed Run Lifecycle

### 5.1 Zustände

| Zustand | Bedeutung |
| --- | --- |
| `PLANNED` | Issue + Human-/Plan-GO vorhanden; noch keine Route gebunden |
| `ROUTED` | PR Router hat sichere Entscheidung geliefert |
| `CONTRACTED` | Execution Contract erfüllt Pflichtfelder |
| `DISPATCHED` | Dispatcher hat Provider-Lauf gestartet |
| `RUNNING` | Provider führt Arbeit aus |
| `AWAITING_APPROVAL` | Review angefordert; Merge noch nicht im Scope |
| `DELIVERED` | Slice im gerouteten PR; Delivery-Session endet |
| `PASS` | Terminal: Delivery-Ziele des Runs erfüllt (nicht gleich Merge) |
| `HOLD` | Terminal/pausierend: wartbar, menschliche/Route-Klärung nötig |
| `BLOCKED` | Terminal: Gate/Capability/Safety blockiert Fortschritt |
| `FAILED` | Terminal: Lauffehler nach Start |
| `CANCELLED` | Terminal: explizit abgebrochen |

### 5.2 Erlaubte Übergänge

```text
PLANNED → ROUTED | HOLD | BLOCKED | CANCELLED
ROUTED → CONTRACTED | HOLD | BLOCKED | CANCELLED
CONTRACTED → DISPATCHED | HOLD | BLOCKED | CANCELLED
DISPATCHED → RUNNING | FAILED | CANCELLED
RUNNING → AWAITING_APPROVAL | DELIVERED | FAILED | HOLD | BLOCKED | CANCELLED
AWAITING_APPROVAL → DELIVERED | HOLD | BLOCKED | CANCELLED
DELIVERED → PASS | HOLD
```

Merge-Pfad (separate Session, nicht Teil des Delivery-Runs):

```text
DELIVERED/PASS (open PR) → Completeness MERGE_CANDIDATE → FROZEN
  → Final CI SUCCESS on exact head → FINAL_HEAD_READY_FOR_APPROVAL
  → PR Reviewer APPROVE(HEAD_SHA) → Merge Agent regular squash-merge
  → session-close
```

Ein Delivery-Run darf Completeness/Conductor/Final-CI **referenzieren**, aber
nicht als eigene Autorität starten oder ersetzen.

### 5.3 Terminale Semantik

| Terminal | Semantik |
| --- | --- |
| `PASS` | Governed Delivery-Ziele erreicht; PR/Issue typischerweise noch offen |
| `HOLD` | Fortschritt bewusst gestoppt; Ursache dokumentiert; Retry nach Klärung möglich |
| `BLOCKED` | Gate/Capability/Safety verhindert Fortschritt ohne Scope-/Gate-Änderung |
| `FAILED` | Lauf nach Start fehlgeschlagen; Evidence muss Fehler zeigen |
| `CANCELLED` | Expliziter Abbruch; kein stilles Weiterlaufen |

### 5.4 Fail-closed Pflichtfälle

Sofort `HOLD` oder `BLOCKED` (nie stilles Weiterlaufen), wenn:

- Execution Contract fehlt oder ungültig ist
- PR Router `HOLD_*` oder unsichere Route liefert
- Environment-/Capability-Preflight fehlschlägt
- Pflicht-Evidence fehlt oder Evidence-Arten vermischt/vorgetäuscht werden
- Scope in Runtime/Risk/Live/Secrets driftet
- Private Cursor-Endpunkte oder UI-Scraping als Kernpfad nötig wären

## 6. Evidence-Grenzen

Diese Evidence-Arten sind strikt getrennt. Keine darf die andere vortäuschen.

| Evidence-Art | Was sie belegt | Was sie nicht belegt |
| --- | --- | --- |
| **Brain Evidence** | Kontext-/Trust-Lage aus Context tools/records oder ehrlichem Repo-Fallback | Ausführungserfolg, Final-CI, Merge-Reife |
| **Agent Run Evidence** | Dass ein governed Provider-Lauf startete/endete und welche Artefakte entstand | hosted Required Checks SUCCESS; Completeness; Merge-Authority |
| **Targeted Slice Validation** | Eng begrenzte Tests/Checks für den Delivery-Slice | Full Fast-CI / Final-Head-CI |
| **Final CI / hosted Required Checks** | Commitgebundene Final-Evidence auf exaktem PR-Head SHA | Slice-Lokalität; Brain-Kontext; Approval-als-Merge |

Regeln:

1. Brain Evidence ist Kontext-Evidence und autorisiert keine Writes.
2. Agent Run Evidence ist Ausführungsevidence und ersetzt keine Final-CI.
3. Targeted Slice Validation ist kein Final-Head-CI.
4. Die hosted Required Checks (`ci (Unit/Integration + Lint gesammelt)` +
   `policy-gate`) sind commitgebundene Final-CI-Evidence für Merge-Gates.
5. Approval-Review-Artefakte sind weder Final-CI noch Mergefreigabe.

## 7. Zero-Click und Bootstrap

### 7.1 Normalbetrieb (Zero-Click)

Nach **einmaligem** externem Bootstrap gilt der Normalbetrieb als
**repo-deklarativ**:

- CLI/SDK/öffentliche APIs und repo-versionierte Config/Registry
- Kein wiederholtes Zusammenklicken von Agenten, Triggern, MCPs oder
  Betriebsprofilen im Cursor-Dashboard
- Erwartete spätere Frontdoor (Epic `#4249`, Implementierung außerhalb `#4250`):
  `python -m tools.agent_control plan|apply|dispatch|status|drift`

### 7.2 `MANUAL_BOOTSTRAP_ONLY`

Felder/Capabilities, die öffentlich nicht automatisierbar sind:

1. werden als `MANUAL_BOOTSTRAP_ONLY` inventarisiert,
2. einmalig manuell gesetzt,
3. danach nur noch per **Capability Probe** und **Drift-Meldung** überwacht,
4. nie durch private API oder UI-Scraping „automatisiert“.

### 7.3 Secrets

- Secrets ausschließlich als Referenz oder Secret-Klasse (Store/Environment)
- Keine Klartext-Werte in Canon, Issues, Prompts, Evidence oder Logs
- Provider-API-Keys nur über Secret-Store-/Environment-Referenz

## 8. Authority- und Truth-Order

Binding authority folgt der Constitution-Hierarchie. Höher schlägt niedriger;
Live-GitHub darf diese Ordnung **nicht** umkehren:

1. **CDB Constitution** (`CDB_CONSTITUTION.md`)
2. **Binding CDB Governance** und spezifische Policies (`CDB_GOVERNANCE.md`,
   `CDB_*_POLICY.md`, inkl. `CDB_AGENT_POLICY.md`)
3. **Anwendbare, bereits owner-ratifizierte** kanonische Contracts und Runbooks
4. **GitHub- und Repo-Live-State** für operative Fakten *innerhalb* dieser
   Grenzen (Issue/PR-Zustand, Checks, Branches, Diffs, Kommentare als Evidenz)
5. Verifizierte Context-/DB-/MCP-Evidence mit Record-Nachweis
6. Ledger (`CURRENT_STATUS.md` u. a.), Backoffice und Memory

Regeln:

- Ein GitHub-Issue, PR-Kommentar, Check oder Branch überschreibt keine
  bindende Governance und erzeugt keine verbotene Authority.
- Live-State darf veraltete operative Snapshots/Ledger korrigieren.
- Widerspruch zu bindender Governance → `HOLD` oder `BLOCKED`, kein stilles
  Override.
- Dieses Canon-Dokument steht **unter** Constitution/Governance/Policies und
  darf sie weder ersetzen noch abschwächen.
- Ein Execution Contract darf Rechte nur innerhalb dieser Hierarchie
  beschreiben; Approval, Delivery und Tests erzeugen keine Merge-Authority.

Board-Stage `trade-capable` und Ledger-Einträge erzeugen kein Live-Go.
LR-SSOT bleibt [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md).

## 9. Lineage

| Issue | Rolle für ACP |
| --- | --- |
| `#4202`, `#4228` | Gelieferte PR-Routing-/Policy-Grundlage |
| `#4226`, `#4227` | Delivery-/Merge-Skill-Trennung (Lineage; nicht neu erfinden) |
| `#4170` | `cdb-local-ci` / Final-CI-Härtung (Lineage; nicht durch Cursor ersetzen) |
| `#1640`, `#1644` | Historische **GitHub Workflow** Control Plane — nur Abgrenzung |
| `#4249` | Meta-Epic ACP |
| `#4250` | Dieses Canon-Dokument (Owner-ratified at `c691a8d0`) |
| `#4251`+ | Folge-Implementierungen; Schemata/Code außerhalb dieses Docs |

Konflikte mit `#4226`/`#4227`/`#4170` werden nicht durch ACP-Neudefinition
„gelöst“. ACP referenziert ihre gelieferte Semantik und erweitert sie nicht
in Merge- oder Final-CI-Authority.

## 10. Verhältnis zu bestehenden Canon-Flächen

| Fläche | Verhältnis |
| --- | --- |
| [`CDB_AGENT_POLICY.md`](CDB_AGENT_POLICY.md) | Write-Gates, Autonomie-Zonen, Agentenverhalten — ACP ergänzt Orchestrierungs-Authority, ersetzt Policy nicht |
| [`PR_ROUTING_AND_BATCH_MERGE_POLICY.md`](../../docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md) | Delivery/Merge-Trennung und Router — ACP konsumiert, ersetzt nicht |
| [`merge_policy_ci_gate.md`](../../docs/runbooks/merge_policy_ci_gate.md) | Required Final-CI / Capability Merge — ACP konsumiert, ersetzt nicht |
| [`ISSUE_AND_BRANCH_LIFECYCLE.md`](ISSUE_AND_BRANCH_LIFECYCLE.md) | Issue/Branch-Lifecycle — ACP Run-Lifecycle ist orthogonal und ergänzend |
| GitHub Workflow Control Plane | Andere Systemfläche; keine Vermischung |

## 11. Stop-Bedingungen für ACP-Arbeit

STOP und dokumentieren, wenn:

- kein sicherer PR-Route-Entscheid möglich ist
- ein anderer aktiver PR `#4250` bereits implementiert
- Scope Dispatcher-/Provider-/Registry-Code verlangt (andere Child-Issues)
- Merge-Authority oder Live-Go in den Canon rutscht
- private Cursor-Endpunkte oder UI-Scraping erforderlich wären
- verpflichtende Canon-Dateien fehlen oder widersprechen
- ungeklärter Konflikt mit `#4226`, `#4227` oder `#4170` entsteht

## 12. Execution Contract Anchor (`#4251`)

Schema und Validator für die Router-Handoff-Übergabe:

- Spec: [`docs/contracts/agent_execution/CDB_AGENT_EXECUTION_CONTRACT_V1.md`](../../docs/contracts/agent_execution/CDB_AGENT_EXECUTION_CONTRACT_V1.md)
- JSON Schema: [`docs/contracts/cdb_agent_execution.v1.schema.json`](../../docs/contracts/cdb_agent_execution.v1.schema.json)
- Tooling: `python -m tools.agent_execution_contract`

Dieses Canon-Dokument ist die Authority-/Lifecycle-SSOT für ACP-Rollen und
Truth Order. Feldshapes und Hash/Attenuation liegen im
Execution-Contract-Slice `#4251`. Registry/Reconciler folgen in `#4252` und
dürfen Contract-Autorität nicht erweitern.
