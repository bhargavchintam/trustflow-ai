"""Identity resolver. Two paths in priority order:

1. Bearer JWT (Supabase Auth) — production path. Email is in the JWT, tenant_id
   and user_id are derived from email domain (see auth/identity_mapping.py).
2. X-Tenant-Id / X-User-Id headers — automation path (smoke tests, eval suite,
   internal admin tooling). Documented in README as the dev-only fallback.

Requests with neither get 401 unless ALLOW_ANONYMOUS_IDENTITY=true, which maps
them to the default demo identity — local curl-debugging convenience only.

This is the only place identity is established. Everywhere else
(`request.state.identity` or `Depends(resolve_identity)`) just reads the result.
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import Cookie, Header, Query
from psycopg.rows import dict_row

from app.auth.identity_mapping import derive_identity_fields, derive_role
from app.auth.jwt_validator import TokenError, decode_token, http_unauthorized
from app.config import get_settings
from app.db.connection import connection
from app.models import Identity


async def lookup_role(tenant_id: str, user_id: str) -> str | None:
    async with connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT role FROM user_roles WHERE tenant_id = %s AND user_id = %s",
                (tenant_id, user_id),
            )
            row = await cur.fetchone()
    return row["role"] if row else None


def _parse_bearer(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def _identity_from_jwt(token: str, session_id: str | None) -> Identity | None:
    try:
        payload = decode_token(token)
    except TokenError:
        return None
    email = payload.get("email")
    if not email:
        return None
    tenant_id, user_id, derived_role = derive_identity_fields(email)
    db_role = await lookup_role(tenant_id, user_id)
    role = db_role or derived_role
    return Identity(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id or str(uuid4()),
        role=role,  # type: ignore[arg-type]
    )


async def resolve_identity_optional(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    tenant: str | None = Query(default=None),
    user: str | None = Query(default=None),
    session_id_cookie: str | None = Cookie(default=None, alias="trustflow_session"),
) -> Identity | None:
    """Like resolve_identity but returns None for unauthenticated requests."""
    session_id = x_session_id or session_id_cookie

    token = _parse_bearer(authorization)
    if token:
        ident = await _identity_from_jwt(token, session_id)
        if ident is not None:
            return ident

    if x_tenant_id or x_user_id or tenant or user:
        s = get_settings()
        tenant_id = x_tenant_id or tenant or s.default_tenant_id
        user_id = x_user_id or user or s.default_user_id
        sid = session_id or str(uuid4())
        db_role = await lookup_role(tenant_id, user_id)
        fallback_role = derive_role(user_id)
        return Identity(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=sid,
            role=db_role or fallback_role,  # type: ignore[arg-type]
        )

    return None


async def resolve_identity(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    tenant: str | None = Query(default=None),
    user: str | None = Query(default=None),
    session_id_cookie: str | None = Cookie(default=None, alias="trustflow_session"),
) -> Identity:
    ident = await resolve_identity_optional(
        authorization=authorization,
        x_tenant_id=x_tenant_id,
        x_user_id=x_user_id,
        x_session_id=x_session_id,
        tenant=tenant,
        user=user,
        session_id_cookie=session_id_cookie,
    )
    if ident is not None:
        return ident
    s = get_settings()
    if not s.allow_anonymous_identity:
        raise http_unauthorized("no identity: supply a bearer token or X-Tenant-Id/X-User-Id headers")
    return Identity(
        tenant_id=s.default_tenant_id,
        user_id=s.default_user_id,
        session_id=str(uuid4()),
        role="employee",
    )
