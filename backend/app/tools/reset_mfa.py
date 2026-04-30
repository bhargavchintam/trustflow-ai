from typing import Any

from app.models import Identity


async def reset_mfa(args: dict[str, Any], identity: Identity) -> dict[str, Any]:
    target = args.get("target_user", identity.user_id)
    return {
        "user": target,
        "status": "mfa_reset_initiated",
        "ticket_id": f"TKT-MFA-{identity.user_id[:4].upper()}-001",
        "next_step": "Open the authenticator app on your device and re-enroll.",
    }
