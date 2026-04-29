"""Lazy Supabase client factories. Two flavors: anon (sign-up/sign-in) and
service-role (admin operations like creating demo accounts)."""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


class SupabaseNotConfigured(RuntimeError):
    pass


@lru_cache
def anon_client() -> Client:
    s = get_settings()
    if not (s.supabase_url and s.supabase_anon_key):
        raise SupabaseNotConfigured("SUPABASE_URL and SUPABASE_ANON_KEY required")
    return create_client(s.supabase_url, s.supabase_anon_key)


@lru_cache
def admin_client() -> Client:
    s = get_settings()
    if not (s.supabase_url and s.supabase_service_role_key):
        raise SupabaseNotConfigured(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required for admin ops"
        )
    return create_client(s.supabase_url, s.supabase_service_role_key)
