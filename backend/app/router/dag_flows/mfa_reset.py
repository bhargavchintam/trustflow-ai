"""DAG flow: mfa_reset. Templated reset of multi-factor enrolment."""
from __future__ import annotations

from uuid import UUID

from app.audit.logger import log_event
from app.memory import service as memory
from app.models import Identity, ToolCall
from app.policy import gateway


async def run(
    *,
    identity: Identity,
    user_input: str,
    correlation_id: UUID,
    message_id: UUID,
) -> str:
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
            tool="reset_mfa",
            args={"target_user": identity.user_id},
            proposed_by="dag",
        ),
        identity=identity,
        correlation_id=correlation_id,
        message_id=message_id,
    )

    if tool_result.hitl:
        response = (
            "MFA reset for an admin/executive account requires HITL approval. "
            "I've filed ticket **#TKT-PENDING** for the IT team — they'll respond "
            "within 4 business hours."
        )
    elif tool_result.blocked:
        response = (
            f"I can't reset MFA — {tool_result.reason}. Filing a ticket for IT."
        )
    elif tool_result.error:
        response = "Hit a snag resetting MFA. I've escalated to the IT team."
    else:
        data = tool_result.data or {}
        ticket = data.get("ticket_id", "TKT-UNKNOWN")
        next_step = data.get("next_step", "Re-enrol via your authenticator app.")
        response = (
            f"Done — your MFA enrolment has been reset (ticket **{ticket}**). "
            f"{next_step}"
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
