"""Identity resolver. Pulls (tenant_id, user_id, session_id, role) from headers/cookies/query
ONLY — never from the request body. This is enforced by the tenant-isolation-checker agent.

For the demo, identity is asserted by the client. In production a JWT middleware would
validate signatures and populate request.state.identity here.
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import Cookie, Header, Query
from psycopg.rows import dict_row

from app.config import get_settings
from app.db.connection import connection
from app.models import Identity


async def lookup_role(tenant_id: str, user_id: str) -> str:
    async with connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT role FROM user_roles WHERE tenant_id = %s AND user_id = %s",
                (tenant_id, user_id),
            )
            row = await cur.fetchone()
    return row["role"] if row else "employee"


async def resolve_identity(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    tenant: str | None = Query(default=None),
    user: str | None = Query(default=None),
    session_id_cookie: str | None = Cookie(default=None, alias="trustflow_session"),
) -> Identity:
    s = get_settings()
    tenant_id = x_tenant_id or tenant or s.default_tenant_id
    user_id = x_user_id or user or s.default_user_id
    session_id = x_session_id or session_id_cookie or str(uuid4())
    role = await lookup_role(tenant_id, user_id)
    return Identity(tenant_id=tenant_id, user_id=user_id, session_id=session_id, role=role)
