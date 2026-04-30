from typing import Any

from app.models import Identity


async def unlock_account(args: dict[str, Any], identity: Identity) -> dict[str, Any]:
    target = args.get("target_user", identity.user_id)
    return {
        "user": target,
        "status": "unlocked",
        "ticket_id": f"TKT-UNL-{identity.user_id[:4].upper()}-001",
        "message": "Account unlocked. Please try signing in again.",
    }
