"""Trusted live branch-protection attestation for approval snapshots (#4505)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from core.utils.clock import utcnow as cdb_utcnow
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.approval.producer_trust import (
    load_producer_trust_policy,
    producer_actor_trusted,
)
from tools.agent_control.paths import REPO_ROOT

EVIDENCE_MARKER = "<!-- cdb-protection-live:v1 -->"
PRODUCER = "cdb-protection-live-attestation"
SCHEMA_ID = "cdb.protection_live_attestation.v1"
SCHEMA_VERSION = "1.0.0"
SCHEMA_RELPATH = "docs/contracts/cdb_protection_live_attestation.v1.schema.json"
SHA40 = re.compile(r"^[a-f0-9]{40}$")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
DEFAULT_PROTECTION_ATTESTATION_MAX_AGE_HOURS = 24
DEFAULT_PROTECTION_ATTESTATION_MAX_FUTURE_SKEW_MINUTES = 5
GH_TIMEOUT_EXIT_CODE = -1
_PROTECTION_READ_HINT = (
    "Classic branch protection read requires repository administration "
    "read (admin:true on PAT or administration:read on GitHub App). "
    "Cursor Cloud ghs_ installation tokens typically lack this; "
    "use trusted cdb-protection-live attestation from cdb-local-ci "
    "or grant administration:read on the provider installation."
)


@dataclass(frozen=True)
class ProtectionReadError:
    endpoint: str
    http_status: int | None
    gh_exit_code: int
    message: str
    hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "http_status": self.http_status,
            "gh_exit_code": self.gh_exit_code,
            "message": self.message,
            "hint": self.hint,
        }


@dataclass(frozen=True)
class ResolvedProtectionAttestation:
    required_checks: list[dict[str, Any]]
    strict: bool
    comment_id: int
    envelope_digest: str
    observed_at: str


def _utc_now() -> datetime:
    value = cdb_utcnow()
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _format_observed_at(now: datetime | None = None) -> str:
    return (now or _utc_now()).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_protection_attestation_schema(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    path = root / SCHEMA_RELPATH
    if not path.is_file():
        raise ApprovalError(
            "PROTECTION_ATTESTATION_SCHEMA_MISSING",
            f"missing schema: {path}",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ApprovalError(
            "PROTECTION_ATTESTATION_SCHEMA_INVALID", "schema must be mapping"
        )
    return data


def _extract_http_status(stderr: str) -> int | None:
    for token in stderr.replace("(", " ").replace(")", " ").split():
        if token.isdigit() and len(token) == 3:
            return int(token)
    return None


def probe_branch_protection_api(
    owner: str,
    repo: str,
    base_branch: str,
    *,
    timeout: int = 60,
) -> tuple[dict[str, Any] | None, ProtectionReadError | None]:
    """Read live classic branch protection; fail closed with diagnostics."""
    endpoint = f"repos/{owner}/{repo}/branches/{base_branch}/protection"
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, ProtectionReadError(
            endpoint=endpoint,
            http_status=None,
            gh_exit_code=GH_TIMEOUT_EXIT_CODE,
            message=f"branch protection probe timed out after {timeout}s on {endpoint}",
            hint=_PROTECTION_READ_HINT,
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return None, ProtectionReadError(
            endpoint=endpoint,
            http_status=_extract_http_status(detail),
            gh_exit_code=result.returncode,
            message=detail[:500] if detail else "gh api failed",
            hint=_PROTECTION_READ_HINT,
        )
    raw = (result.stdout or "").strip()
    if not raw:
        return None, ProtectionReadError(
            endpoint=endpoint,
            http_status=None,
            gh_exit_code=result.returncode,
            message="empty response body",
            hint="branch protection endpoint returned no JSON payload",
        )
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return None, ProtectionReadError(
            endpoint=endpoint,
            http_status=200,
            gh_exit_code=0,
            message="protection payload is not a mapping",
            hint="unexpected GitHub API response shape",
        )
    return payload, None


def parse_required_checks_from_protection_payload(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool] | None:
    """Parse required checks and strict flag from branch protection JSON."""
    rsc = payload.get("required_status_checks")
    if not isinstance(rsc, dict):
        return None
    strict = bool(rsc.get("strict"))
    contexts: list[str] = []
    context_bindings: dict[str, dict[str, Any]] = {}
    raw = rsc.get("contexts")
    if isinstance(raw, list):
        contexts = [str(item) for item in raw if isinstance(item, str) and item.strip()]
    checks_list = rsc.get("checks")
    if isinstance(checks_list, list):
        for item in checks_list:
            if not isinstance(item, dict):
                continue
            context = item.get("context")
            if not isinstance(context, str) or not context.strip():
                continue
            binding: dict[str, Any] = {"name": context.strip()}
            app_id = item.get("app_id")
            if app_id is not None:
                binding["app_id"] = app_id
                binding["mechanism"] = "check_run"
            context_bindings[context.strip()] = binding
    if not contexts:
        return None
    out: list[dict[str, Any]] = []
    for name in contexts:
        if name in context_bindings:
            entry = dict(context_bindings[name])
            if "mechanism" not in entry:
                entry["mechanism"] = "unknown"
        else:
            entry = {"name": name, "mechanism": "unknown"}
        out.append(entry)
    return out, strict


def build_protection_live_envelope(
    *,
    repository: str,
    base_ref: str,
    base_sha: str,
    protection_payload: dict[str, Any],
    observed_at: str | None = None,
) -> dict[str, Any]:
    parsed = parse_required_checks_from_protection_payload(protection_payload)
    if parsed is None:
        raise ApprovalError(
            "PROTECTION_ATTESTATION_INCOMPLETE",
            "branch protection payload missing required_status_checks",
        )
    required_checks, strict = parsed
    base = base_sha.lower()
    if not SHA40.match(base):
        raise ApprovalError("PROTECTION_ATTESTATION_INVALID", "invalid base_sha")
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "producer": PRODUCER,
        "subject": {
            "repository": repository,
            "base_ref": base_ref,
            "base_sha": base,
        },
        "protection": {
            "source": "branch_protection_api",
            "required_checks": required_checks,
            "strict": strict,
        },
        "observed_at": observed_at or _format_observed_at(),
    }


def format_protection_attestation_comment_body(envelope: dict[str, Any]) -> str:
    text = json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False)
    return f"{EVIDENCE_MARKER}\n\n```json\n{text}\n```\n"


def _extract_envelope_json(body: str) -> dict[str, Any] | None:
    if EVIDENCE_MARKER not in body:
        return None
    fenced = _JSON_FENCE_RE.search(body)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    start = body.find("{", body.index(EVIDENCE_MARKER))
    if start < 0:
        return None
    depth = 0
    for idx in range(start, len(body)):
        ch = body[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(body[start : idx + 1])
                    return data if isinstance(data, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _protection_attestation_max_age_hours(
    trust_policy: dict[str, Any],
) -> int:
    producers = (
        trust_policy.get("producers")
        if isinstance(trust_policy.get("producers"), dict)
        else {}
    )
    rules = producers.get(PRODUCER) if isinstance(producers.get(PRODUCER), dict) else {}
    raw = rules.get("max_observed_age_hours")
    if isinstance(raw, int) and raw > 0:
        return raw
    return DEFAULT_PROTECTION_ATTESTATION_MAX_AGE_HOURS


def _parse_observed_at(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _attestation_is_fresh(
    observed_at: str,
    *,
    trust_policy: dict[str, Any],
    now: datetime | None = None,
) -> bool:
    observed = _parse_observed_at(observed_at)
    if observed is None:
        return False
    clock = now or _utc_now()
    max_age = timedelta(hours=_protection_attestation_max_age_hours(trust_policy))
    max_future_skew = timedelta(
        minutes=DEFAULT_PROTECTION_ATTESTATION_MAX_FUTURE_SKEW_MINUTES
    )
    return clock - max_age <= observed <= clock + max_future_skew


def _envelope_digest(envelope: dict[str, Any]) -> str:
    material = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(material).hexdigest()


def resolve_protection_live_attestation(
    *,
    comments: list[CommentRecord],
    repository: str,
    live_base_sha: str,
    live_base_ref: str,
    repo_root: Path | None = None,
) -> ResolvedProtectionAttestation | None:
    """Return newest trusted attestation bound to live base SHA, else None."""
    root = repo_root or REPO_ROOT
    schema = load_protection_attestation_schema(root)
    validator = Draft202012Validator(schema)
    trust_policy = load_producer_trust_policy(root)
    base = live_base_sha.lower()
    candidates: list[tuple[int, ResolvedProtectionAttestation]] = []

    for comment in comments:
        if comment.comment_id is None:
            continue
        body = comment.body or ""
        envelope = _extract_envelope_json(body)
        if envelope is None:
            continue
        errors = sorted(validator.iter_errors(envelope), key=lambda e: list(e.path))
        if errors:
            continue
        trusted, _detail = producer_actor_trusted(
            producer=PRODUCER,
            comment=comment,
            trust_policy=trust_policy,
            repo_root=root,
        )
        if not trusted:
            continue
        subject = envelope.get("subject")
        if not isinstance(subject, dict):
            continue
        if subject.get("repository") != repository:
            continue
        if subject.get("base_ref") != live_base_ref:
            continue
        subj_base = subject.get("base_sha")
        if not isinstance(subj_base, str) or subj_base.lower() != base:
            continue
        protection = envelope.get("protection")
        if not isinstance(protection, dict):
            continue
        required = protection.get("required_checks")
        if not isinstance(required, list) or not required:
            continue
        observed_at = str(envelope.get("observed_at") or "")
        if not _attestation_is_fresh(observed_at, trust_policy=trust_policy):
            continue
        strict = bool(protection.get("strict"))
        resolved = ResolvedProtectionAttestation(
            required_checks=[dict(item) for item in required if isinstance(item, dict)],
            strict=strict,
            comment_id=comment.comment_id,
            envelope_digest=_envelope_digest(envelope),
            observed_at=observed_at,
        )
        candidates.append((comment.comment_id, resolved))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]
