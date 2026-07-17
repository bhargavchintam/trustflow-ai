"""Auth endpoints — sign-up, sign-in, sign-out, me. Wraps Supabase Auth."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.identity import resolve_identity_optional
from app.auth.identity_mapping import derive_identity_fields
from app.auth.jwt_validator import http_unauthorized
from app.auth.supabase_client import (
    SupabaseNotConfigured,
    admin_client,
    anon_client,
)
from app.db.connection import connection
from app.models import Identity

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None
    user: dict
    identity: Identity


async def _ensure_role_row(tenant_id: str, user_id: str, role: str) -> None:
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


def _build_identity(email: str, session_id: str = "session_default") -> Identity:
    tenant_id, user_id, role = derive_identity_fields(email)
    return Identity(
        tenant_id=tenant_id, user_id=user_id, session_id=session_id, role=role
    )


@router.post("/sign-up", response_model=AuthResponse)
async def sign_up(req: SignUpRequest):
    """Open sign-up: admin-creates the user with email_confirm=true (bypasses Supabase's
    optional email-confirmation flow), then signs them in to return a real session.
    For production, swap admin_client for anon_client + handle confirm flow."""
    try:
        admin = admin_client()
        anon = anon_client()
    except SupabaseNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        admin.auth.admin.create_user(
            {
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {"signup_source": "trustflow_demo"},
            }
        )
    except Exception as e:
        msg = str(e)
        if "already" in msg.lower() or "registered" in msg.lower():
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Try Sign in instead.",
            ) from e
        raise HTTPException(status_code=400, detail=f"sign-up failed: {e}") from e

    try:
        result = anon.auth.sign_in_with_password(
            {"email": req.email, "password": req.password}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"post-signup sign-in failed: {e}") from e
    if not result.session:
        raise HTTPException(status_code=500, detail="post-signup sign-in returned no session")

    identity = _build_identity(req.email)
    await _ensure_role_row(identity.tenant_id, identity.user_id, identity.role)

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user={
            "id": result.user.id if result.user else None,
            "email": result.user.email if result.user else None,
        },
        identity=identity,
    )


@router.post("/sign-in", response_model=AuthResponse)
async def sign_in(req: SignInRequest):
    try:
        client = anon_client()
    except SupabaseNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        result = client.auth.sign_in_with_password(
            {"email": req.email, "password": req.password}
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"sign-in failed: {e}") from e
    if not result.session:
        raise HTTPException(status_code=401, detail="invalid credentials")

    identity = _build_identity(req.email)
    await _ensure_role_row(identity.tenant_id, identity.user_id, identity.role)

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user={
            "id": result.user.id if result.user else None,
            "email": result.user.email if result.user else None,
        },
        identity=identity,
    )


@router.post("/sign-out")
async def sign_out():
    try:
        client = anon_client()
        client.auth.sign_out()
    except Exception:  # noqa: S110 -- best-effort sign-out; client already discards local session either way
        pass
    return {"status": "ok"}


@router.get("/me", response_model=Identity)
async def me(identity: Identity | None = Depends(resolve_identity_optional)):
    if identity is None:
        raise http_unauthorized("not authenticated")
    return identity
