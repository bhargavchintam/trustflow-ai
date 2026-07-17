"""DAG flow: password_reset. Single-call deterministic path."""
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
        call=ToolCall(tool="reset_password", args={"target_user": identity.user_id},
                      proposed_by="dag"),
        identity=identity,
        correlation_id=correlation_id,
        message_id=message_id,
    )

    if tool_result.hitl:
        response = (
            "Password reset for your role requires admin approval. Your request "
            "has been logged for the IT team to review — they'll respond within "
            "4 business hours. In the meantime, I can help with anything else?"
        )
    elif tool_result.blocked:
        response = (
            f"I can't reset that password — {tool_result.reason}. "
            f"This attempt has been logged; please contact IT if you believe "
            f"this is an error."
        )
    elif tool_result.error:
        response = (
            "Something went wrong with the password reset. Please raise a ticket with IT."
        )
    else:
        data = tool_result.data or {}
        ticket = data.get("ticket_id", "TKT-UNKNOWN")
        response = (
            f"Done — your password has been reset (ticket {ticket}). "
            f"A temporary password has been emailed to you. "
            f"You'll be prompted to set a new one on next login."
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
