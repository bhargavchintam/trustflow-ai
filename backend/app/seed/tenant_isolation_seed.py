"""Seed a second tenant (tenant_globex with Priya) so the cross-tenant eval case
has data to be isolated FROM."""
from __future__ import annotations

import asyncio

from app.db.connection import close_pool, connection, init_pool
from app.memory import service as memory

TENANT = "tenant_globex"
USER = "priya"

ROLE = "employee"

EPISODIC = [
    ("user", "I can't sign into my workstation this morning, password seems wrong."),
    ("assistant", "Let me check — looks like your account is locked. I'll trigger an unlock."),
]

SEMANTIC = [
    "Uses Windows 11 enterprise laptop",
    "Locked out frequently due to typo on the corporate keyboard",
]


async def _ensure_role():
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_roles (tenant_id, user_id, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = EXCLUDED.role
                """,
                (TENANT, USER, ROLE),
            )
        await conn.commit()


async def seed_tenant_isolation() -> None:
    await init_pool()
    await _ensure_role()
    await memory.wipe_user(tenant_id=TENANT, user_id=USER)
    session_id = "session_globex_employee_2026_04_20"
    for role, content in EPISODIC:
        await memory.write_episodic(
            tenant_id=TENANT, user_id=USER, session_id=session_id, role=role, content=content
        )
    for fact in SEMANTIC:
        await memory.write_semantic(tenant_id=TENANT, user_id=USER, fact=fact)


async def main() -> None:
    try:
        await seed_tenant_isolation()
        print(f"[seed] {USER} seeded under tenant={TENANT}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
