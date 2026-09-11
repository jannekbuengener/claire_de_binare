# CDB Cursor Subagent Shared Contract

Status: Canonical (Cursor subagent slice)  
Scope: All `.cursor/agents/cdb-*.md` subagents  
Governance: `knowledge/governance/CDB_AGENT_POLICY.md`, `agents/AGENTS.md`

---

## Authority and limits

Cursor subagents under `.cursor/agents/` are **helper roles** for delegated
work. They are **not** standalone authorities:

- They do not replace Session Lead, Human Gate, or canonical governance.
- They do not grant Live-Readiness, Echtgeld, deploy, merge, or strategy GO.
- Parent agent and Jannek retain decision authority.
- Subagents return one consolidated result to the parent; they do not own delivery.

---

## Parent agent enforcement

The **parent agent** (Session Lead / invoking operator context) owns gates;
subagents do not self-authorize.

**Parent MUST enforce before delegating or accepting subagent output:**

1. **Jannek GO** — explicit, scoped GO for any write, GitHub mutation, or
   delivery action (subagent prompts alone are not GO).
2. **Session-start** — `.cursor/skills/cdb-session-start/SKILL.md` completed for
   the write scope when applicable.
3. **Single-Writer LOCK** — per `knowledge/governance/CDB_AGENT_POLICY.md` §4
   when issue-scoped writes apply.
4. **Brain Evidence Gate** — when scope requires it (see below).
5. **Scope gates** — IN/OUT scope stated; subagent must not expand scope.

**`readonly: false` in frontmatter** means the subagent *can* edit files **only
after** the parent has confirmed GO + session-start + LOCK (when required). It is
**not** a free pass; without gates the subagent stays read-only (fail-closed).

Subagents must **STOP** and return the missing gate (GO, LOCK, skill, evidence)
instead of improvising writes or GitHub actions.

---

## Cursor Subagent Contract

- Work in your own clean context and return one final, consolidated result to the parent agent.
- Do not assume prior chat history is available. Require the parent prompt to include the issue/PR/task context.
- Follow the `readonly` frontmatter: if `readonly: true`, do not edit files and do not run state-changing commands.
- If a needed action exceeds your permissions, stop and return the exact missing GO, tool, file, or evidence.

---

## CDB Mandatory Bootstrap

Before any analysis, implementation, review, or plan:

1. Read `AGENTS.md` in the repo root.
2. Follow the pointer to `agents/AGENTS.md`.
3. If OpenCode is used, read `agents/OPEN_CODE_AGENTS.md`.
4. Read the complete Read Order defined in `agents/AGENTS.md`.
5. If any required file is missing, report the exact missing file and stop. Do not guess and do not start implementation.
6. Only after governance is loaded, fetch GitHub Issues/PRs/checks live.
7. For connected context, read all relevant Issues/PRs/docs before forming the plan.

---

## Non-Negotiable Operating Rules

- Repo live state and GitHub live state beat memory, stale queues, screenshots, and old status files.
- `CURRENT_STATUS.md` is an engineering **ledger**, not live truth.
- Live-readiness SSOT is `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- Board stage `trade-capable` is **not** a live, real-money, or readiness GO.
- Live-readiness remains **NO-GO** unless the LR SSOT and explicit human gate say otherwise.
- Default mode is read-only until Jannek gives a precise GO.
- No writes, commits, pushes, labels, comments, merges, branch deletes, workflow dispatches, stack changes, or live-mode changes without explicit GO.
- **GitHub writes — `gh` CLI only (absolute):** Any repository-mutating or
  GitHub-side action MUST go through the **`gh` CLI**, including: PR
  create/update, issue comments, labels, review actions, merges, branch deletes,
  and workflow dispatch. **No silent substitute** via GitHub REST/GraphQL API,
  MCP GitHub tools, connectors, or IDE integrations when `gh` can perform the
  action.
- **MCP / API / connectors — read-only default for subagents:** GitHub MCP,
  GitHub API clients, and third-party connectors may be used for **read /
  inspect / dry-run** only (e.g. `gh pr view`, `gh issue view`, check status).
  They MUST NOT perform mutating GitHub operations unless Jannek gives a
  **separate, explicit GO** that names the exact tool and action — and even
  then, prefer `gh` for the mutation. MCP config mutation is out of scope
  unless explicitly GO-gated.
- Direct push to `main` is not an acceptable default path. Use PR-based flow.
- `DELIVERY_APPROVED.yaml` is human-controlled; agents must not modify it.
- If scope grows, checks are red, evidence is missing, or assumptions are unstable: stop and report.
- Before Docker/infra stack changes, require explicit Jannek Human-GO with stated scope. There is no external Gordon/Docker-AI gate; if GO is missing, **STOP** (fail-closed). Prefer GitHub-live and repo evidence before ledger or memory claims.

---

## Zone A vs Write-Zone (`CDB_AGENT_POLICY` precedence)

`knowledge/governance/CDB_AGENT_POLICY.md` is authoritative when subagent text
or user phrasing conflicts with policy.

| Class | Zone | Subagent behavior |
| --- | --- | --- |
| Read-only discovery | Zone A–C (non-mutating) | Allowed without GO: repo reads, `gh` **view/list/status**, analysis, comparisons, plans marked review-only. |
| Mutating repo/GitHub/infra | Write-Zone (§4 Write-Gates) | Requires Jannek GO + session-start + LOCK (when issue-scoped) + **`gh`-only** for GitHub mutations. |
| Forbidden | Zone D | Never: custody/tresor, hard limits, canonical policy edits without GO, execution without risk layer, safety bypass. |

**Tension rule:** Subagents must not treat Zone A autonomy as permission to
commit, push, merge, label, comment on GitHub, dispatch workflows, or mutate
MCP/runtime/infra. Those are Write-Zone actions. On ambiguity → **STOP** (fail-closed).

---

## Brain Evidence Gate

For scopes including **Strategy, Runtime, Module, Service, Contract, Context,
SurrealDB, MCP tools, DB-backed Memory, or Evidence**, output this block
**before any plan** (see `agents/AGENTS.md` § Brain Evidence Gate):

```text
## Brain Evidence
brain_source: surrealdb-local | in_memory | repo-only | unavailable
brain_status: used | partial | not-used | blocked
tools_or_queries:
  - <Tool/Command/Query>
records_or_results:
  - <Record-ID/Count/Source/Hash, falls vorhanden>
repo_crosscheck:
  - <Datei/Pfad/Symbol/Commit>
impact_on_plan:
  - <Was dadurch anders geplant wurde>
limitations:
  - <Was nicht bewiesen ist>
```

### Field logic

- `brain_source=surrealdb-local`: Brain-Claims only with tool/query/record evidence.
- `brain_source=in_memory`: Fixture/Noop/In-Memory only; no DB-backed Brain-Claims.
- `brain_source=repo-only`: Clearly state brain-not-used.
- `brain_source=unavailable`: Clearly state `blocked` or **repo-only fallback**; do not imply DB-backed memory.

### Rules

- No plan may claim Memory/Evidence/Decision consideration without record/tool/query evidence.
- Strategy/Runtime/Module work MUST distinguish `repo-only` from brain-backed.
- GitHub/Repo/Live evidence wins over Brain/CIS claims.
- Board-Stage `trade-capable` is not Live-Go.
- LR remains NO-GO unless LR SSOT and human gate change.

### Context Brain adoption (#2775 / Phase-2 slice #2797)

SSOT: [`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](../../knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md)
(`read_only_context_brain = conditional`). Handoff details: [`agents/OPEN_CODE_AGENTS.md`](../../agents/OPEN_CODE_AGENTS.md).

**Source priority** (higher wins):

1. Live GitHub → 2. Repo files → 3. SurrealDB context package (guarded adapter only) →
4. Ledger (`CURRENT_STATUS.md` is **not** live truth) → 5. Fallback with limitations.

**Defaults until verified Context/DB/MCP evidence:**

- `brain_source=repo-only`, `brain_status=not-used`
- `in_memory` / Noop: no DB-backed claims
- `surrealdb-local`: only with adapter/tool/query/record evidence; caller-supplied
  `source`, `brain_source`, `brain_status`, or `metadata.source` are **not** evidence

**`briefing.session_context`:** read-only working/session memory (`session_only=true`);
not persistent DB memory. DB-backed claims only when `brain_source=surrealdb-local` and
`brain_status` is `used` or `partial`.

**Outputs are advisory:** Context Brain / MCP / briefing results do **not** trigger
automatic code changes, issue creation, labels, merges, or productive DB writes.

**Write gates (unchanged on main):** `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`;
no raw SurrealQL agent surface; no trading-state/secrets ingestion into SurrealDB.

---

## Write-Gates (PR Router + Dual-Lock)

Per `knowledge/governance/CDB_AGENT_POLICY.md` §4. Applies to agents with
`readonly: false` in frontmatter **before any** commit, push, PR create/update,
label, merge, or other repository-mutating GitHub action.

Before Session-Plan finalization, branch, worktree, or PR creation, the parent
MUST run:

`python -m tools.pr_routing route --issue <ISSUE> --agent <AGENT_NAME>`

The read-only result fixes the target PR/branch, lane, validation profile and
lock state. `HOLD_*` means no write surface may be created.

Before a new PR, reserve on the Issue:

`LOCK_RESERVATION: agent=<AGENT_NAME> issue=#<ISSUE> batch_pr=pending ts=<ISO8601> mode=batch-slice`

After Draft-PR creation, set the same LOCK on Issue and PR:

`LOCK: agent=<AGENT_NAME> issue=#<ISSUE> batch_pr=#<PR> ts=<ISO8601> mode=batch-slice`

Handoff requires matching UNLOCK events on Issue and PR:

`UNLOCK: agent=<OLD> issue=#<ISSUE> batch_pr=#<PR> ts=<ISO8601> mode=batch-slice reason=handoff-to-<NEW>`

**Rules:**

1. Only a complete, live-revalidated Issue/PR lock pair permits writes.
2. `PARTIAL_LOCK`, malformed, foreign or stale locks → **HARD STOP**.
3. Never auto-take over a stale lock.
4. Only one writer may modify a batch PR at a time.
5. Session Close defaults to targeted Slice Validation and
   `DONE_SLICE_ADDED_TO_BATCH_PR`, without merge or Issue close.
6. Full Fast-CI and hosted Required-Check verification belong only to a frozen final merge head.
7. Lock violation detected → `STOP: lock violation avoided. Detected LOCK by <X>. No changes made.`

Until Jannek GO + session-start + valid LOCK (when issue-scoped), remain read-only
even if frontmatter says `readonly: false`.

---

## Session boundary skills

**Before** any write scope (edits, commits, PR, GitHub writes):

- Cursor: `.cursor/skills/cdb-session-start/SKILL.md`
- Codex: `.codex/cdb_skills/cdb-session-start/SKILL.md`
- Router: `docs/skills/cdb-pr-router/SKILL.md`

**After** implementation/validation/repo work, before session close:

- Cursor: `.cursor/skills/cdb-session-close/SKILL.md`
- Codex: `.codex/cdb_skills/cdb-session-close/SKILL.md`

No write, commit, push, or PR action without explicit Jannek GO **and** completed session-start for that scope.

---

## MCP Capability Resolution (Context scope)

When scope includes **Context, SurrealDB, MCP tools, ContextBridge, or
DB-backed Memory** (see `agents/OPEN_CODE_AGENTS.md`):

1. Run MCP Capability Resolution **before** tool-dependent planning — repo file presence ≠ MCP availability.
2. Reference: `docs/runbooks/surrealdb_context_mcp_access.md` §1.5 and §1.5.1.
3. If `context.briefing`, `context.required_reads`, or `context.readiness` are not in the active MCP inventory → **STOP** and degrade to `repo-only` + `brain_status=not-used`.
4. `brain_source=unavailable` → **repo-only fallback**; mark limitations explicitly; no DB-backed claims.
5. Wave-14 read-only tools: `metadata.source=surrealdb-local` only from real adapter evidence; caller-supplied source fields are not DB evidence (fail-closed).
6. Do not mutate MCP configuration unless explicitly scoped and GO-gated.
7. **No MCP GitHub mutation:** MCP tools must not create/update GitHub resources
   (issues, PRs, comments, labels, merges) for subagents; use `gh` after GO.

---

## Standard output shape

Return:

1. Lage
2. Befund
3. Nächster Schritt
4. Validierung
5. Restunsicherheiten
6. Status

---

## Readonly vs write-capable agents

| `readonly` | Agent | May edit files after GO + session-start + LOCK |
| --- | --- | --- |
| `true` | `cdb-audit-priority-gatekeeper` | No |
| `true` | `cdb-code-reviewer` | No |
| `true` | `cdb-control-orchestrator` | No |
| `true` | `cdb-governance-gatekeeper` | No |
| `true` | `cdb-market-research-analyst` | No |
| `true` | `cdb-repository-auditor` | No |
| `true` | `cdb-security-triage` | No |
| `true` | `cdb-stack-ops-auditor` | No |
| `true` | `cdb-system-architect` | No |
| `true` | `cdb-validation-evidence-analyst` | No |
| `false` | `cdb-ci-debugger` | Yes (narrow CI/docs fix scope) |
| `false` | `cdb-context-intelligence-engineer` | Yes (Context/MCP/docs/tests scope) |
| `false` | `cdb-docs-canon-maintainer` | Yes (docs/ledger/runbook scope) |
| `false` | `cdb-implementation-engineer` | Yes (narrow code/docs slice) |

Only the four `readonly: false` agents may perform file edits — and only after
Jannek GO, session-start, and LOCK when issue-scoped. All others stay read-only
regardless of user phrasing.
