# Context Evidence, Claim, Decision, and Memory Retrieval Runbook

## 1. Purpose and Scope

- Part of Wave 14 (#2115–#2128) of Epic #1976 (Context Intelligence System)
- Operator/agent-facing guide for safe use of Evidence Lookup, Claim Resolution,
  Decision History/Replay, Scoped Memory Read, Trust Summary, and Briefing Enrichment tools
- Scope: read-only context retrieval — no writes, no live capital, no Echtgeld-Go
- Prerequisite: Issues #2116–#2126 CLOSED; #2122 (Briefing Enrichment) partially open (see Section 9)

**LR-Status: NO-GO** — this runbook covers context tooling only.
No runtime, trading, or live-capital implication.

---

## 2. Tool Overview

### `tools/surrealdb/evidence_lookup.py` — Evidence Lookup v1 (#2116)

- **Schema version:** `evidence-lookup/v1`
- **Modes:** `by_artifact`, `by_claim`, `by_decision`, `by_source_path`, `by_run_id`,
  `by_evidence_type`, `by_freshness`, `by_confidence`
- **Read-only.** Pure domain function. No SurrealDB writes.
- **MCP adapter:** `cdb_context_evidence_resolve` (handler in `tools/mcp/context_evidence_memory_tools.py`)

### `tools/surrealdb/claim_resolver.py` — Claim Resolution v1 (#2117)

- **Schema version:** `claim-resolver/v1`
- **Modes:** `by_claim_id`, `by_topic`, `by_scope`, `by_status`, `by_artifact`,
  `by_evidence_ref`, `by_decision_ref`
- **Claim statuses:** `proposed`, `supported`, `weakly_supported`, `disputed`,
  `superseded`, `stale`, `invalidated`
- **MCP adapter:** `cdb_context_claim_resolve`

### `tools/surrealdb/decision_history_query.py` — Decision History v1 (#2118)

- **Contract:** `docs/surrealdb/decision_replay_query_contract.md`
- **Read-only.** Filters decision events by decision ID, topic, scope, artifact, issue, or status.
- **MCP adapter:** `cdb_context_decision_history`

### `tools/surrealdb/decision_replay_builder.py` — Decision Replay v1 (#2119)

- **Contract:** `docs/surrealdb/decision_replay_query_contract.md`
- **Replays a decision chain** for audit or explanation — no re-execution, no write.
- **MCP adapter:** `cdb_context_decision_replay`

### `tools/surrealdb/memory_read.py` — Scoped Memory Read v1 (#2120)

- **Schema version:** `memory-read/v1`
- **Modes:** `by_scope`, `by_topic`, `by_artifact`, `by_decision`, `by_agent`,
  `by_freshness`, `by_memory_type`
- **TTL-aware:** stale records are flagged, not silently returned.
- **Memory is a hint, not ground truth.**
- **MCP adapter:** `cdb_context_memory_get`

### `tools/surrealdb/trust_summary.py` — Context Trust Summary Builder v1 (#2121)

- **Schema version:** `trust-summary/v1`
- **Trust levels:** `blocked`, `weak`, `acceptable`, `strong`
- **Composite score weights:** evidence 30%, claims 25%, decisions 25%, memory 20%
- **MCP adapter:** `cdb_context_trust_summary`

### `tools/mcp/context_evidence_memory_tools.py` — MCP Adapter (#2123/#2125)

Handlers:
- `handle_cdb_context_evidence_resolve(request)`
- `handle_cdb_context_claim_resolve(request)`
- `handle_cdb_context_memory_get(request)`
- `handle_cdb_context_trust_summary(request)`

All handlers: read-only, fail-closed, return `metadata.read_only=True`.

### `tools/mcp/context_decision_tools.py` — MCP Adapter (#2124)

Handlers:
- `handle_cdb_context_decision_history(request)`
- `handle_cdb_context_decision_replay(request)`

---

## 3. When to Use Which Tool

| Use Case | Tool | Timing |
|----------|------|--------|
| Find evidence backing a claim or artifact | `cdb_context_evidence_resolve` | Before accepting a claim as fact |
| Resolve claim status (supported/disputed/stale) | `cdb_context_claim_resolve` | Before acting on a claim |
| Review what decisions were made and why | `cdb_context_decision_history` | Before repeating or contradicting a past decision |
| Replay a decision chain for audit | `cdb_context_decision_replay` | During post-mortem or governance review |
| Read scoped memory about a task/scope | `cdb_context_memory_get` | As a hint before starting work |
| Assess overall trust level of context | `cdb_context_trust_summary` | After gathering evidence/claims/memory |
| Enrich an agent briefing with above | `cdb_context_briefing` | Before acting on any scoped task |

**Recommended order:**
1. Evidence Lookup → 2. Claim Resolution → 3. Decision History →
4. Memory Read → 5. Trust Summary → 6. Briefing Enrichment

---

## 4. Required Inputs and Safe Defaults

### `cdb_context_evidence_resolve`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `evidence_records` | list | Yes | In-memory evidence records |
| `mode` | str | Yes | One of the 8 lookup modes |
| `artifact` | str | mode-dependent | Required for `by_artifact` |
| `claim` | str | mode-dependent | Required for `by_claim` |
| `decision` | str | mode-dependent | Required for `by_decision` |
| `source_path` | str | mode-dependent | Required for `by_source_path` |
| `run_id` | str | mode-dependent | Required for `by_run_id` |
| `evidence_type` | str | mode-dependent | Required for `by_evidence_type` |
| `min_confidence` | float | mode-dependent | Required for `by_confidence`; threshold in [0.0, 1.0] |
| `freshness_days` | int | mode-dependent | Required for `by_freshness`; filter window in days |

### `cdb_context_claim_resolve`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `claim_records` | list | Yes | In-memory claim records |
| `mode` | str | Yes | One of the 7 resolve modes |
| `claim_id` | str | mode-dependent | Required for `by_claim_id` |
| `topic` | str | mode-dependent | Required for `by_topic` |
| `scope` | str | mode-dependent | Required for `by_scope` |
| `status` | str | mode-dependent | Required for `by_status` |
| `artifact` | str | mode-dependent | Required for `by_artifact` |
| `evidence_ref` | str | mode-dependent | Required for `by_evidence_ref` |
| `decision_ref` | str | mode-dependent | Required for `by_decision_ref` |
| `known_evidence_ids` | list[str] | No | Cross-validates evidence backing |

### `cdb_context_decision_history`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_events` | list | Yes | In-memory decision events |
| `mode` | str | Yes | One of: `by_decision_id`, `by_topic`, `by_scope`, `by_artifact`, `by_issue`, `by_status`, `current_for_topic`, `superseded_for_topic` |
| `decision_id` | str | mode-dependent | Required for `by_decision_id` |
| `topic` | str | mode-dependent | Required for `by_topic`, `current_for_topic`, `superseded_for_topic` |
| `scope` | str | mode-dependent | Required for `by_scope` |
| `artifact` | str | mode-dependent | Required for `by_artifact` |
| `issue` | str | mode-dependent | Required for `by_issue` |
| `status` | str | mode-dependent | Required for `by_status` |
| `limit` | int | No | Max decisions to return (default 200) |

### `cdb_context_decision_replay`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_events` | list | Yes | In-memory decision events |
| `mode` | str | Yes | One of: `replay_by_decision_id`, `replay_current_for_topic`, `replay_superseded_for_topic`, `replay_by_scope`, `replay_by_artifact`, `replay_by_status` |
| `decision_id` | str | mode-dependent | Required for `replay_by_decision_id` |
| `topic` | str | mode-dependent | Required for `replay_current_for_topic`, `replay_superseded_for_topic` |
| `scope` | str | mode-dependent | Required for `replay_by_scope` |
| `artifact` | str | mode-dependent | Required for `replay_by_artifact` |
| `status` | str | mode-dependent | Required for `replay_by_status` |
| `limit` | int | No | Max decisions to return (default 50, max 500) |

### `cdb_context_memory_get`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `memory_records` | list | Yes | In-memory memory records |
| `mode` | str | Yes | One of: `by_scope`, `by_topic`, `by_artifact`, `by_decision`, `by_agent`, `by_freshness`, `by_memory_type` |
| `scope` | str | mode-dependent | Required for `by_scope` |
| `topic` | str | mode-dependent | Required for `by_topic` |
| `artifact` | str | mode-dependent | Required for `by_artifact` |
| `decision` | str | mode-dependent | Required for `by_decision` |
| `agent` | str | mode-dependent | Required for `by_agent` |
| `memory_type` | str | mode-dependent | Required for `by_memory_type` |
| `freshness_days` | int | mode-dependent | Required for `by_freshness`; filter window in days |
| `limit` | int | No | Max records to return (default 200) |

### `cdb_context_trust_summary`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scope` | str | Yes | Scope name for the summary |
| `evidence_result` | dict | No | Output from evidence lookup |
| `claim_result` | dict | No | Output from claim resolution |
| `decision_result` | dict | No | Output from decision history |
| `memory_result` | dict | No | Output from memory read |

---

## 5. Example Requests

### Evidence Lookup — by_artifact

```json
{
  "tool": "cdb_context_evidence_resolve",
  "evidence_records": [
    {
      "evidence_id": "ev-001",
      "artifact_refs": ["risk_service.py"],
      "evidence_type": "test_pass",
      "confidence": 0.95,
      "created_at": "2026-05-01T10:00:00Z",
      "source_refs": ["tests/unit/risk/test_risk_service.py"],
      "claim_refs": ["claim-001"]
    }
  ],
  "mode": "by_artifact",
  "artifact": "risk_service.py"
}
```

### Claim Resolution — by_status (disputed)

```json
{
  "tool": "cdb_context_claim_resolve",
  "claim_records": [
    {
      "claim_id": "claim-004",
      "status": "disputed",
      "description": "Kill-switch is always active",
      "evidence_refs": ["ev-003"],
      "artifact_refs": ["kill_switch.py"]
    }
  ],
  "mode": "by_status",
  "status": "disputed"
}
```

### Decision History — by_topic

```json
{
  "tool": "cdb_context_decision_history",
  "decision_events": [...],
  "mode": "by_topic",
  "topic": "RiskManager"
}
```

### Decision Replay — audit chain from root

```json
{
  "tool": "cdb_context_decision_replay",
  "decision_events": [...],
  "mode": "replay_by_decision_id",
  "decision_id": "dec-001",
  "limit": 50
}
```

### Memory Read — by_scope

```json
{
  "tool": "cdb_context_memory_get",
  "memory_records": [...],
  "mode": "by_scope",
  "scope": "wave14"
}
```

### Trust Summary — composite

```json
{
  "tool": "cdb_context_trust_summary",
  "scope": "wave14",
  "evidence_result": "<output of cdb_context_evidence_resolve>",
  "claim_result": "<output of cdb_context_claim_resolve>",
  "decision_result": "<output of cdb_context_decision_history>",
  "memory_result": "<output of cdb_context_memory_get>"
}
```

---

## 6. Interpreting Trust Summary Output

| Trust Level | Score Range | Interpretation |
|-------------|-------------|----------------|
| `blocked` | < 0.30 | Do not proceed. Missing or contradicted evidence. Stop condition. |
| `weak` | 0.30–0.54 | Proceed with explicit human approval. Flag all gaps. |
| `acceptable` | 0.55–0.79 | Proceed with caution. Verify key evidence before action. |
| `strong` | ≥ 0.80 | Evidence is solid. Proceed normally; document evidence trail. |

**Guardrails:**
- Trust level is derived from in-memory records only — it is a **hint**, not a certification.
- A `strong` trust level does not authorize live capital, runtime change, or Echtgeld-Go.
- A `blocked` trust level must always produce a stop condition in the briefing.
- Missing evidence must be treated as a blocker for critical paths.
- Stale/weak/disputed evidence must be surfaced, not silently dropped.

---

## 7. Handling Missing, Stale, and Disputed Evidence

### Missing Evidence

- If `lookup_evidence_v1` returns an empty result for a critical artifact, produce a
  `missing_evidence` stop condition.
- Do not proceed or guess. Block the action path.
- Document which artifact and which claim was unresolvable.

```
Stop condition: S5 — missing evidence resolution
Required: evidence for <artifact_id> before proceeding.
```

### Stale Evidence

- `by_freshness` mode returns only records with `created_at` within the `freshness_days`
  window; older records are excluded, not marked `stale: true`.
- The `stale: true` flag is read from the record itself — `lookup_evidence_v1` does not
  compute staleness from age.
- Stale evidence contributes negatively to the trust score.
- Operator must review and re-verify before treating stale evidence as current.

### Stale/Superseded Memory

- Memory records with exceeded TTL are flagged `stale: true` by `read_memory_v1`.
- Superseded memory records are returned with status `superseded`.
- **Memory is a hint, not ground truth.** Never block solely on memory; never trust
  superseded memory without re-validation.

### Disputed Claims

- Claims in status `disputed` lower the trust score significantly.
- Disputed claims must be surfaced in `missing_evidence_notice` and
  `contradictory_evidence_notice` of the briefing.
- Do not act on disputed claims without human review.

---

## 8. Human-GO Boundaries

The following actions **always require explicit human GO** regardless of trust level:

| Action | Required GO |
|--------|-------------|
| Live capital deployment | GO LIVE (LR gate — currently NO-GO) |
| Echtgeld trading | GO ECHTGELD (LR gate — currently NO-GO) |
| Strategy validation | Human Gate |
| Merge of code changes | GO MERGE |
| Push to main | GO PUSH |
| Issue close / comment | GO GITHUB LIVE |
| Admin merge (\--admin\) | GO ADMIN MERGE - **never** a bypass for missing/red hosted Required Checks (\ci (Unit/Integration + Lint gesammelt)\, \policy-gate\); with \nforce_admins=true\ the Required Status remains mandatory |
| Review thread resolve | GO REVIEW THREAD RESOLVE |
| Commit | GO COMMIT |

**No context tool output — regardless of trust level — substitutes for these human GO signals.**

---

## 9. Current Status: Briefing Enrichment (#2122)

As of Wave-14 PR #2343, `context_bridge.py` includes placeholder Briefing Enrichment fields
(`enriched_evidence`, `enriched_decisions`, `enriched_memory`), but **does not yet call**
`lookup_evidence_v1`, `resolve_claims_v1`, `read_memory_v1`, or `build_trust_summary_v1`.

- Issue #2122 is **OPEN**.
- The Wave-14 MCP tools (`cdb_context_evidence_resolve`, `cdb_context_claim_resolve`,
  `cdb_context_memory_get`, `cdb_context_trust_summary`, `cdb_context_decision_history`,
  `cdb_context_decision_replay`) are implemented as adapter functions but are **not yet
  registered in `tools/mcp/registry.py`**.
- Until PR 2 (code slice) merges, the Briefing Enrichment fields return empty lists and
  the trust summary is a partial-mode string.

This does **not** affect Wave-14 read-only retrieval services (#2116–#2121), which are
fully functional and tested (53 tests passing).

---

## 10. Tests and Fixtures

| File | Covers |
|------|--------|
| `tests/unit/surrealdb/test_wave14_services_v1.py` | evidence_lookup, claim_resolver, memory_read, trust_summary (37 tests) |
| `tests/unit/tools/mcp/test_mcp_wave14_tools.py` | MCP handlers evidence/claim/memory/trust (16 tests) |
| `tests/unit/surrealdb/test_decision_history_query_v1.py` | decision_history_query |
| `tests/unit/surrealdb/test_decision_replay_builder_v1.py` | decision_replay_builder |
| `tests/unit/surrealdb/test_decision_mcp_tools_v1.py` | decision MCP tools |
| `tests/unit/tools/mcp/test_mcp_briefing_enrichment.py` | Briefing enrichment stub (5 tests) |
| `tests/fixtures/surrealdb/wave14/wave14_v1.json` | Evidence/claim/memory fixture data |
| `tests/fixtures/surrealdb/decision_history/` | Decision history fixture data |
| `tests/fixtures/surrealdb/decision_replay/` | Decision replay fixture data |
| `tests/fixtures/surrealdb/decision_mcp/` | Decision MCP fixture data |

### Running Wave-14 Unit Tests

```bash
pytest tests/unit/surrealdb/test_wave14_services_v1.py -v -m unit
pytest tests/unit/tools/mcp/test_mcp_wave14_tools.py -v -m unit
pytest tests/unit/surrealdb/test_decision_history_query_v1.py -v -m unit
pytest tests/unit/surrealdb/test_decision_replay_builder_v1.py -v -m unit
pytest tests/unit/surrealdb/test_decision_mcp_tools_v1.py -v -m unit
```

No SurrealDB instance required. All tests run in-memory (NoopAdapter pattern).

---

## 11. Guardrails Summary

- **No Write** — every tool in Wave 14 is read-only. No evidence write, no decision write,
  no memory write, no repo write.
- **No Live-Go** — LR-STATUS remains NO-GO. No context tool output authorizes live capital.
- **No Echtgeld-Go** — Board-Stage `trade-capable` is orthogonal to LR; does not authorize
  real money.
- **Fail-closed** — if evidence is missing or trust is `blocked`, the tool stops and reports,
  never guesses.
- **Memory is a hint** — memory records must not be treated as authoritative system state.
- **Decisions explain history** — decision replay provides audit trace only; it does not
  re-execute or authorize anything.
- `approval_semantics.no_echtgeld_go: true` is carried in every tool response.
