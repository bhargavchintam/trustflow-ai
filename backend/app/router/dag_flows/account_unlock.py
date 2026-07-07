"""DAG flow: account_unlock. Single-call deterministic path."""
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
            tool="unlock_account",
            args={"target_user": identity.user_id},
            proposed_by="dag",
        ),
        identity=identity,
        correlation_id=correlation_id,
        message_id=message_id,
    )

    if tool_result.hitl:
        response = (
            "Account unlock for an admin/executive account requires approval. "
            "Your request has been logged for the IT team to review — they'll "
            "respond within 4 business hours."
        )
    elif tool_result.blocked:
        response = (
            f"I can't unlock that account — {tool_result.reason}. "
            f"This attempt has been logged; please contact IT if you believe "
            f"this is an error."
        )
    elif tool_result.error:
        response = "Hit a snag unlocking the account. Please raise a ticket with IT."
    else:
        data = tool_result.data or {}
        ticket = data.get("ticket_id", "TKT-UNKNOWN")
        response = (
            f"Done — your account has been unlocked (ticket **{ticket}**). "
            f"Try signing in again. If you still see a lockout, it may take "
            f"up to 60 seconds for the unlock to propagate."
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
