"""DAG flow: request_software. Templated 1-step path.

User says 'I need <tool>' or 'request access to <tool>'. We file a templated
ticket via the file_ticket tool (gateway-mediated), no LLM in the loop.
"""
from __future__ import annotations

import re
from uuid import UUID

from app.audit.logger import log_event
from app.memory import service as memory
from app.models import Identity, ToolCall
from app.policy import gateway

_SOFTWARE_RE = re.compile(
    r"\b(?:request|need|install|access to|provision|grant me)\s+([\w./-]+(?:\s+[\w./-]+){0,2})",
    re.IGNORECASE,
)


def _extract_software(input_text: str) -> str:
    m = _SOFTWARE_RE.search(input_text)
    if m:
        return m.group(1).strip().rstrip(".,?!")
    return "the requested software"


async def run(
    *,
    identity: Identity,
    user_input: str,
    correlation_id: UUID,
    message_id: UUID,
) -> str:
    software = _extract_software(user_input)

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
                "category": "software_request",
                "summary": f"Software access request: {software}",
            },
            proposed_by="dag",
        ),
        identity=identity,
        correlation_id=correlation_id,
        message_id=message_id,
    )

    if tool_result.blocked:
        response = (
            f"I couldn't file the request automatically — {tool_result.reason}. "
            f"Please email IT directly."
        )
    elif tool_result.error:
        response = "Hit a snag filing the ticket. I've escalated to the IT team."
    else:
        ticket = (tool_result.data or {}).get("ticket_id", "TKT-PENDING")
        response = (
            f"Filed software access request **{ticket}** for {software}. "
            f"IT will review (usually within 1 business day) and you'll get an "
            f"email when it's provisioned."
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
