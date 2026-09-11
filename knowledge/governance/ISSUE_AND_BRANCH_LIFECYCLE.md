# ISSUE_AND_BRANCH_LIFECYCLE.md

## Claire de Binare – Issue, Branch & PR Lineage Policy

**Status:** Canonical  
**Zweck:** Eindeutige Delivery-Lineage ohne Issue-, Branch- oder PR-Explosion
**Gültig für:** Alle Agenten, Tools und Humans
**Transition:** Human-authorized via Issue `#4202`

---

## 1. Grundprinzip

**Issues sind langfristige Verträge.**  
**Commits, Branches und PR-Ledger bilden ihre nachvollziehbare Evidence-Linie.**

Ein Issue benötigt einen eindeutig zugeordneten Arbeitskontext, aber **kein eigener finaler Pull Request** ist zwingend. Kompatible Issue-Slices dürfen durch
den read-only PR Steward einem kontrollierten Batch-PR zugeordnet werden.

## 2. Issue-Regeln

1. Kein neues Issue, wenn bereits ein Vertrag für dasselbe Ziel existiert.
2. Ein Issue bleibt offen, bis seine ursprüngliche DoD vollständig erfüllt und
   die Lieferung auf `main` verifiziert ist.
3. Slice-Handoffs dokumentieren Ziel-PR, Commit, targeted Validation und
   Restunsicherheit als Issue-Kommentar.
4. Keine vorzeitige Issue-Closure und keine erfundene Merge-Evidence.
5. Pausierte oder blockierte Issues dürfen nicht in aktive Batch-PRs geroutet
   werden.

## 3. Routing- und Branch-Regeln

1. Vor Branch-, Worktree-, PR-Erstellung oder Plan-Finalisierung wird
   `cdb-pr-router` ausgeführt.
2. Ein bestehender kompatibler offener PR wird wiederverwendet.
3. Ein neuer Batch- oder Dedicated-Branch entsteht nur, wenn keine sichere Route
   existiert und der Router dies ausdrücklich entscheidet.
4. Ein Issue darf zu jedem Zeitpunkt nur einen aktiven schreibenden Arbeitskontext
   besitzen.
5. Mehrere kompatible Issues dürfen denselben Batch-Branch verwenden; ihre
   Commits und Evidence bleiben im PR-Ledger getrennt nachvollziehbar.
6. Security-, Secrets-, Migration-, Live-Readiness- sowie unabhängige
   Risk-/Execution-Verträge bleiben Dedicated.

## 4. PR-Regeln

1. Jeder PR referenziert mindestens ein offenes Issue.
2. Batch-PRs besitzen den versionierten `cdb-batch-pr:v1`-Marker und ein
   maschinenlesbares Ledger.
3. Nur `steward_state=accepting_slices` darf neue Issue-Slices aufnehmen.
4. Jede gelieferte Issue besitzt genau einen Closure-Eintrag im finalen PR-Body.
5. `Closes #N` schließt erst beim tatsächlichen Merge; vorzeitiges manuelles
   Schließen bleibt verboten.
6. Ein Merge-Trigger friert den PR als `merge_candidate` ein, autorisiert aber
   keinen Merge.

## 4.1 Post-Merge Status-/Ledger-Pflege (kein Nachlauf-PR)

Nach einem Merge ist ein **sofortiger eigener Nachlauf-PR** verboten, wenn sein
einziger Zweck eine `CURRENT_STATUS-only`- oder `ledger-only`-Nachpflege ist
(Issue `#4218`).

**Erlaubte Standardpfade:**

1. Status-/Ledger-Anpassung **vor dem Freeze** im ursprünglichen Batch-/Feature-PR.
2. Spätere Anpassung im nächsten kompatiblen **`docs-governance`**-Batch
   (über `cdb-pr-router`; kein Sofort-Tail-PR).

**Fail-closed:** Ist unklar, ob eine Korrektur zwingend sofort nötig ist, darf
kein Einzel-PR entstehen. Der Befund wird als Follow-up dokumentiert und später
gebündelt.

**Enge Ausnahme (sicherheitskritisch):** Nur wenn ein aktueller Claim
nachweislich sicherheitskritisch falsch ist und unmittelbar zu falscher
Runtime-, Risk-, LR- oder Echtgeld-Entscheidung führen könnte, und die Korrektur
nicht verantwortbar bis zum nächsten Batch warten kann. Dann: Ausnahme explizit
begründen, `cdb-pr-router` ausführen, dedizierten Governance-/Incident-Scope
nutzen — keinen gewöhnlichen CURRENT_STATUS-Nachlauf-PR daraus machen.

**Keine Ausnahme:** fehlende Merge-SHA im Ledger, veraltete PR-Zahl/Datumszeile,
Statuszusammenfassung hinter GitHub-Live-State, kosmetische Nachpflege.

## 5. Validation und Abschluss

### Slice-Handoff

- targeted Tests und relevante Contract-Tests
- Lint/Format für den betroffenen Scope
- `git diff --check`
- Commit und Push in den gerouteten PR
- Ledger- und Issue-Handoff
- kein Full Fast-CI und kein `cdb-local-ci` Publish als Default
- Status `DONE_SLICE_ADDED_TO_BATCH_PR`

### Finaler Batch-Head

1. Intake einfrieren.
2. Aktuelles `main` integrieren.
3. Kombinierten Diff reviewen.
4. Vollständige Fast-CI auf exakt diesem Head ausführen.
5. Hosted Required Checks (`ci (Unit/Integration + Lint gesammelt)` + `policy-gate`) auf exakt diesem Head verifizieren.
6. Head-, Base-, Review- und Lock-Evidence erneut prüfen.
7. Normal mergen; kein Admin-Bypass ohne separate Human Authority.
8. Nur vollständig gelieferte Issues nach verifiziertem Main-Merge schließen.

## 6. Single-Writer

Issue- und PR-Level-Locks folgen
[`CDB_AGENT_POLICY.md`](CDB_AGENT_POLICY.md). Fremde, partielle oder stale Locks
werden fail-closed behandelt und niemals blind überschrieben.

## 7. Trust Score Integration

Routing, Lock, Handoff, Freeze, Merge und Issue-Closure sind Decision Events.
Unsicherheit bleibt sichtbar; bei fehlender Evidence bleibt das Issue offen.

## 8. Grenzen

- Human Authority und explizites Scope-GO bleiben erforderlich.
- Branch Protection wird durch diesen Lifecycle nicht gelockert.
- LR bleibt `NO-GO`.
- Echtgeld-, Tresor-, Risk- und Execution-Grenzen bleiben unverändert.
