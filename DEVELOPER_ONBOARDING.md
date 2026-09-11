# Developer Onboarding Guide

**Welcome to Claire de Binare!**

This guide helps you set up a local development environment from scratch. It is
Windows/PowerShell-first but also covers Linux/macOS and CI-only workflows.

For repo-wide PowerShell discovery, use [`tools/README.md`](tools/README.md). On
Windows, use `.\tools\cdb.ps1` as the canonical PowerShell v1 front door. This
guide mirrors the canonical v1 entrypoints where they are directly needed.

---

## Table of Contents

1. [Orientierung](#orientierung)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Environment Configuration](#environment-configuration)
5. [Secrets Management](#secrets-management)
6. [Quick Verification](#quick-verification)
7. [Development Workflow](#development-workflow)
8. [Running the Stack (Optional)](#running-the-stack-optional)
9. [Troubleshooting](#troubleshooting)
10. [Next Steps](#next-steps)
11. [Quick Reference](#quick-reference)

---

## Orientierung

Bevor du Code auscheckst, lies die aktuelle Projektlage:

| Surface | Zweck |
|---------|-------|
| [`README.md`](README.md) | GitHub-Landingpage; aktueller Status und Navigation |
| [`docs/index.md`](docs/index.md) | Kuerzester aktiver Docs-Einstieg |
| [`docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`](docs/onboarding/DEVELOPER_VISUAL_START_HERE.md) | Visueller Developer-Start (Mermaid-Flow, Beispiele, Vorlagen) |
| [`docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md`](docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md) | Kanonischer Fresh-Agent Safe-Work Drill Contract (Definition, nicht Ausfuehrung) |
| [`docs/onboarding/first_issue_sandbox.md`](docs/onboarding/first_issue_sandbox.md) | Gefuehrter Rehearsal-Pfad fuer den ersten sicheren Issue-to-PR-Workflow |
| [`docs/onboarding/fresh_clone_rehearsal.md`](docs/onboarding/fresh_clone_rehearsal.md) | Read-only-by-default Fresh-Clone-Pfad bis zur ersten Grundsicherheit |
| [`AGENTS.md`](AGENTS.md) | Root-Pointer -> [`agents/AGENTS.md`](agents/AGENTS.md) (Agenten-Read-Order) |
| [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) | SSOT fuer Echtgeld Go/No-Go (**NO-GO**) |
| [`docs/runbooks/CONTROL_REGISTER.md`](docs/runbooks/CONTROL_REGISTER.md) | Board-Stage und operativer Fokus |
| [`CURRENT_STATUS.md`](CURRENT_STATUS.md) | Repo-/Engineering-Ledger (keine Live-Wahrheit) |
| [`docs/onboarding/cdb_glossary.md`](docs/onboarding/cdb_glossary.md) | CDB-Terminologie-Referenz fuer alle Onboarding-Flaechen |
| [`docs/surrealdb/README.md`](docs/surrealdb/README.md) | Context-/MCP-Docs-Index und Repo-Brain-Einstieg |

Wichtige Statusregeln:
- **LR bleibt NO-GO.** Board-Stage `trade-capable` ist kein Live-Go.
- Kein Echtgeld-Go ohne explizite Human-Freigabe.
- `CURRENT_STATUS.md` ist ein Ledger, nicht Live-Wahrheit.
- GitHub live und Repo live fuehren.
- `PROJECT_STATUS.md` und `knowledge/CURRENT_STATUS.md` sind historische Snapshots.

---

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **Git** | 2.30+ | Version control | [Install Git](https://git-scm.com/downloads) |
| **Python** | 3.12+ | Service development | [Install Python](https://www.python.org/downloads/) |
| **Docker** | 20.10+ | Container runtime (optional for CI-only) | [Install Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.0+ | Multi-container orchestration | Included with Docker Desktop |

### Optional Tools (Recommended)

| Tool | Purpose | Installation |
|------|---------|--------------|
| **PowerShell 7+** | Primary shell on Windows | [Install PowerShell](https://learn.microsoft.com/en-us/powershell/) |
| **Make** | Build automation (included on Linux/Mac) | [GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm) for Windows |
| **gh CLI** | GitHub CLI for PR/Issue workflow | [Install gh](https://cli.github.com/) |
| **Ruff** | Python linter (installed via requirements-dev.txt) | `pip install ruff` |

### System Requirements

- **RAM**: 8GB minimum, 16GB recommended (16GB required for full BLUE+RED stack)
- **Disk Space**: 10GB free space (without full stack), 20GB (with Docker images)
- **OS**: Windows 10/11, macOS 11+, or Linux (Ubuntu 22.04+)

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/jannekbuengener/Claire_de_Binare.git
cd Claire_de_Binare
```

### 2. Verify Prerequisites

**PowerShell (Windows)**:
```powershell
pwsh --version
python --version
git --version
docker --version
docker compose version
```

**Bash (Linux/Mac)**:
```bash
python3 --version
git --version
docker --version
docker compose version
```

If any command fails, install the missing prerequisite before continuing.

### 3. Create Python Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

Install the same Python dependency layers as CI (`.github/workflows/ci.yml`):

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-mcp.txt
```

`requirements.txt` covers runtime/test conveniences (for example `numpy`,
`prometheus_client`). `requirements-dev.txt` covers linting and dev tooling.
`requirements-mcp.txt` is required for pytest collection of MCP-related unit
tests; without it, the canonical quick-test command below fails with
`ModuleNotFoundError: mcp`.

---

## Environment Configuration

### 1. Create .env File

```bash
cp .env.example .env
```

### 2. Review .env Configuration

Open `.env` in your editor and review the default values. Key settings:

```
# Secrets path (REQUIRED)
SECRETS_PATH=${HOME}/Documents/.secrets/.cdb  # Linux/Mac
# SECRETS_PATH=C:\Users\<username>\Documents\.secrets\.cdb  # Windows

# Safety settings (CRITICAL)
MEXC_TESTNET=true          # Always true for development
MOCK_TRADING=true          # Use mock executor (no real trades)
DRY_RUN=true               # Log trades without executing
SIGNAL_STRATEGY_ID=paper   # Paper trading mode
```

Never set `MEXC_TESTNET=false` or `SIGNAL_STRATEGY_ID=live` in development.

### 3. Update SECRETS_PATH (if needed)

**Windows**:
```powershell
SECRETS_PATH=C:\Users\YourUsername\Documents\.secrets\.cdb
```

**Linux/Mac**:
```bash
SECRETS_PATH=${HOME}/Documents/.secrets/.cdb
```

---

## Secrets Management

CDB uses a **filesystem-based secrets directory** (`SECRETS_PATH`). All secrets
are read by Docker Compose at runtime. The secrets directory path is never
committed to Git.

### 1. Initialize Secrets

**Windows (PowerShell v1 Front Door)**:
```powershell
.\tools\cdb.ps1 secrets init
```

**Linux/Mac**:
```bash
chmod +x infrastructure/scripts/init-secrets.sh
./infrastructure/scripts/init-secrets.sh
```

The init script generates placeholder secrets for local development:
- `REDIS_PASSWORD` - Redis authentication
- `POSTGRES_PASSWORD` - PostgreSQL database password
- `GRAFANA_PASSWORD` - Grafana admin password

### 2. Verify Secrets Created

**Windows**:
```powershell
dir $env:USERPROFILE\Documents\.secrets\.cdb\
```

**Linux/Mac**:
```bash
ls -la ~/Documents/.secrets/.cdb/
```

Verify the three files exist. For actual MEXC API keys, see team documentation.
CI and unit tests use mocked credentials; no real secrets are required for local
`make test` or `pytest` runs.

### 3. Secret Safety Rules

- Never output secret values to console, logs, or documentation.
- Use docker-compose secrets mounts instead of inline environment variables.
- CI and tests use mocked secrets; real secrets are only needed for running the
  full BLUE+RED stack with exchange connectivity.

---

## Quick Verification

Before running the full stack, verify your local setup:

### 1. Git Status

```bash
git status
git log --oneline -5
```

Ensure you are on `main` or a feature branch based on a recent `main`.

### 2. GitHub CLI

```bash
gh auth status
```

Verify you're logged in to GitHub. If not:
```bash
gh auth login
```

### 3. Python / Lint / Test Smoke

```bash
# Lint (CI-required)
ruff check .

# Quick test (no containers needed)
pytest -q -k "not test_mcp_time_server_runtime" --no-header
```

### 4. Onboarding Doctor (One-Command Preflight)

```bash
# Cross-platform Python doctor (recommended)
python -m tools.onboarding_doctor

# JSON output
python -m tools.onboarding_doctor --format json

# PowerShell v1 front door (Windows)
.\tools\cdb.ps1 onboarding doctor

# Write a Markdown evidence report
python -m tools.onboarding_doctor --report docs/evidence/local_onboarding_check.md

# Make target (all platforms)
make onboarding-doctor
```

This read-only tool validates your entire local developer setup without
requiring a running stack, Docker mutation, or secret exposure. It checks:
- Git installed and branch state
- Python version (3.11+ required)
- Docker and Docker Compose presence (optional)
- gh CLI and authentication (optional)
- `.env` file presence
- SECRETS_PATH existence (not contents)
- CI Python dependency layers (`requirements.txt`, `requirements-mcp.txt`)
- All key onboarding files exist
- `make context-doctor` reachability

It does **not** output secret values. Exit codes: 0 = all good, 1 = blocking.

The `--report PATH` option writes a Markdown evidence report including the
repo HEAD, branch, a check summary, active onboarding surfaces, and safety
boundaries. The report is only written when `--report` is explicitly set;
the default doctor run remains read-only and writes no files.

### 5. Repo Brain / Context Preflight

Before the first `make context-doctor` on a fresh clone, initialize the local
context query config:

```bash
make context-query-config-init
```

For the full context stack (optional), start local SurrealDB first:

```bash
make context-up
```

Then run the read-only preflight:

```bash
make context-doctor
```

This read-only tool validates your local context setup without requiring a
running stack. It checks:
- Secrets presence (not values)
- Python and pip dependencies
- Key file references
- No live-key or LR violations

### 5. Repo Brain / Context Intelligence

After the basic quick verification, review the dedicated Repo Brain onboarding:

```bash
# Start here for Repo Brain / Context Intelligence
# docs/onboarding/repo_brain_context_intelligence.md
```

This page covers:
- What Repo Brain / Context Intelligence is and is not
- Brain Evidence Block guide (source values, examples)
- Developer first-use flow
- Safety boundaries (LR NO-GO, no Live-Go, no Echtgeld-Go)

### 6. Docs / Onboarding Pointer Check

Verify the active start chain is accessible:

```bash
# All of these should exist
Get-Item README.md, docs/index.md, docs/onboarding/DEVELOPER_VISUAL_START_HERE.md,
         DEVELOPER_ONBOARDING.md, docs/surrealdb/README.md,
         tools/README.md, tests/README.md, services/README.md
```

---

## Development Workflow

### Running Tests

**Unit tests (fast, no containers)**:
```bash
pytest tests/unit/ -v
```

**Full CI slice (unit + integration)**:
```bash
make test
# or:
pytest -q -k "not test_mcp_time_server_runtime"
```

**With coverage**:
```bash
make test-coverage
```

**Integration tests (mocked externals)**:
```bash
pytest tests/integration/ -v
```

### Code Style

**Lint**:
```bash
ruff check .
```

**Format**:
```bash
black .
```

**Type check**:
```bash
mypy core/ services/
```

### PR / Issue Workflow

1. Run `python -m tools.pr_routing route --issue <N>` before planning, branch,
   worktree, or PR creation.
2. Reuse the routed open PR/branch; create a Draft PR only when the routing
   decision explicitly permits it.
3. Before a new PR, reserve the Issue. After PR creation, establish the
   identical Issue-/PR-level `LOCK:` pair before any write.
4. Make one scoped slice and run targeted tests, affected lint, and
   `git diff --check`.
5. Push the slice, update the PR ledger and Issue handoff, then stop with
   `DONE_SLICE_ADDED_TO_BATCH_PR`. Do not merge or close the Issue by default.
6. Only a frozen `merge_candidate` receives combined-diff review, full Fast-CI,
   hosted Required Checks, and the separate authorized merge flow.

**Required status at merge**: the hosted Required Checks
`ci (Unit/Integration + Lint gesammelt)` and `policy-gate` must be SUCCESS on
the exact final PR head. They are not required for an intermediate slice
handoff.
Scope boundaries: no runtime, Docker, live-trading, LR, or DB-write changes
without explicit issue scope.

**Important**: Neither an Issue-only status comment nor a one-sided PR lock is
sufficient. Until Issue and PR contain the identical live lock, the state is
`PARTIAL_LOCK` and writes are blocked.

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

---

## Running the Stack (Optional)

Canonical runtime: **BLUE+RED** stack. This is optional for CI-only development.

### 1. Start the Stack

**Via PowerShell v1 Front Door** (Windows, canonical):
```powershell
.\tools\cdb.ps1 runtime up
```

**Via Make** (all platforms):
```bash
make docker-up
```

**Via Compose directly**:
```bash
docker network create cdb_network 2>/dev/null || true
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### 2. Verify Stack

```powershell
.\tools\cdb.ps1 stack verify
```

Or:
```bash
make docker-health
```

### 3. Smoke Test

```powershell
.\tools\cdb.ps1 runtime smoke
```

This validates the current BLUE core flow path, not the full BLUE+RED stack
end-to-end.

### 4. Health Probes (after stack is up)

| Service | Port |
|---------|------|
| Allocation | `:8006` |
| Candles | `:8007` |
| Regime | `:8008` |
| Market | `:8009` |
| Risk | `:8002` |

### 5. View Logs

```powershell
.\tools\cdb.ps1 service logs -ServiceName cdb_risk -Follow
```

### 6. Stop the Stack

```bash
make docker-down
```

---

## Troubleshooting

### "Missing .env file"

**Solution**: Copy the template:
```bash
cp .env.example .env
```

### "Secret file not found"

**Solution**: Run the secrets init script:

**Windows**:
```powershell
.\tools\cdb.ps1 secrets init
```

**Linux/Mac**:
```bash
./infrastructure/scripts/init-secrets.sh
```

### "Port already in use"

**Solution**: Check for conflicting services:

**Windows**:
```powershell
netstat -ano | findstr :5432
netstat -ano | findstr :6379
```

**Linux/Mac**:
```bash
sudo lsof -i :5432
sudo lsof -i :6379
```

### "Cannot connect to Docker daemon"

**Solution**:
1. Ensure Docker Desktop is running
2. Check Docker service status: `docker info`
3. Restart Docker Desktop if needed

### "Service unhealthy"

**Solution**: Check service logs:
```powershell
.\tools\cdb.ps1 service logs -ServiceName <service> -Lines 100
```

Common causes: missing env variable, wrong secret, port conflict.

### "Tests fail with connection errors"

**Solution**:
1. If running unit/integration tests: ensure you have no conflicting local Redis/Postgres
2. If running E2E tests: ensure the full BLUE+RED stack is running
3. Run with verbose output: `pytest -v -s`

### "ModuleNotFoundError: mcp" during pytest

**Solution**: Install MCP test dependencies (CI does this too):
```bash
pip install -r requirements-mcp.txt
```

If other collection errors mention `numpy` or `prometheus_client`, also ensure
`requirements.txt` is installed (see [Initial Setup](#initial-setup) step 4).

### "make context-doctor fails on fresh clone"

**Solution**:
1. Run `make context-query-config-init` once
2. If you need the full context stack, run `make context-up` before
   `make context-doctor`

### "ruff check fails"

**Solution**: Ensure dev dependencies are installed:
```bash
pip install -r requirements.txt -r requirements-dev.txt -r requirements-mcp.txt
```

### Getting Help

1. **Check stack health**: `make docker-health` or `.\tools\cdb.ps1 stack verify`
2. **Review logs**: `.\tools\cdb.ps1 service logs -ServiceName <service>`
3. **Search existing issues**: [GitHub Issues](https://github.com/jannekbuengener/Claire_de_Binare/issues)
4. **Ask for help**: Open a new issue with your OS, error message, and steps to reproduce

---

## Next Steps

### Final Restart / Tool Reload Required

**After completing setup and onboarding, you MUST restart your current tool.**

1. Close your current tool: Cursor, OpenCode, Claude Code / Codex, Terminal/Shell, PowerShell, IDE
2. Reopen it / start a new session
3. Only then continue with CDB work

**Why:** Env (PATH, venv), MCP configuration, secrets (SECRETS_PATH), and agent/skill
definitions may have changed during onboarding. Sessions started before onboarding
can have stale caches. Without a restart:
- new MCP/agent configuration may not be loaded
- new PATH/Env values may not take effect
- new Cursor/OpenCode agents may not be discovered
- CLI/terminal sessions may use stale process state
- onboarding appears complete, but tooling runs with old context — phantom errors result

### 1. Explore the Codebase

- **Service Architecture**: See [`services/README.md`](services/README.md)
- **Test Taxonomy**: See [`tests/README.md`](tests/README.md)
- **Tooling**: See [`tools/README.md`](tools/README.md)

### 2. Review Documentation

- **Docs index**: [`docs/index.md`](docs/index.md)
- **Visual developer start**: [`docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`](docs/onboarding/DEVELOPER_VISUAL_START_HERE.md)
- **Repo Brain / Context Intelligence**: [`docs/surrealdb/README.md`](docs/surrealdb/README.md)
- **Governance**: `knowledge/governance/CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`
- **Runbooks**: [`docs/runbooks/README.md`](docs/runbooks/README.md)

### 3. Development Best Practices

**Code style**:
- Python: Black formatter (line-length 88), Ruff linter, mypy type checker
- All enforced in CI; run locally before committing
- See [`AGENTS.md`](AGENTS.md) for full style guidelines

**Test coverage** (minimum 80%):
```bash
make test-coverage
```

**Pre-commit hooks** (optional):
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Note: Ruff and Black are the primary CI gates. Pre-commit is optional.

### 4. Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for:
- PR workflow and branch naming
- Commit message format
- Testing requirements
- Required checks and scope boundaries
- `LOCK:` semantics for PRs
- Safety/LR boundaries

---

## Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| **PowerShell index** | `tools/README.md` |
| **Start stack** | `.\tools\cdb.ps1 runtime up` or `make docker-up` |
| **Stop stack** | `make docker-down` |
| **View logs** | `.\tools\cdb.ps1 service logs -ServiceName cdb_risk -Follow` |
| **Verify stack** | `.\tools\cdb.ps1 stack verify` or `make docker-health` |
| **Run CI tests** | `make test` |
| **Run tests (no stack)** | `pytest -q -k "not test_mcp_time_server_runtime"` |
| **Check coverage** | `make test-coverage` |
| **Lint** | `ruff check .` |
| **Format** | `black .` |
| **Type check** | `mypy core/ services/` |
| **Onboarding doctor** | `python -m tools.onboarding_doctor` or `.\tools\cdb.ps1 onboarding doctor` or `make onboarding-doctor` |
| **Onboarding simulation** | `python -m tools.onboarding_simulation` or `.\tools\cdb.ps1 onboarding simulate` |
| **Restart after onboarding** | **Required:** Close and reopen your tool/IDE/shell after onboarding |
| **Context preflight** | `make context-doctor` |
| **Core smoke test** | `.\tools\cdb.ps1 runtime smoke` |

### Important URLs (with stack running)

- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

### Important Files

- `.env` - Environment configuration
- `~/Documents/.secrets/.cdb/` - Secrets directory (check presence, never output values)
- `tools/README.md` - Authoritative PowerShell index
- `infrastructure/compose/compose.blue.yml` + `compose.red.yml` - Canonical stack definitions
- `Makefile` - Build and test targets

### Safety / LR Reminder

- **LR bleibt NO-GO** — SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Board-Stage `trade-capable` ist kein Live-Go**
- **Kein Echtgeld-Go ohne Human-Freigabe**
- **`CURRENT_STATUS.md` ist Ledger, nicht Live-Wahrheit**

---

**Document Version**: 2.0.0
**Last Updated**: 2026-06-16
**Maintained By**: Development Team
