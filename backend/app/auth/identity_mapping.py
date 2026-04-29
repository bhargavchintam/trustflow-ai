"""Email → (tenant_id, user_id, role) mapping.

Open sign-up: any email is accepted. Tenant is derived from email domain
so each company gets its own isolated tenant naturally. Two domains are
special-cased so the demo data (Bob / Charlie pre-seeds) lines up:

  *@acme.demo   -> tenant_acme
  *@globex.demo -> tenant_globex
  any other     -> tenant_<sanitized-domain>

Role: admin@<anything> -> "admin"; everyone else -> "employee".
The user_id is the email local part, sanitized.
"""
from __future__ import annotations

import re

SPECIAL_DOMAINS = {
    "acme.demo": "tenant_acme",
    "globex.demo": "tenant_globex",
}


def sanitize_user_id(local: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_-]+", "", local.lower()).strip("-_")
    return cleaned or "user"


def tenant_id_for_domain(domain: str) -> str:
    domain = domain.lower().strip()
    if domain in SPECIAL_DOMAINS:
        return SPECIAL_DOMAINS[domain]
    safe = re.sub(r"[^a-z0-9]+", "_", domain).strip("_")
    return f"tenant_{safe}"


def derive_role(user_id: str) -> str:
    return "admin" if user_id == "admin" else "employee"


def split_email(email: str) -> tuple[str, str]:
    local, _, domain = email.partition("@")
    if not local or not domain:
        raise ValueError(f"invalid email: {email!r}")
    return local, domain


def derive_identity_fields(email: str) -> tuple[str, str, str]:
    """Return (tenant_id, user_id, role) for the given email."""
    local, domain = split_email(email)
    user_id = sanitize_user_id(local)
    tenant_id = tenant_id_for_domain(domain)
    role = derive_role(user_id)
    return tenant_id, user_id, role
