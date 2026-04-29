"""Validate Supabase Auth JWTs (HS256) issued for our project.

Supabase signs access tokens with the project's JWT secret using HS256. We
validate signature + standard claims (`exp`, `aud`) and return the decoded
payload (which includes `email`, `sub`, `role`).
"""
from __future__ import annotations

import logging

import jwt
from fastapi import HTTPException, status

from app.config import get_settings

log = logging.getLogger(__name__)


class TokenError(Exception):
    pass


def decode_token(token: str) -> dict:
    settings = get_settings()
    secret = settings.supabase_jwt_secret
    if not secret:
        raise TokenError("SUPABASE_JWT_SECRET not configured")
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenError("token expired") from e
    except jwt.InvalidTokenError as e:
        raise TokenError(f"invalid token: {e}") from e
    return payload


def http_unauthorized(reason: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=reason,
        headers={"WWW-Authenticate": "Bearer"},
    )
