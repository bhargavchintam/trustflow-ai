"""Seed Acme tenant: Maya's pre-existing memory + procedural playbooks.

Idempotent: deletes Maya's existing memory before reseeding so the
returning-user behaviour starts from a clean slate every time.
"""
from __future__ import annotations

import asyncio

from app.db.connection import close_pool, connection, init_pool
from app.memory import service as memory

TENANT = "tenant_acme"
RETURNING_USER = "maya"
DEFAULT_ROLES = {
    "sam": "employee",
    "maya": "employee",
    "drew": "admin",
    "ceo": "executive",
}

MAYA_EPISODIC = [
    ("user", "VPN keeps disconnecting whenever my Mac wakes from sleep. It's been happening for the last week."),
    ("assistant", "Got it — sounds like a wake-event issue with GlobalProtect. Let me check your client version and recent disconnect events."),
    ("user", "Thanks. It's especially bad when I'm on coffee shop wifi."),
    ("assistant", "I can see GlobalProtect 6.2 with three recent disconnects. The fix is to reinstall the client and reset the network location. I'll walk you through it."),
    ("user", "That worked! Issue resolved."),
    ("assistant", "Glad it's fixed. I've recorded the playbook for next time."),
]

MAYA_SEMANTIC = [
    "Uses MacBook Pro M2 (macOS 14.5)",
    "VPN client: Palo Alto GlobalProtect 6.2",
    "Frequently works from coffee shops on public wifi",
]

VPN_PROCEDURAL = {
    "problem_signature": "vpn_disconnect_on_wake_macos",
    "steps": [
        {"action": "check GlobalProtect client version", "tool": "vpn_diagnostic"},
        {"action": "toggle 'Enforce GlobalProtect Connection' off then on", "tool": None},
        {"action": "reset network location in System Settings -> Network", "tool": None},
        {"action": "reinstall GlobalProtect from internal portal if symptom persists", "tool": None},
    ],
}

EMAIL_SLOW_PROCEDURAL = {
    "problem_signature": "email_slow_outlook_macos",
    "steps": [
        {"action": "check Outlook profile size and OST file integrity", "tool": None},
        {"action": "disable third-party Outlook add-ins (Settings -> Add-ins -> Manage)", "tool": None},
        {"action": "rebuild OST cache: quit Outlook, delete .ost in ~/Library/Group Containers", "tool": None},
        {"action": "if persists, file ticket for Exchange-side mailbox audit", "tool": None},
    ],
}

TEAMS_AUDIO_PROCEDURAL = {
    "problem_signature": "teams_audio_dropout_call",
    "steps": [
        {"action": "switch from VoIP to PSTN dial-in for the next 24h to confirm app vs network", "tool": None},
        {"action": "update audio drivers and Teams to latest", "tool": None},
        {"action": "in Teams Settings -> Devices, disable noise-suppression and re-test", "tool": None},
        {"action": "if dropouts persist on PSTN too, escalate to network team for QoS audit", "tool": None},
    ],
}

SLACK_SEARCH_PROCEDURAL = {
    "problem_signature": "slack_search_returns_no_results",
    "steps": [
        {"action": "verify channel scope (DMs and private channels are searched separately)", "tool": None},
        {"action": "rebuild local search index: Help -> Troubleshoot -> Reset Cache", "tool": None},
        {"action": "if still failing, check Workspace search-availability setting (admin)", "tool": None},
    ],
}

ZOOM_ECHO_PROCEDURAL = {
    "problem_signature": "zoom_audio_echo_in_meetings",
    "steps": [
        {"action": "ask call participants to mute when not speaking; echo is usually a single mic", "tool": None},
        {"action": "in Zoom Settings -> Audio, enable 'Suppress background noise' (Auto)", "tool": None},
        {"action": "switch to a wired headset; built-in laptop speaker + mic creates feedback", "tool": None},
        {"action": "if echo persists, run Audio Test Speaker & Microphone in Settings", "tool": None},
    ],
}

PRINTER_QUEUE_PROCEDURAL = {
    "problem_signature": "printer_queue_stuck_jobs",
    "steps": [
        {"action": "open the printer queue and Cancel All Documents", "tool": None},
        {"action": "restart the print spooler service (Windows: services.msc -> Print Spooler -> Restart)", "tool": None},
        {"action": "remove and re-add the printer if it's an IP printer that was offline", "tool": None},
        {"action": "if multiple users hit this same printer, escalate to facilities (driver issue)", "tool": None},
    ],
}

GIT_AUTH_PROCEDURAL = {
    "problem_signature": "git_clone_authentication_failed_github",
    "steps": [
        {"action": "verify SSH key is loaded: ssh-add -l", "tool": None},
        {"action": "test SSH auth: ssh -T git@github.com (expect 'successfully authenticated' message)", "tool": None},
        {"action": "rotate the SSH key if the org enforces 90-day expiry", "tool": None},
        {"action": "if HTTPS, ensure GitHub PAT has the correct scopes (repo, read:org)", "tool": None},
    ],
}

WIFI_AUTOCONNECT_PROCEDURAL = {
    "problem_signature": "wifi_does_not_autoconnect_on_wake",
    "steps": [
        {"action": "in Network preferences, set the office SSID priority to top", "tool": None},
        {"action": "uncheck 'Disable wifi when ethernet is connected' if dock-tethered", "tool": None},
        {"action": "forget and rejoin SSID with WPA2-Enterprise creds", "tool": None},
        {"action": "if still failing on multiple devices, escalate to networking (DHCP exhaustion)", "tool": None},
    ],
}

ALL_PROCEDURAL = [
    VPN_PROCEDURAL,
    EMAIL_SLOW_PROCEDURAL,
    TEAMS_AUDIO_PROCEDURAL,
    SLACK_SEARCH_PROCEDURAL,
    ZOOM_ECHO_PROCEDURAL,
    PRINTER_QUEUE_PROCEDURAL,
    GIT_AUTH_PROCEDURAL,
    WIFI_AUTOCONNECT_PROCEDURAL,
]


async def _ensure_user_roles() -> None:
    async with connection() as conn:
        async with conn.cursor() as cur:
            for user_id, role in DEFAULT_ROLES.items():
                await cur.execute(
                    """
                    INSERT INTO user_roles (tenant_id, user_id, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = EXCLUDED.role
                    """,
                    (TENANT, user_id, role),
                )
        await conn.commit()


async def seed_bob() -> None:
    """Kept named seed_bob for import stability; seeds Maya's history under tenant_acme."""
    await init_pool()
    await _ensure_user_roles()

    await memory.wipe_user(tenant_id=TENANT, user_id=RETURNING_USER)

    async with connection() as conn:
        async with conn.cursor() as cur:
            for proc in ALL_PROCEDURAL:
                await cur.execute(
                    "DELETE FROM procedural_memory WHERE tenant_id = %s AND problem_signature = %s",
                    (TENANT, proc["problem_signature"]),
                )
        await conn.commit()

    session_id = "session_acme_returning_user"
    for role, content in MAYA_EPISODIC:
        await memory.write_episodic(
            tenant_id=TENANT, user_id=RETURNING_USER, session_id=session_id, role=role, content=content
        )

    for fact in MAYA_SEMANTIC:
        await memory.write_semantic(
            tenant_id=TENANT, user_id=RETURNING_USER, fact=fact, confidence=0.9
        )

    for proc in ALL_PROCEDURAL:
        await memory.write_procedural(
            tenant_id=TENANT,
            problem_signature=proc["problem_signature"],
            steps=proc["steps"],
        )


async def main() -> None:
    try:
        await seed_bob()
        print(f"[seed] {RETURNING_USER} seeded under tenant={TENANT}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
