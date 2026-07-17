"""Seed the four sample workspace accounts in Supabase Auth + user_roles.

Idempotent: safe to run repeatedly. Existing accounts are left alone; legacy
emails (older naming) are removed so the login UI only ever surfaces the
current set.

Sample accounts (all use password "DemoPass123!"):
    sam@acme.com       -> tenant_acme,    role=employee  (fresh, no history)
    maya@acme.com      -> tenant_acme,    role=employee  (pre-seeded history)
    priya@globex.com   -> tenant_globex,  role=employee  (separate tenant)
    drew@acme.com      -> tenant_acme,    role=admin     (admin surface)

Run after `app.seed.bob_seed` and `app.seed.tenant_isolation_seed` so memory
and roles tables already exist with the right rows.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from app.auth.identity_mapping import derive_identity_fields
from app.auth.supabase_client import SupabaseNotConfigured, admin_client
from app.db.connection import close_pool, connection, init_pool

log = logging.getLogger(__name__)

DEMO_PASSWORD = "DemoPass123!"  # noqa: S105 -- seed data for local/demo Supabase accounts, not a real secret

DEMO_ACCOUNTS: list[tuple[str, str]] = [
    ("sam@acme.com", "Sam (Acme employee, fresh account — no prior history)"),
    ("maya@acme.com", "Maya (Acme employee, returning user with prior IT history)"),
    ("priya@globex.com", "Priya (Globex employee, separate tenant)"),
    ("drew@acme.com", "Drew (Acme administrator, full ops access)"),
]

# Old account emails that should be removed if found (renamed during product polish).
LEGACY_EMAILS_TO_REMOVE = {
    "alice@acme.demo",
    "bob@acme.demo",
    "charlie@globex.demo",
    "admin@acme.demo",
}


def _list_existing_users() -> dict[str, str]:
    """Return {email_lower: user_id} for all users in the project."""
    client = admin_client()
    out: dict[str, str] = {}
    page = 1
    while True:
        resp = client.auth.admin.list_users(page=page, per_page=100)
        users = resp if isinstance(resp, list) else getattr(resp, "users", []) or []
        if not users:
            break
        for u in users:
            email = getattr(u, "email", None)
            uid = getattr(u, "id", None)
            if email and uid:
                out[email.lower()] = uid
        if len(users) < 100:
            break
        page += 1
    return out


def _list_existing_emails() -> set[str]:
    return set(_list_existing_users().keys())


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
    summary = {"created": [], "existing": [], "removed_legacy": [], "errors": []}

    try:
        existing_users = _list_existing_users()
    except SupabaseNotConfigured as e:
        return {"error": str(e), **summary}
    except Exception as e:
        return {"error": f"list_users failed: {e}", **summary}

    existing = set(existing_users.keys())

    # Remove any legacy demo accounts (renamed during product polish) so the
    # login page only ever shows the current account list.
    try:
        client = admin_client()
        for legacy_email in LEGACY_EMAILS_TO_REMOVE:
            uid = existing_users.get(legacy_email)
            if uid:
                try:
                    client.auth.admin.delete_user(uid)
                    summary["removed_legacy"].append(legacy_email)
                except Exception as e:
                    summary["errors"].append({"email": legacy_email, "error": f"delete: {e}"})
    except Exception as e:
        summary["errors"].append({"email": "<legacy-cleanup>", "error": str(e)})

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
