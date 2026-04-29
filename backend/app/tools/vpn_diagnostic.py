from typing import Any

from app.models import Identity


async def vpn_diagnostic(args: dict[str, Any], identity: Identity) -> dict[str, Any]:
    target = args.get("target_user", identity.user_id)
    if target == "bob":
        return {
            "status": "GlobalProtect 6.2 detected",
            "last_disconnect": "2026-04-15T09:32:00Z",
            "wake_event_count": 3,
            "client": "Palo Alto GlobalProtect 6.2",
            "os": "macOS 14.5",
            "recommendation": "reinstall_globalprotect",
        }
    return {
        "status": "VPN client detected",
        "last_disconnect": None,
        "wake_event_count": 0,
        "client": "GlobalProtect 6.2 (default)",
        "os": "unknown",
        "recommendation": "run_standard_diagnostic",
    }
