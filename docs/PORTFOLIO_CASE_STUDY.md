# Claire de Binare — Portfolio Case Study

## 1. The problem

Claire de Binare is a deterministic trading and validation system, but the portfolio value of the project is broader than trading.

The central systems problem is:

> **How can a complex automated system distinguish technical capability from justified permission to operate?**

In a safety-relevant system, “the code runs,” “the tests passed,” “a stage is trade-capable,” and “real-capital operation is authorized” are different claims. Claire keeps those claims separate.

## 2. Why production claims are dangerous

Automation creates a strong temptation to compress many states into one:

```text
implemented → tested → ready → safe → live
```

That shortcut is deliberately rejected here.

Instead, the repository uses separate status and evidence surfaces for:

- engineering state,
- board/control stage,
- deterministic validation,
- replay and shadow evidence,
- soak / chaos evidence,
- live-readiness,
- explicit human authorization.

A positive result at one layer cannot silently authorize a stronger claim at another layer.

## 3. Stage is not Live Readiness

The root README currently records the Control-Board stage as `trade-capable`.

At the same time, the canonical Live-Readiness source records:

- **global verdict: NO-GO**,
- **LR-050: NO-GO / fail-closed**,
- **not ready for live capital**,
- **not ready for human live approval**.

This is not a contradiction. It is the design.

The Board stage answers a capability question. Live Readiness answers an authorization question.

Authoritative references:

- [Live Readiness Audit Status](live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- [LR-050 Final Reconcile](live-readiness/LR-050-FINAL-RECONCILE.md)
- [Control Register](runbooks/CONTROL_REGISTER.md)

## 4. Evidence contract

The project follows an evidence-first rule:

> **A stronger operational claim requires evidence that is valid for exactly that claim.**

Examples of evidence layers in the repository include:

- deterministic tests,
- replay evidence,
- paper/shadow execution,
- zero-execution proofs,
- long-running soak evidence,
- chaos/recovery evidence,
- status/state files,
- explicit Go/No-Go reconciliations.

Evidence is not interchangeable.

A successful unit test does not prove production safety. A prestart checklist does not prove live-capital readiness. A closed GitHub issue does not itself clear a runtime gate.

## 5. Fail-closed principle

The system prefers a conservative stop when required state is:

- missing,
- stale,
- ambiguous,
- contradictory,
- incomplete,
- insufficient for the requested authority.

This is visible in the Live-Readiness model: open blockers retain **NO-GO** rather than being interpreted optimistically.

The principle can be summarized as:

```text
unknown evidence != permission
partial PASS     != global PASS
trade-capable    != live-authorized
merged docs      != runtime authorization
```

## 6. Concrete NO-GO case: LR-050

LR-050 is a useful real example because it demonstrates that the system can possess substantial positive evidence and still refuse the stronger claim.

The repository documents:

- completed earlier validation phases,
- a committed P5 prestart pack with GO status,
- continuity / shadow evidence,
- delivered planning SSOTs.

Despite that, the canonical LR-050 reconcile remains:

- **NO-GO**,
- **fail-closed**,
- **not ready for live capital**,
- **not ready for human live approval**.

Why?

Because prestart evidence is only evidence for prestart readiness. It does not close remaining `blocker_before_live` conditions and does not replace explicit human authorization.

This is exactly the behavior the governance model is meant to produce: **positive local evidence must not be inflated into a broader production claim.**

## 7. Re-validation

A status is not treated as permanent truth merely because it once passed.

When the relevant subject changes, the system expects fresh evidence appropriate to the changed state.

At portfolio level, the pattern is:

```text
Change / new candidate
        ↓
Bounded validation scope
        ↓
Evidence generation
        ↓
Gate interpretation
   ┌────┴────┐
 PASS       HOLD / FAIL
   ↓            ↓
next stage   remain fail-closed
   ↓
new material change → re-validate
```

This protects against stale approval and claim drift.

## 8. Auditability

The repository is intentionally documentation-heavy because a safety claim should be reconstructable.

Important decisions are tied to explicit:

- control registers,
- readiness state,
- evidence artifacts,
- issue/PR history,
- gate documents,
- validation reports.

The goal is not bureaucracy for its own sake. The goal is to make it possible to answer:

- What was believed?
- What was actually proven?
- Which evidence supported it?
- Which authority was still missing?
- Why did the system proceed or stop?

## 9. My role

My contribution is primarily system and governance design.

I work on:

- decomposing complex goals into explicit states,
- defining boundaries and non-goals,
- specifying acceptance and validation criteria,
- separating technical readiness from operational authority,
- orchestrating AI-assisted implementation and review,
- identifying contradictions and missing evidence,
- keeping unsupported claims conservative.

A substantial amount of code and documentation is produced with AI assistance. The portfolio claim is therefore not “I manually wrote this entire trading platform.”

The claim is:

> **I design and operate the system of requirements, boundaries, evidence and validation that keeps an AI-assisted complex project from confusing progress with proof.**

## 10. What this project demonstrates

- systems thinking,
- deterministic state design,
- governance,
- evidence-based validation,
- fail-closed decision making,
- risk boundaries,
- auditability,
- requirements engineering,
- AI-assisted delivery orchestration,
- explicit handling of uncertainty.

## 11. What this project does not claim

This case study does **not** claim:

- that live trading is authorized,
- that the system is production-safe for real capital,
- that past returns prove future profitability,
- that I am a quantitative ML researcher,
- that I manually implemented every component,
- that a Board-stage label overrides Live Readiness.

The current live-capital verdict remains whatever the canonical Live-Readiness SSOT states. At the time of this portfolio documentation change, that verdict is **NO-GO**.

## 12. Why this matters outside trading

The same design problem appears in many AI systems:

- an agent returns an answer,
- a workflow says “success,”
- a model produces a confident result,
- a CI job is green,
- an automation has permission to act.

None of those facts alone proves that the larger outcome is safe or correct.

Claire de Binare is therefore a useful case for **AI Governance, AI Quality, Agent Evaluation, Reliability and regulated AI delivery**: it treats claims, evidence and authority as separate things that must be reconciled deliberately.
