from typing import Any
from uuid import uuid4

from app.db.connection import connection
from app.models import Identity


async def reset_password(args: dict[str, Any], identity: Identity) -> dict[str, Any]:
    """Mock password reset. Files a ticket and returns a confirmation.
    Real systems would call Okta/AD; this is a demo."""
    ticket_id = f"TKT-{uuid4().hex[:8].upper()}"
    target = args.get("target_user", identity.user_id)
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tickets (id, tenant_id, user_id, action, status)
                VALUES (%s, %s, %s, %s, 'completed')
                """,
                (ticket_id, identity.tenant_id, target, "password_reset"),
            )
        await conn.commit()
    return {
        "ticket_id": ticket_id,
        "user": target,
        "action": "password_reset",
        "status": "completed",
        "instructions": "A temporary password has been emailed. Reset on next login.",
    }
