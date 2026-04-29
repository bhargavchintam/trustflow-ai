from typing import Any

from app.models import Identity


async def check_vpn_status(args: dict[str, Any], identity: Identity) -> dict[str, Any]:
    target = args.get("target_user", identity.user_id)
    return {
        "user": target,
        "client": "GlobalProtect 6.2",
        "tunnel": "down" if target == "maya" else "up",
        "last_handshake": "2026-04-29T12:01:00Z",
    }
