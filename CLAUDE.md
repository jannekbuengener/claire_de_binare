# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Governance & Session Rules

The authoritative role definition for Claude is at `agents/roles/CLAUDE.md`. Read it at session start.

**Mandatory session-start read order:**
1. `agents/roles/CLAUDE.md` (role + governance)
2. `agents/AGENTS.md` (agent registry)
3. `knowledge/governance/CDB_CONSTITUTION.md`
4. `knowledge/governance/CDB_GOVERNANCE.md`
5. `knowledge/governance/CDB_AGENT_POLICY.md`
6. `knowledge/governance/SYSTEM_INVARIANTS.md`
7. `docs/meta/REPOSITORY_CANON.md`
8. `CURRENT_STATUS.md` (current repo/engineering status)
9. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (Go/No-Go verdict)
10. `docs/runbooks/CONTROL_REGISTER.md` (board/stage focus)
11. `agents/OPEN_CODE_AGENTS.md`

**Live-Readiness: NO-GO** — no real trades without explicit human gate. See `docs/live-readiness/`.
**Control Board Stage:** `trade-capable` (ratified 2026-04-08) — orthogonal to LR `NO-GO`; no live capital, no Grafana gate, no strategy validation.

**Session-Boundary Skills (Pflicht, fail-closed):** Lesen und anwenden — kein Überspringen.
- **Vor** jeder Repo-/GitHub-/Planungs-/Implementierungsarbeit:
  - Codex: `.codex/cdb_skills/cdb-session-start/SKILL.md`
  - Cursor: `.cursor/skills/cdb-session-start/SKILL.md`
- **Vor** Plan-Finalisierung, Branch-, Worktree- oder PR-Erstellung:
  - `python -m tools.pr_routing route --issue <ISSUE>`
  - Skill: `docs/skills/cdb-pr-router/SKILL.md`
  - Skill: `docs/skills/cdb-pr-completeness-review/SKILL.md` (before MERGE_CANDIDATE)
  - Skill: `docs/skills/cdb-batch-merge-conductor/SKILL.md` (Final-Head Preparation → `FINAL_HEAD_READY_FOR_APPROVAL`; no merge)
- **Nach** Implementierung/Validierung/Repo-Arbeit, vor Abschluss:
  - Codex: `.codex/cdb_skills/cdb-session-close/SKILL.md`
  - Cursor: `.cursor/skills/cdb-session-close/SKILL.md`

**Session-Ende (Pflicht):** Session-Log unter `knowledge/logs/sessions/YYYY-MM-DD-<topic>.md` ablegen. `CURRENT_STATUS.md` aktualisieren wenn sich Repo-/Engineering-Status geändert hat.

**PR-Flow v1:** Normale Sessions liefern targeted-validierte Slices in den
gerouteten PR und enden mit `DONE_SLICE_ADDED_TO_BATCH_PR`. Full Fast-CI,
hosted Required Checks, Merge und Issue-Closure gelten nur für einen
eingefrorenen finalen `merge_candidate`.

---

## Commands

### Tests

```bash
# CI (mocks, no containers needed)
pytest -q -k "not test_mcp_time_server_runtime"   # what CI runs
make test                                           # unit + integration
make test-unit                                      # pytest -m unit
make test-integration                               # pytest -m "integration and not e2e and not local_only"
make test-coverage                                  # 80% threshold, html report

# Single test
pytest tests/path/to/test_file.py::test_function_name -v

# E2E / local (requires running containers)
make test-e2e          # pytest -m e2e
make test-local        # pytest -m local_only
make test-local-chaos  # DESTRUCTIVE — kills containers
```

Test markers: `unit`, `integration`, `e2e`, `local_only`, `slow`, `chaos`, `contract`, `smoke`, `load`.
E2E and `local_only` tests are excluded from CI by default.

### Lint & Format

```bash
ruff check .                        # linter (CI-required)
black --config pyproject.toml .     # formatter (CI checks changed .py files only)
```

Config: `pyproject.toml` — Python 3.12, line-length 88. `services/ws/mexc_proto_gen/` is excluded from both.

### Stack (Runtime)

```bash
# One-time network setup
docker network create cdb_network

# Start BLUE (core, always-on) + RED (signal + monitoring)
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# Or via Makefile
make docker-up          # starts BLUE + RED
make docker-health      # check health of all containers
make docker-down        # stop both stacks

# PowerShell v1 front door (Windows canonical)
.\tools\cdb.ps1 secrets init
.\tools\cdb.ps1 runtime up
.\tools\cdb.ps1 stack verify
.\tools\cdb.ps1 runtime smoke
.\tools\cdb.ps1 service logs -ServiceName cdb_risk -Lines 100
```

### CI Lab Baseline (Docker, isolated)

```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/test.yml up --abort-on-container-exit
```

This is the canonical 431B baseline for isolated test/E2E labs — distinct from the BLUE+RED operator runtime.

### Ops

```bash
make systemcheck         # pre-flight checks before paper trading
make paper-trading-start # requires running stack
make paper-trading-logs  # live logs of paper-trading runner
make paper-trading-stop
make daily-check
make backup              # Postgres + Redis to F:\Claire_Backups
make security-scan       # gitleaks + ruff + bandit
make pre-close           # pre-close sweep (untracked artefacts)
make mcp-config-validate # validate MCP configuration
```

---

## Architecture

### BLUE/RED Stack Split

The runtime is split into two Docker Compose stacks sharing `cdb_network`:

**BLUE** (`compose.blue.yml`) — core, always-on, must run for trading:
- `cdb_postgres` (port 5432) + `cdb_redis` (port 6379) — data layer
- `cdb_market` (8009) — owns `market_state:{symbol}` in Redis (post-cutover, Issue #1201)
- `cdb_candles` (8007) — aggregates ticks into 1-min candles on `stream.candles_1m`
- `cdb_regime` (8008) — reads candles, classifies market regime (ADX/ATR-based)
- `cdb_allocation` (8006) — maps regime to allocation percentage per mode
- `cdb_risk` (8002) — central gate: blocks orders if `allocation_pct <= 0`; holds kill-switch
- `cdb_execution` (8003) — submits orders; `MOCK_TRADING=true` by default
- `cdb_db_writer` — persists Redis stream events to Postgres
- `cdb_paper_runner` (8004) — 14-day paper trading runner

**RED** (`compose.red.yml`) — optional, restartable without affecting BLUE:
- `cdb_ws` (8000) — WebSocket feed from MEXC (protobuf)
- `cdb_signal` — consumes candles/regime, generates trade signals
- Prometheus + Grafana (port 3000) + exporters + report service

### Data Flow

```
cdb_ws → Redis pub/sub (market_data) → cdb_market (market_state)
                                      → cdb_candles (stream.candles_1m)
                                           → cdb_regime
                                                → cdb_allocation
cdb_signal → signals → cdb_risk → orders → cdb_execution → MEXC API
                                      → cdb_db_writer → Postgres
```

### Core Library (`core/`)

Shared domain code imported by all services:

| Package | Purpose |
|---|---|
| `core/domain/` | Domain models (`models.py`), events (`event.py`), secrets |
| `core/clients/` | MEXC REST API client |
| `core/indicators/` | Technical indicators (trend, momentum, volatility, composite) |
| `core/safety/` | Kill-switch (`kill_switch.py`) |
| `core/contracts/` | `decision_contract_v1.py` — TRACE_CONTRACT_V1 envelope validation |
| `core/replay/` | Canonical JSON, envelopes, publisher for replay/shadow mode |
| `core/utils/` | Redis client, Postgres client, rate limiter, clock, UUID gen |
| `core/config/` | Feature flags, trading mode |

### Secrets

Secrets are Docker secrets loaded from `~/Documents/.secrets/.cdb/` (not env vars). The `SECRETS_PATH` env var overrides the default path. Services read them via `/run/secrets/<name>` at startup.

### Kill-Switch

Shared state file at `/app/kill_switch/.cdb_kill_switch.state` (Docker volume `kill_switch_state`). Both `cdb_risk` and `cdb_execution` mount this volume. The path is set via `CDB_KILL_SWITCH_STATE_FILE`.

### Test Structure

```
tests/
  unit/          # -m unit, fast, no containers
  integration/   # -m integration, mocked services
  e2e/           # -m e2e, requires running BLUE stack
  local/         # -m local_only, destructive/stress tests
  fixtures/      # shared fixtures + mcp_smoke_config.json
  conftest.py
```

Coverage target: 80% on `core/` and `services/` (enforced by `make test-coverage`). Default `pytest` run has no coverage to avoid false failures.

### CI / Branch Protection

- Required merge contexts (SSOT: `docs/runbooks/merge_policy_ci_gate.md`, verify live via `gh api`): hosted Check Runs `ci (Unit/Integration + Lint gesammelt)` and `policy-gate` (exact PR head SHA) — the only branch-protection-required contexts on `main` since #4540.
- `cdb-local-ci` (local Fast-CI publisher) is seit #4540 kein Required Context mehr; optionaler lokaler Preflight/Diagnose nur.
- `policy-gate` categorizes PRs; core/service PRs need label `allow-core-change` or `manual-approval`
- `strict: true` — branch must be up-to-date with main before merge
- Bot review threads (Sourcery, Copilot) must be resolved before merge
- Runner: `ci.yml` runs on `ubuntu-latest` (GitHub-hosted); self-hosted runners decommissioned from active CI per #3575; historical labels defined in `infrastructure/actions-runner/`
- Autonomous squash merge is capability-based (see `.cursor/rules/CDB-Checks-and-Merge-Rule.mdc`): allowed once the hosted Required Checks (`ci (Unit/Integration + Lint gesammelt)`, `policy-gate`) are SUCCESS live on the exact PR head SHA; `--admin` is never a substitute for a missing/red required status.

### Key Governance Files

- `knowledge/governance/CDB_CONSTITUTION.md` — top-level rules
- `knowledge/governance/CDB_GOVERNANCE.md`
- `knowledge/governance/SYSTEM_INVARIANTS.md` — invariants that must never be violated
- `docs/live-readiness/` — LR-STATE.yaml files + evidence per phase (P0–P5)
- `knowledge/logs/sessions/` — session evidence logs
- `docs/navigation/mcp-navpack/` — MCP navigation presets (ENTRYPOINTS.yaml, CHEATSHEET.md)

### Service Conventions

All services under `services/` follow the same layout: `service.py`, `config.py`, `models.py`, `Dockerfile`, `requirements.txt`. The canonical entry point is:

```bash
python -m services.<name>.service
```

Logging is configured via `LOG_LEVEL` env var (or `logging_config.json` if present in the service dir).

### Determinism & Audit Trail

**No-float rule:** All monetary values must use `Decimal` with fixed quantization. `core/contracts/decision_contract_v1.py` defines `_MONEY_Q`, `_RATIO_Q`, `_QTY_Q` and enforces this via `_to_decimal()`. Never use `float` on the order path.

**TRACE_CONTRACT_V1:** Use `build_decision_contract_v1_bundle` / `verify_decision_contract_v1_bundle` from `core/contracts/decision_contract_v1.py` to hash inputs and outputs for audit. Raise `DecisionContractError` on violation.

**Envelope chain:** Shadow/replay produces a linked chain `DecisionEnvelopeV1 → OrderEnvelopeV1 → FillEnvelopeV1` (see `core/replay/envelopes.py`). `core/replay/canonical_json.py` provides sorted-key JSON serialization for deterministic hashes.

### Agent SDK (retired)

The standalone `cdb_agent_sdk/` package was removed from the Claire de Binare repository in PR #2994. Use the repo-local skill packs under `.codex/cdb_skills/` and `.opencode/skills/` instead. Historical notes remain in `knowledge/systems/SDK_OVERVIEW.md` (marked retired).

### MINGW64 / Git Bash (Windows)

`/var/run/docker.sock` gets path-converted. Prefix Docker commands with Linux paths with `MSYS_NO_PATHCONV=1`.
