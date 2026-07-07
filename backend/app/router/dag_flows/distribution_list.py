"""DAG flow: distribution_list_access. Templated DL membership request via file_ticket."""
from __future__ import annotations

import re
from uuid import UUID

from app.audit.logger import log_event
from app.memory import service as memory
from app.models import Identity, ToolCall
from app.policy import gateway

_DL_RE = re.compile(
    r"\b(?:dl|distribution\s+list|mailing\s+list|email\s+group|google\s+group)\s+"
    r"(?:called\s+|named\s+|for\s+)?([\w./_+-]+(?:[\s@.][\w./_+-]+)*)",
    re.IGNORECASE,
)


def _extract_list(input_text: str) -> str:
    m = _DL_RE.search(input_text)
    if m:
        return m.group(1).strip().rstrip(".,?!")
    return "the requested distribution list"


async def run(
    *,
    identity: Identity,
    user_input: str,
    correlation_id: UUID,
    message_id: UUID,
) -> str:
    dl_name = _extract_list(user_input)

    await memory.write_episodic(
        tenant_id=identity.tenant_id,
        user_id=identity.user_id,
        session_id=identity.session_id,
        role="user",
        content=user_input,
    )
    await log_event(
        correlation_id=correlation_id,
        identity=identity,
        message_id=message_id,
        event_type="memory_write",
        payload={"tier": "episodic", "role": "user"},
    )

    tool_result = await gateway.execute(
        call=ToolCall(
            tool="file_ticket",
            args={
                "target_user": identity.user_id,
                "category": "dl_access_request",
                "summary": f"Distribution-list access request: {dl_name}",
            },
            proposed_by="dag",
        ),
        identity=identity,
        correlation_id=correlation_id,
        message_id=message_id,
    )

    if tool_result.blocked:
        response = (
            f"I couldn't file the DL access request — {tool_result.reason}. "
            f"Please email IT directly."
        )
    elif tool_result.error:
        response = "Hit a snag filing the ticket. Please email IT directly."
    else:
        ticket = (tool_result.data or {}).get("ticket_id", "TKT-PENDING")
        response = (
            f"Filed access request **{ticket}** to add you to *{dl_name}*. "
            f"The DL owner will review and approve (usually within 1 business day)."
        )

    await memory.write_episodic(
        tenant_id=identity.tenant_id,
        user_id=identity.user_id,
        session_id=identity.session_id,
        role="assistant",
        content=response,
    )
    await log_event(
        correlation_id=correlation_id,
        identity=identity,
        message_id=message_id,
        event_type="memory_write",
        payload={"tier": "episodic", "role": "assistant"},
    )
    return response
