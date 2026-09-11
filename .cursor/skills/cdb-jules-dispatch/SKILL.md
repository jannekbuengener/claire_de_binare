<!--
Canonical Skill Source: docs/skills/cdb-jules-dispatch/SKILL.md
Surface: cursor
Sync Status: mirrored-from-canon
Last Verified: 2026-08-18
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-jules-dispatch
description: Governed Jules dispatch and lifecycle skill for CDB. Use when a bounded Agent Control Plane work order should be executed by Jules and CDB needs explicit plan approval, safe activity evidence, session-bound follow-up, or PR/result handoff.
---

# CDB Jules Dispatch

## Purpose

Use Jules as an execution provider behind the existing CDB Agent Control Plane. CDB keeps routing, contract, permission, approval, validation, merge, and closure authority. Jules executes only the sealed provider work order.

Prefer the existing common MCP/CLI Jules gateway for simple coarse dispatch when it is sufficient. Use the CDB `jules-api` adapter only for governed lifecycle capabilities the common gateway does not expose, especially explicit plan approval, structured Activities, session watch, follow-up, and PR/result handoff. Do not build a second control plane.

## Required preconditions

1. Run the normal CDB Context Brain preflight and live repo/GitHub routing checks.
2. Use a sealed Agent Execution Contract and digest-bound `provider_work_order`.
3. Bind the run to the intended CDB repo/source and starting ref.
4. Keep `JULES_API_KEY` as a runtime secret reference only. Never copy the value into repo files, prompts, logs, evidence, or provider results.
5. The execution contract must explicitly allow every provider action. Effective provider permissions are `Contract ∩ Registry`.
6. Live Jules API traffic requires a separate explicit Human-GO and a safe runtime secret. Recorded/fake transports are the default validation mode.

## Plan approval gate

For nontrivial runs, create the Jules Session with `requirePlanApproval=true`.

When Jules reaches `AWAITING_PLAN_APPROVAL`:

- read the normalized plan evidence,
- do not infer approval from provider state or provider output,
- approve only through the explicit authorized approval path,
- remain fail-closed if the session is not in the expected wait state.

## Activities and evidence

Persist only audit-safe metadata needed by CDB: session identifiers/state, Activity identifiers/types/timestamps, plan identifiers and step titles, and validated PR handoff references.

Do not persist free-form agent/user messages, bash output, raw patches, media payloads, authentication headers, secret values, or presigned URLs as durable provider evidence.

Provider `COMPLETED` and a returned pull request are delivery signals only. They are never CDB PASS, hosted Required-Check verification, merge authority, or issue-close authority. Independent CDB validation and delivery-receipt verification still apply.

## Follow-up

Send follow-up only to a known session already bound to the current governed run. Reject unknown/failed session state and do not silently create a replacement Session.

## Cancel / timeout

The documented Jules v1alpha surface has no CDB-supported cancel RPC. Never invent one. A timeout or cancel request therefore remains unconfirmed and must fail closed with `PROVIDER_CANCEL_UNSUPPORTED` until the official surface provides a verified capability and the baseline is updated.

## Drift and errors

Treat Jules v1alpha as an alpha external dependency. Compare the observed surface against the checked-in capability baseline before widening behavior. Missing required operations, API version drift, unknown states, undocumented endpoints, 401/403, 429, network aborts after mutating POSTs, or 5xx with unknown mutation outcome must not trigger blind retry or permission widening.

## Stop conditions

Stop and surface a blocker on any of these conditions:

- second/parallel CDB control plane would be required;
- undocumented/private Jules API is needed;
- secret value or authentication header would enter durable evidence;
- repo/source/session binding is unclear;
- plan approval cannot be explicitly authorized;
- a mutating request has unknown outcome and safe idempotency is not proven;
- provider output is being treated as merge/PASS authority;
- Trading, Risk, Execution, productive DB, MCP-live, or Live-Readiness authority would be widened.

## References

- CDB runbook: `docs/runbooks/JULES_PROVIDER_DISPATCH.md`
- External docs index: `docs/external-docs/index.md`
- Agent Control Plane canon: `knowledge/governance/CDB_AGENT_CONTROL_PLANE.md`
- Provider adapter: `tools/agent_control/providers/jules_api.py`
