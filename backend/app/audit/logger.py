"""Single chokepoint for trace events. Every route decision, policy check, tool call,
memory op, and LLM call writes here."""
import json
import re
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.db.connection import connection
from app.models import EventType, Identity, PolicyDecisionLiteral

_PII_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "<email>"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "<card>"),
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "<secret>"),
    (re.compile(r"pa-[A-Za-z0-9_-]{20,}"), "<secret>"),
]


def redact(text: str) -> str:
    out = text
    for pat, repl in _PII_PATTERNS:
        out = pat.sub(repl, out)
    return out


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    serialised = json.dumps(payload, default=str)
    redacted = redact(serialised)
    return json.loads(redacted)


async def log_event(
    *,
    correlation_id: UUID,
    identity: Identity,
    message_id: UUID,
    event_type: EventType,
    payload: dict[str, Any] | None = None,
    decision: PolicyDecisionLiteral | None = None,
    reason: str | None = None,
    latency_ms: int | None = None,
) -> UUID:
    event_id = uuid4()
    safe_payload = redact_payload(payload or {})
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tool_audit (
                    id, correlation_id, tenant_id, user_id, session_id, message_id,
                    event_type, payload, decision, reason, latency_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    correlation_id,
                    identity.tenant_id,
                    identity.user_id,
                    identity.session_id,
                    message_id,
                    event_type,
                    Jsonb(safe_payload),
                    decision,
                    reason,
                    latency_ms,
                ),
            )
        await conn.commit()
    return event_id


async def fetch_trace(
    *,
    tenant_id: str,
    session_id: str,
    message_id: UUID | None = None,
    correlation_id: UUID | None = None,
) -> list[dict[str, Any]]:
    where = "tenant_id = %s AND session_id = %s"
    params: list[Any] = [tenant_id, session_id]
    if message_id is not None:
        where += " AND message_id = %s"
        params.append(message_id)
    if correlation_id is not None:
        where += " AND correlation_id = %s"
        params.append(correlation_id)

    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT id, correlation_id, tenant_id, user_id, session_id, message_id,
                       event_type, payload, decision, reason, latency_ms, created_at
                FROM tool_audit
                WHERE {where}
                ORDER BY created_at ASC
                """,
                params,
            )
            rows = await cur.fetchall()
    cols = [
        "id",
        "correlation_id",
        "tenant_id",
        "user_id",
        "session_id",
        "message_id",
        "event_type",
        "payload",
        "decision",
        "reason",
        "latency_ms",
        "created_at",
    ]
    return [dict(zip(cols, r)) for r in rows]
