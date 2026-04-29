"""Seed Bob's pre-existing memory so the returning-user demo works.

Idempotent: deletes Bob's existing memory before reseeding.
"""
from __future__ import annotations

import asyncio

from app.db.connection import close_pool, connection, init_pool
from app.memory import service as memory

TENANT = "tenant_acme"
DEFAULT_ROLES = {
    "alice": "employee",
    "bob": "employee",
    "charlie": "employee",
    "ceo": "executive",
}

BOB_EPISODIC = [
    ("user", "VPN keeps disconnecting whenever my Mac wakes from sleep. It's been happening for the last week."),
    ("assistant", "Got it — sounds like a wake-event issue with GlobalProtect. Let me check your client version and recent disconnect events."),
    ("user", "Thanks. It's especially bad when I'm on coffee shop wifi."),
    ("assistant", "I can see GlobalProtect 6.2 with three recent disconnects. The fix is to reinstall the client and reset the network location. I'll walk you through it."),
    ("user", "That worked! Issue resolved."),
    ("assistant", "Glad it's fixed. I've recorded the playbook for next time."),
]

BOB_SEMANTIC = [
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

ALL_PROCEDURAL = [VPN_PROCEDURAL, EMAIL_SLOW_PROCEDURAL, TEAMS_AUDIO_PROCEDURAL]


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
    await init_pool()
    await _ensure_user_roles()

    await memory.wipe_user(tenant_id=TENANT, user_id="bob")

    async with connection() as conn:
        async with conn.cursor() as cur:
            for proc in ALL_PROCEDURAL:
                await cur.execute(
                    "DELETE FROM procedural_memory WHERE tenant_id = %s AND problem_signature = %s",
                    (TENANT, proc["problem_signature"]),
                )
        await conn.commit()

    session_id = "session_bob_2026_04_15"
    for role, content in BOB_EPISODIC:
        await memory.write_episodic(
            tenant_id=TENANT, user_id="bob", session_id=session_id, role=role, content=content
        )

    for fact in BOB_SEMANTIC:
        await memory.write_semantic(
            tenant_id=TENANT, user_id="bob", fact=fact, confidence=0.9
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
        print(f"[seed] bob seeded under tenant={TENANT}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
