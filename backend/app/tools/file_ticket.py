from typing import Any
from uuid import uuid4

from app.db.connection import connection
from app.models import Identity


async def file_ticket(args: dict[str, Any], identity: Identity) -> dict[str, Any]:
    """Generic ticket creation. Used by DAG flows (e.g., request_software) and as
    a fallback by ReAct agent for problems it can't resolve directly."""
    ticket_id = f"TKT-{uuid4().hex[:8].upper()}"
    target = args.get("target_user", identity.user_id)
    category = args.get("category", "general")
    summary = args.get("summary", "User-filed support request")[:500]
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tickets (id, tenant_id, user_id, action, status)
                VALUES (%s, %s, %s, %s, 'open')
                """,
                (ticket_id, identity.tenant_id, target, category),
            )
        await conn.commit()
    return {
        "ticket_id": ticket_id,
        "category": category,
        "summary": summary,
        "user": target,
        "status": "open",
        "eta": "1 business day",
    }
