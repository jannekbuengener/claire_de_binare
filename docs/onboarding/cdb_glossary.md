# CDB Glossary

## Navigation

- [Root README](../../README.md)
- [Dokumentationsindex](../../docs/index.md)
- [Developer Visual Start](DEVELOPER_VISUAL_START_HERE.md)
- [Developer Onboarding](../../DEVELOPER_ONBOARDING.md)
- [Core Eventflows](core-eventflows/README.md)
- [Repo Brain / Context Intelligence](repo_brain_context_intelligence.md)

## Status / Authority

**Status:** Docs-only onboarding artifact. Terminology reference — not authoritative for governance, policy, or gate decisions.

**Issues:** [#3247](https://github.com/jannekbuengener/Claire_de_Binare/issues/3247), [#3262](https://github.com/jannekbuengener/Claire_de_Binare/issues/3262)

**Parent:** [#3253 Core-System Eventflow Map Pack](https://github.com/jannekbuengener/Claire_de_Binare/issues/3253)

**Boundary:** This glossary defines terms for onboarding orientation. It does not define new policies, weaken existing LR/Risk/Execution rules, or create any Live-Go or Echtgeld-Go.

LR remains NO-GO. Board stage `trade-capable` is not Live-Go. No Echtgeld-Go.

## How to use this glossary

- Terms are grouped by domain area.
- Each term has: **Definition**, **CDB Context**, **Authority Boundary**, and **Primary Source**.
- If you encounter a term you don't understand in any onboarding doc or flow diagram, look it up here first.
- This glossary is linked from the main onboarding surfaces ([README](../../README.md), [DEVELOPER_VISUAL_START_HERE](DEVELOPER_VISUAL_START_HERE.md), [core eventflows README](core-eventflows/README.md)).

## Governance and readiness terms

### LR
- **Definition:** Live-Readiness. CDB's formal gate system that determines whether the system may operate with real capital.
- **CDB Context:** LR is the SSOT for Echtgeld Go/No-Go. The verdict is documented in [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md).
- **Authority Boundary:** LR is a human-controlled gate. No agent, service, or automation can change the LR verdict. LR remains NO-GO until explicitly cleared.
- **Primary Source:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)

### LR-SSOT
- **Definition:** The single source of truth for LR status — the LR audit status document.
- **CDB Context:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) is the sole LR-SSOT. Board stage, [CURRENT_STATUS.md](../../CURRENT_STATUS.md), or any other file cannot override it.
- **Authority Boundary:** Read-only for agents. Human-maintained.
- **Primary Source:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)

### SSOT
- **Definition:** Single Source of Truth. The one authoritative location for a given fact or status.
- **CDB Context:** Applied to LR status, Board stage, repo engineering status, and governance documents. Each domain has exactly one SSOT.
- **Authority Boundary:** Do not create competing SSOTs. Always verify which file is the SSOT for a given domain.
- **Primary Source:** [`AGENTS.md`](../../AGENTS.md)

### NO-GO
- **Definition:** A gate verdict meaning the action or transition is blocked.
- **CDB Context:** Used for LR status (LR remains NO-GO), gate verdicts, and stop conditions.
- **Authority Boundary:** NO-GO is final until the blocking condition is resolved and the gate is re-evaluated.
- **Primary Source:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)

### GO
- **Definition:** A gate verdict meaning the action or transition is permitted.
- **CDB Context:** Used for individual gate checks, CI status, and operational go decisions.
- **Authority Boundary:** GO is context-specific. LR-GO requires explicit human approval and is never automatic.
- **Primary Source:** [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)

### Human-GO
- **Definition:** A GO that requires explicit human approval, not an agent or automated decision.
- **CDB Context:** Required for all live-capital exposure, LR gate transitions, and certain high-risk operations.
- **Authority Boundary:** No agent can give or imply Human-GO. Human-GO must be explicit and verifiable.
- **Primary Source:** [`knowledge/governance/CDB_AGENT_POLICY.md`](../../knowledge/governance/CDB_AGENT_POLICY.md)

### Board-Stage
- **Definition:** The operational stage of the CDB project board (proof, stability, trade-capable, strategy-validated).
- **CDB Context:** Currently `trade-capable` (ratified 2026-04-08 via [#1492](https://github.com/jannekbuengener/Claire_de_Binare/issues/1492)). The Board stage is orthogonal to LR — it describes the system's operational focus, not its live-trading authorization.
- **Authority Boundary:** Board stage does not authorize live capital or strategy execution. It is not an LR gate.
- **Primary Source:** [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)

### trade-capable
- **Definition:** Board stage indicating the system can theoretically place trades.
- **CDB Context:** Means the infrastructure, services, and basic trade flow exist. It does not mean live trading is approved. LR remains NO-GO independent of this stage.
- **Authority Boundary:** trade-capable is Board context only. Never cite trade-capable as LR-Go or Echtgeld-Go.
- **Primary Source:** [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)

### Live-Readiness
- **Definition:** The state of being cleared for live trading with real capital.
- **CDB Context:** Governed by the LR process. Currently NO-GO. All phases except P5 are done; P5 (live capital) requires explicit human approval.
- **Authority Boundary:** Live-Readiness is a human gate, not a technical milestone.
- **Primary Source:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)

### Echtgeld-Go
- **Definition:** German for "real money go". The authorization to trade with real capital.
- **CDB Context:** The highest-level gate. Requires cleared LR, Human-GO, and explicit sign-off. Currently not granted.
- **Authority Boundary:** Irreversible once given in practice. Must never be assumed or implied.
- **Primary Source:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)

## Runtime and eventflow terms

### BLUE
- **Definition:** The core trading stack (compose.blue.yml). Always-on services for data, risk, execution, and persistence.
- **CDB Context:** Contains PostgreSQL, Redis, Market, Candles, Regime, Allocation, Risk, Execution, DB Writer, Paper Runner. If BLUE is down, the system cannot function.
- **Authority Boundary:** BLUE services are stateless and event-driven. They communicate exclusively through Redis.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md), [`services/README.md`](../../services/README.md)

### RED
- **Definition:** The signal and monitoring stack (compose.red.yml). Failure-isolated from BLUE.
- **CDB Context:** Contains WebSocket, Signal, Reports, Prometheus, Grafana, and exporters. RED can fail without taking down BLUE's core pipeline.
- **Authority Boundary:** RED services produce signals and observability data. They do not authorize trades.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

### Pub/Sub
- **Definition:** Redis Publish/Subscribe — a fire-and-forget broadcast messaging pattern.
- **CDB Context:** `market_data` is Pub/Sub. Messages are not persisted; late subscribers miss messages. Used for real-time market data distribution.
- **Authority Boundary:** Pub/Sub channels carry real-time data only. They are not durable, not replayable.
- **Primary Source:** [`services/README.md`](../../services/README.md)

### Redis Stream
- **Definition:** Redis Stream — a durable, append-only log data structure.
- **CDB Context:** Used for `signals`, `orders`, `order_results`, `stream.fills`, `allocation_decisions`, `portfolio_snapshots`. Consumers can read from any point and replay.
- **Authority Boundary:** Streams are the durable backbone. Downstream consumers must handle each event at least once.
- **Primary Source:** [`services/README.md`](../../services/README.md), [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

### market_data
- **Definition:** Redis Pub/Sub channel carrying real-time market data from cdb_ws.
- **CDB Context:** Published by WebSocket service (cdb_ws). Consumed by cdb_market, cdb_candles, cdb_signal, cdb_paper_runner.
- **Authority Boundary:** Fire-and-forget. No replay. No ordering guarantees.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

### signals
- **Definition:** Redis Stream containing strategy-generated trading signals.
- **CDB Context:** Produced by cdb_signal. Consumed by cdb_risk and cdb_db_writer. A signal is a proposal, not a trade authorization.
- **Authority Boundary:** Signals must pass through Risk before any order is created. A signal alone never produces a trade.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

### orders
- **Definition:** Redis Stream containing risk-approved orders ready for execution.
- **CDB Context:** Produced by cdb_risk after passing all gates. Consumed by cdb_execution and cdb_db_writer.
- **Authority Boundary:** Only Risk can write to the orders stream. Execution processes what it receives.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

### order_results
- **Definition:** Redis Stream carrying execution results back to Risk and DB Writer.
- **CDB Context:** Produced by cdb_execution. Consumed by cdb_risk (position/exposure update) and cdb_db_writer (persistence).
- **Authority Boundary:** Results are feedback, not commands. Risk uses them to update state, not to authorize new actions.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

### stream.fills
- **Definition:** Redis Stream carrying individual fill events from execution.
- **CDB Context:** Complementary to order_results. Provides granular fill-level data for Risk and persistence.
- **Authority Boundary:** Same as order_results — informational feedback, not command.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

### correlation_ledger
- **Definition:** Append-only PostgreSQL audit trail linking SIGNAL → DECISION → ORDER → FILL chains.
- **CDB Context:** The foundation for all audit, replay-vs-paper comparison, and evidence-based validation. Every trading-relevant event links back through this chain.
- **Authority Boundary:** Append-only. No deletion or modification. Persistence is evidence, not approval.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md) ([`infrastructure/database/migrations/006_correlation_phase8c.sql`](../../infrastructure/database/migrations/006_correlation_phase8c.sql))

### Paper (Eventflow context)
- **Definition:** CDB's default execution mode that simulates order fills without touching a real exchange.
- **CDB Context:** Paper is built into the Execution service. It is the default path for all orders. The Paper Runner ([`tools/paper_trading/`](../../tools/paper_trading/README.md)) provides additional portfolio simulation.
- **Authority Boundary:** Paper is not live. Paper results are not predictors of live results. Paper-vs-live drift is expected and must be quantified.
- **Primary Source:** [`services/execution/README.md`](../../services/execution/README.md)

### Shadow (Eventflow context)
- **Definition:** An offline validation mode where replay output is compared against paper reference windows to quantify drift.
- **CDB Context:** Shadow comparison is part of the ARVP pipeline. Shadow evidence helps calibrate the simulator and identify gaps between replay and paper execution.
- **Authority Boundary:** Shadow is validation, not approval. Shadow evidence does not authorize any operational change.
- **Primary Source:** [`core/replay/shadow_compare.py`](../../core/replay/shadow_compare.py)

## Validation and evidence terms

### ARVP
- **Definition:** Automated Replay Validation Pipeline — CDB's primary offline validation mechanism.
- **CDB Context:** From dataset acquisition through deterministic replay, replay-vs-paper comparison, calibration, regime scorecards, to the ARVP Gate verdict. ARVP produces evidence, not approvals.
- **Authority Boundary:** ARVP evidence is validation, not release authorization. A passing ARVP gate does not authorize paper promotion, live trading, or any operational change.
- **Primary Source:** [`core/replay/README.md`](../../core/replay/README.md), [`services/validation/README.md`](../../services/validation/README.md)

### Replay
- **Definition:** Deterministic offline execution of a strategy against historical data.
- **CDB Context:** Replay uses historical candles, a deterministic scheduler, and the strategy's own logic. It does not touch Redis, live services, or any runtime component.
- **Authority Boundary:** Replay is offline validation. Results are not directly comparable to paper or live without further calibration.
- **Primary Source:** [`core/replay/deterministic_loop.py`](../../core/replay/deterministic_loop.py)

### Replay-vs-Paper
- **Definition:** Comparison of replay output against a paper reference window to quantify simulator drift.
- **CDB Context:** Produces shadow_comparison.json, calibration reports, and regime scorecards. If drift exceeds thresholds, the ARVP gate blocks.
- **Authority Boundary:** The comparison reveals drift. It does not determine operational readiness.
- **Primary Source:** [`core/replay/replay_vs_paper_compare.py`](../../core/replay/replay_vs_paper_compare.py)

### Regime Scorecard
- **Definition:** Regime-segmented reading surface for replay and comparison outputs.
- **CDB Context:** Shows how a strategy performed in different market regimes (bull, bear, range, volatile). Reporting only, no policy semantics.
- **Authority Boundary:** Scorecards are informational. They do not trigger any action or gate.
- **Primary Source:** [`core/replay/arvp_regime_scorecards.py`](../../core/replay/arvp_regime_scorecards.py)

### Mock
- **Definition:** A test execution mode with pre-determined outcomes, used in unit/integration tests.
- **CDB Context:** Mock is for CI and local testing, not for runtime operation. It bypasses real exchange adapters and simulates predictable results.
- **Authority Boundary:** Mock must never be used in production or near-production contexts.
- **Primary Source:** Test fixtures in [`tests/README.md`](../../tests/README.md)

### Dry Run
- **Definition:** A mode that logs what would happen without actually executing.
- **CDB Context:** Used by operator CLIs (e.g., `paper_runtime_stimulus_runner.py --dry-run-preview`) to preview effects without side effects.
- **Authority Boundary:** Dry runs produce logs only. No state mutation, no persistence.
- **Primary Source:** [`services/validation/paper_runtime_stimulus_runner.py`](../../services/validation/paper_runtime_stimulus_runner.py)

### Micro-Live
- **Definition:** Heavily restricted live trading with minimal capital, tight risk limits, and explicit human gates.
- **CDB Context:** A future state after LR gates are cleared. Requires separate LR gate clearance, human approval, and cleared LR-SSOT.
- **Authority Boundary:** Micro-Live is not currently active. No service, agent, or configuration can enable it without the full LR process.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Micro-Live Candidate
- **Definition:** A candidate that has passed all validation gates including PAPER_VALIDATED and is eligible for micro-live evaluation.
- **CDB Context:** The furthest active state in the Candidate Lifecycle. Requires explicit LR gate clearance and human approval before any live exposure.
- **Authority Boundary:** Being a MICRO_LIVE_CANDIDATE does not imply live trading. LR gates and human approval are still required.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Evidence
- **Definition:** Reproducible, deterministic, fingerprintable artifacts that support or refute a claim.
- **CDB Context:** Evidence is required for every state transition in the Candidate Lifecycle. ARVP produces evidence; it does not produce approvals.
- **Authority Boundary:** Evidence supports decisions. It does not make decisions. Human interpretation is required for any promotion or gate transition.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Evidence Packet
- **Definition:** A structured bundle of evidence artifacts for a specific candidate or decision.
- **CDB Context:** Contains dataset fingerprints, replay reports, comparison results, calibration reports, and operator notes. Consumed by gates and human reviewers.
- **Authority Boundary:** An evidence packet presents facts. It does not contain or imply approvals.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md`](../../docs/strategy/CDB_PROFITABILITY_CANDIDATE_CONTRACT_V1.md)

### Ledger
- **Definition:** An append-only record of events. In CDB, the correlation_ledger in PostgreSQL.
- **CDB Context:** Every SIGNAL, DECISION, ORDER, and FILL is recorded. The ledger is the audit foundation for all replay and comparison workflows.
- **Authority Boundary:** Append-only and immutable. The ledger records what happened; it does not authorize what should happen.
- **Primary Source:** [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)

## Profitability engine terms

### Candidate
- **Definition:** A strategy idea that has entered the formal lifecycle and is being evaluated through evidence gates.
- **CDB Context:** A candidate progresses through states (IDEA → SPECIFIED → BACKTESTED → ARVP_VALIDATED → STRESS_TESTED → PAPER_CANDIDATE → PAPER_VALIDATED → MICRO_LIVE_CANDIDATE) or enters terminal states (REJECTED, PARKED, UNSAFE, SUPERSEDED, STALE).
- **Authority Boundary:** A candidate is a validation entity, not a trading entity. No candidate state implies trading authorization.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Candidate Factory
- **Definition:** The conceptual process of creating and evaluating strategy candidates through the lifecycle.
- **CDB Context:** The factory produces candidates, not trades. It is a governance framework, not a runtime system.
- **Authority Boundary:** The Candidate Factory has no runtime authority. It does not interact with Risk, Execution, or any trading service.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Strategy League Table
- **Definition:** A ranked list of candidates based on evidence and performance metrics.
- **CDB Context:** The League Table recommends candidates for further validation. It does not authorize any candidate to trade.
- **Authority Boundary:** The League Table is advisory. Ranking alone does not entitle a candidate to promotion or live exposure.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Execution Economics
- **Definition:** The analysis of net trading costs including fees, spread, slippage, rejections, and latency.
- **CDB Context:** Gross returns are not sufficient. Net economics determine whether a candidate is viable. Evidence must account for all friction costs.
- **Authority Boundary:** Execution Economics is a validation input. It does not change runtime behavior.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Capital Sleeves
- **Definition:** Future concept for allocating capital to validated strategies under separate risk and LR gates.
- **CDB Context:** Not yet implemented. Capital Sleeves will require their own contracts, gates, and human approvals before touching Risk or Allocation code.
- **Authority Boundary:** Capital Sleeves are a planning concept. No code, no DB, no runtime impact.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Profitability Engine
- **Definition:** CDB's strategy validation and evidence framework. A candidate pipeline from idea to micro-live.
- **CDB Context:** The Profitability Engine sits above the core. It uses ARVP, Evidence Packets, and the Candidate Lifecycle to validate strategies without touching runtime services.
- **Authority Boundary:** The Profitability Engine is a governance and validation layer. It has no runtime authority.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### PARKED
- **Definition:** A candidate lifecycle terminal state. The candidate is valid but not actively pursued.
- **CDB Context:** Used when a candidate passes current gates but lacks resources, data, or priority to advance. Can be reactivated later.
- **Authority Boundary:** PARKED is a holding state. No active delivery steps.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### UNSAFE
- **Definition:** A candidate lifecycle terminal state. The candidate violates risk, data, or safety boundaries.
- **CDB Context:** A candidate marked UNSAFE cannot be promoted and must not be considered for any execution path.
- **Authority Boundary:** UNSAFE is final. Re-evaluation requires a full restart from IDEA.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Core
- **Definition:** CDB's protected runtime layer: Signal, Risk, Execution, DB Writer, KillSwitch, Circuit Breaker, LR-SSOT.
- **CDB Context:** The Core is not an experimentation surface. No-touch-core principle protects the runtime from strategy experiments or governance changes.
- **Authority Boundary:** No Profitability Engine or validation component may modify Core services.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### No-Touch-Core
- **Definition:** The principle that the core runtime services are off-limits to any strategy, evidence, or profitability changes.
- **CDB Context:** Protects the stability and determinism of the trading pipeline. Changes to Core require separate process and authorization.
- **Authority Boundary:** Absolute. No exception without explicit governance change.
- **Primary Source:** [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)

### Risk Gate
- **Definition:** The mandatory check every signal must pass before execution. Enforced by cdb_risk.
- **CDB Context:** Checks market state freshness, exposure limits, drawdown caps, circuit breaker state, and kill switch status. Blocked decisions are system protection.
- **Authority Boundary:** Risk gates are non-negotiable. No bypass possible for any reason.
- **Primary Source:** [`services/risk/README.md`](../../services/risk/README.md)

### Kill Switch
- **Definition:** A manual/admin override that instantly blocks all order flow.
- **CDB Context:** Overrides all other risk checks. Engaged by operator or automated admin. Persisted and observable.
- **Authority Boundary:** Kill Switch is final until explicitly disengaged by an authorized operator.
- **Primary Source:** [`services/risk/README.md`](../../services/risk/README.md)

### Circuit Breaker
- **Definition:** An automatic safety mechanism that trips when configurable thresholds are exceeded.
- **CDB Context:** Trips on consecutive losses, volatility spikes, or other configured conditions. Requires explicit intervention to reset.
- **Authority Boundary:** Circuit Breaker is automatic. No service can prevent it from tripping when thresholds are met.
- **Primary Source:** [`services/risk/README.md`](../../services/risk/README.md)

## Agent / repo workflow terms

### CURRENT_STATUS.md
- **Definition:** Repo/engineering status ledger. Tracks open PRs, recent main merges, and working status.
- **CDB Context:** This is a ledger, not a live mirror. GitHub live state and repo live state override Current Status claims.
- **Authority Boundary:** Read for orientation. Never treat as SSOT for LR, Board stage, or live state.
- **Primary Source:** [`CURRENT_STATUS.md`](../../CURRENT_STATUS.md)

### PROJECT_STATUS.md (historical snapshot)
- **Definition:** Historical project status snapshot. Not the current overall status.
- **CDB Context:** A retained reference, not an active status surface. Use [CONTROL_REGISTER.md](../../docs/runbooks/CONTROL_REGISTER.md) and [CURRENT_STATUS.md](../../CURRENT_STATUS.md) for current state.
- **Authority Boundary:** Historical reference only. Not authoritative.
- **Primary Source:** [snapshot file](../../PROJECT_STATUS.md) (historical snapshot)

### Control Register
- **Definition:** The current Board stage, operating focus, and control surface for the CDB project.
- **CDB Context:** Documented in [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md). Currently `stage:trade-capable`. Orthogonal to the LR system.
- **Authority Boundary:** The Control Register is the SSOT for Board stage and operating focus. It is not an LR gate.
- **Primary Source:** [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)

### Bootloader
- **Definition:** The required initial read-order file (AGENTS.md -> agents/AGENTS.md) that every agent must resolve before starting work.
- **CDB Context:** The bootloader establishes the governance context, read order, and safety boundaries for any session.
- **Authority Boundary:** Mandatory. No implementation work before bootloader resolution.
- **Primary Source:** [`AGENTS.md`](../../AGENTS.md)

### Read Order
- **Definition:** The ordered list of files an agent must read before planning or implementation.
- **CDB Context:** Defined in [`agents/AGENTS.md`](../../agents/AGENTS.md). Varies by task scope. Always includes governance, architecture, and status files.
- **Authority Boundary:** Reading the Read Order is a precondition for any write action.
- **Primary Source:** [`agents/AGENTS.md`](../../agents/AGENTS.md)

### Brain Evidence
- **Definition:** A structured evidence block that agents must output before planning for strategy/runtime/module/service/contract/context scope.
- **CDB Context:** Documents the agent's context sources, confidence level, and any fallback to repo-only mode.
- **Authority Boundary:** Required for defined scopes. The block itself does not authorize action.
- **Primary Source:** [`agents/AGENTS.md`](../../agents/AGENTS.md)

### Repo Brain
- **Definition:** The collective context and navigation intelligence stored in the repo's canonical files and agent registry.
- **CDB Context:** The Repo Brain is the fallback context source when SurrealDB-backed memory is unavailable.
- **Authority Boundary:** Repo files are truth. Brain is orientation.
- **Primary Source:** [`agents/AGENTS.md`](../../agents/AGENTS.md)

### Context Intelligence
- **Definition:** The system of MCP tools, SurrealDB-backed memory, and context assembly that provides agents with verified session context.
- **CDB Context:** Currently available as local MCP tools. SurrealDB-backed productive memory is not yet activated.
- **Authority Boundary:** Context Intelligence improves agent accuracy. It does not replace repo live truth or GitHub live state.
- **Primary Source:** [`docs/surrealdb/README.md`](../../docs/surrealdb/README.md)

### SurrealDB
- **Definition:** The planned database backend for agent memory, context, and decision records.
- **CDB Context:** SurrealDB is not yet activated for productive memory. All context assembly currently uses in-memory and repo-only fallback.
- **Authority Boundary:** No SurrealDB write or productive memory activation without explicit gates.
- **Primary Source:** [`docs/surrealdb/README.md`](../../docs/surrealdb/README.md)

### MCP
- **Definition:** Model Context Protocol — a protocol for providing tools and context to AI agents.
- **CDB Context:** CDB uses MCP tools for context intelligence (context search, briefing, evidence, decisions, etc.). MCP tools are read-only by default.
- **Authority Boundary:** MCP tools are read-only unless explicitly authorized for write operations.
- **Primary Source:** [`agents/AGENTS.md`](../../agents/AGENTS.md)

### Agent
- **Definition:** An AI coding agent (Claude, Codex, Gemini, etc.) operating on the CDB repo.
- **CDB Context:** Agents must follow the bootloader, read order, governance policies, and single-writer locks. Agents are never authorized for live-trading or LR decisions.
- **Authority Boundary:** Agents act within human-granted scope. No agent can authorize Live-Go, Echtgeld-Go, or bypass Risk/KillSwitch.
- **Primary Source:** [`agents/AGENTS.md`](../../agents/AGENTS.md), [`knowledge/governance/CDB_AGENT_POLICY.md`](../../knowledge/governance/CDB_AGENT_POLICY.md)

### Sub-Agent
- **Definition:** A helper agent invoked by a primary agent for specialized tasks.
- **CDB Context:** Sub-agents have restricted tool access and operate under a shared contract ([`_CDB_SUBAGENT_CONTRACT.md`](../../.cursor/agents/_CDB_SUBAGENT_CONTRACT.md)).
- **Authority Boundary:** Sub-agents cannot create PRs, modify governance, or make independent scope decisions.
- **Primary Source:** [`agents/AGENTS.md`](../../agents/AGENTS.md)

### PR LOCK
- **Definition:** A paired single-writer lock on Issue and assigned PR. Before a new PR, an Issue reservation uses `batch_pr=pending`; after creation both sides must contain the identical `LOCK:` event.
- **CDB Context:** Defined in [CDB_AGENT_POLICY.md](../../knowledge/governance/CDB_AGENT_POLICY.md) section 4. A missing, stale, foreign, malformed, or one-sided pair is fail-closed.
- **Authority Boundary:** `PARTIAL_LOCK` blocks writes. Handoff/release requires matching paired `UNLOCK` events; stale locks are never taken over automatically.
- **Primary Source:** [`knowledge/governance/CDB_AGENT_POLICY.md`](../../knowledge/governance/CDB_AGENT_POLICY.md)

### Required Checks
- **Definition:** The branch-protection-enforced status checks that must pass before a PR can merge.
- **CDB Context:** Seit Migration #4540 sind auf `main` genau zwei hosted Required Checks merge-relevant: `ci (Unit/Integration + Lint gesammelt)` (Hosted GitHub Actions Check Run) und `policy-gate` — beide exakter PR head SHA, `strict: true`, kein festes `app_id`. `cdb-local-ci` (lokaler Fast-CI-Publisher) ist seit #4540 **kein** Required Context mehr, sondern nur noch optionaler Preflight/Diagnose. Verify live with `gh api`, not this glossary entry.
- **Authority Boundary:** Required checks are enforced by branch protection. No merge bypass possible; `--admin` is never a substitute for a missing/red hosted Required Check.
- **Primary Source:** [`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md)

### policy-gate
- **Definition:** A Hosted GitHub Actions workflow that validates PR compliance with CDB governance policies.
- **CDB Context:** Runs on every PR. Since migration #4540 it is one of the two branch-protection-required merge contexts on `main` (together with `ci (Unit/Integration + Lint gesammelt)`).
- **Authority Boundary:** `policy-gate` findings should be treated as a hard local gate before merge; a green hosted `policy-gate` Check Run on the exact head is a branch-protection-required merge condition.
- **Primary Source:** [`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md)

### CI
- **Definition:** Continuous Integration. Automated test and validation pipeline running on every PR.
- **CDB Context:** Hosted Actions `ci.yml` runs unit tests, integration tests, lint (ruff), publishes the required Check Run `ci (Unit/Integration + Lint gesammelt)` on `ubuntu-latest`. Local Fast-CI (`ci/`) remains an optional developer-preflight mirror (`cdb-local-ci`) that is not merge-required since #4540.
- **Authority Boundary:** The hosted Required Checks are the pre-merge gate. They validate code quality, not operational readiness.
- **Primary Source:** [`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md)

## Safety boundaries

- **This glossary defines terms. It does not define new policies.**
- No definition in this glossary creates a Live-Go, Echtgeld-Go, or authority bypass.
- No definition weakens existing LR, Risk, Execution, or governance rules.
- Board stage `trade-capable` is not Live-Go — this is reinforced in every relevant definition.
- LR remains NO-GO. No Echtgeld-Go.

## Sources

- [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md)
- [`services/README.md`](../../services/README.md)
- [`docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md`](../../docs/strategy/CDB_PROFITABILITY_ENGINE_CANON.md)
- [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- [`docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)
- [`docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`](DEVELOPER_VISUAL_START_HERE.md)
- [`docs/onboarding/core-eventflows/README.md`](core-eventflows/README.md)
- [`knowledge/governance/CDB_AGENT_POLICY.md`](../../knowledge/governance/CDB_AGENT_POLICY.md)
- [`docs/surrealdb/README.md`](../../docs/surrealdb/README.md)
- [`core/replay/README.md`](../../core/replay/README.md)
- [`services/risk/README.md`](../../services/risk/README.md)
