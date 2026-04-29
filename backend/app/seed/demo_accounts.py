"""Seed the four demo accounts in Supabase Auth + user_roles.

Idempotent: safe to run repeatedly. If an account already exists, it's left
alone (we only set the password to the demo default if the user is freshly
created or password is None).

Demo accounts (all use password "DemoPass123!"):
    alice@acme.demo     -> tenant_acme,    role=employee
    bob@acme.demo       -> tenant_acme,    role=employee  (pre-seeded memory)
    charlie@globex.demo -> tenant_globex,  role=employee
    admin@acme.demo     -> tenant_acme,    role=admin

Run after `app.seed.bob_seed` and `app.seed.tenant_isolation_seed` so memory
and roles tables already exist with the right rows.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from app.auth.identity_mapping import derive_identity_fields
from app.auth.supabase_client import SupabaseNotConfigured, admin_client
from app.db.connection import close_pool, connection, init_pool

log = logging.getLogger(__name__)

DEMO_PASSWORD = "DemoPass123!"

DEMO_ACCOUNTS: list[tuple[str, str]] = [
    ("alice@acme.demo", "Alice (employee, no prior history — the new-user demo)"),
    ("bob@acme.demo", "Bob (employee, pre-seeded VPN history — the returning-user demo)"),
    ("charlie@globex.demo", "Charlie (employee, different tenant — proves tenant isolation)"),
    ("admin@acme.demo", "Admin (admin role — unlocks Demo Controls + Attack chips + /eval)"),
]


def _list_existing_emails() -> set[str]:
    client = admin_client()
    emails: set[str] = set()
    page = 1
    while True:
        resp = client.auth.admin.list_users(page=page, per_page=100)
        users = resp if isinstance(resp, list) else getattr(resp, "users", []) or []
        if not users:
            break
        for u in users:
            email = getattr(u, "email", None)
            if email:
                emails.add(email.lower())
        if len(users) < 100:
            break
        page += 1
    return emails


def _create_account(email: str, password: str) -> None:
    client = admin_client()
    client.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"demo_account": True},
        }
    )


async def _ensure_role(tenant_id: str, user_id: str, role: str) -> None:
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_roles (tenant_id, user_id, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, user_id) DO UPDATE
                    SET role = EXCLUDED.role
                """,
                (tenant_id, user_id, role),
            )
        await conn.commit()


async def seed_demo_accounts(emails: Iterable[tuple[str, str]] | None = None) -> dict:
    accounts = list(emails) if emails is not None else DEMO_ACCOUNTS
    summary = {"created": [], "existing": [], "errors": []}

    try:
        existing = _list_existing_emails()
    except SupabaseNotConfigured as e:
        return {"error": str(e), **summary}
    except Exception as e:
        return {"error": f"list_users failed: {e}", **summary}

    for email, _label in accounts:
        email_l = email.lower()
        try:
            tenant_id, user_id, role = derive_identity_fields(email_l)
            await _ensure_role(tenant_id, user_id, role)
            if email_l in existing:
                summary["existing"].append(email_l)
            else:
                _create_account(email_l, DEMO_PASSWORD)
                summary["created"].append(email_l)
        except Exception as e:
            summary["errors"].append({"email": email_l, "error": str(e)})

    return summary


async def main() -> None:
    await init_pool()
    try:
        result = await seed_demo_accounts()
        print(
            f"[demo_accounts] created={len(result['created'])} "
            f"existing={len(result['existing'])} errors={len(result['errors'])}"
        )
        for e in result["created"]:
            print(f"  + {e}")
        for e in result["existing"]:
            print(f"  = {e}")
        for err in result["errors"]:
            print(f"  ! {err}")
        if result.get("error"):
            print(f"  FATAL: {result['error']}")
            raise SystemExit(1)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
