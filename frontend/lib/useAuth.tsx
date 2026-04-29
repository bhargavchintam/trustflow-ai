"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { SUPABASE_CONFIGURED, supabase } from "./supabase";
import type { Identity } from "./types";

interface AuthState {
  session: Session | null;
  identity: Identity | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthCtx = createContext<AuthState | null>(null);

function deriveIdentityFromEmail(email: string): Identity {
  const [localRaw, domainRaw] = email.split("@");
  const local = (localRaw ?? "user").toLowerCase().replace(/[^a-z0-9_-]+/g, "") || "user";
  const domain = (domainRaw ?? "demo").toLowerCase();
  const SPECIAL: Record<string, string> = {
    "acme.demo": "tenant_acme",
    "globex.demo": "tenant_globex",
  };
  const tenant_id = SPECIAL[domain] ?? `tenant_${domain.replace(/[^a-z0-9]+/g, "_")}`;
  const role: Identity["role"] = local === "admin" ? "admin" : "employee";
  return {
    tenant_id,
    user_id: local,
    session_id: typeof crypto !== "undefined" ? crypto.randomUUID() : "session",
    role,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!SUPABASE_CONFIGURED) {
      setLoading(false);
      return;
    }
    const sb = supabase();
    let cancelled = false;
    sb.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      setSession(data.session ?? null);
      setLoading(false);
    });
    const { data: sub } = sb.auth.onAuthStateChange((_event, s) => {
      setSession(s ?? null);
      setLoading(false);
    });
    return () => {
      cancelled = true;
      sub?.subscription.unsubscribe();
    };
  }, []);

  const identity = useMemo<Identity | null>(() => {
    const email = session?.user.email;
    return email ? deriveIdentityFromEmail(email) : null;
  }, [session?.user.email]);

  const signIn = async (email: string, password: string) => {
    const sb = supabase();
    const { error } = await sb.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };

  const signUp = async (email: string, password: string) => {
    const sb = supabase();
    const { error } = await sb.auth.signUp({ email, password });
    if (error) throw error;
  };

  const signOut = async () => {
    const sb = supabase();
    await sb.auth.signOut();
    setSession(null);
  };

  const refresh = async () => {
    const sb = supabase();
    const { data } = await sb.auth.getSession();
    setSession(data.session ?? null);
  };

  const value: AuthState = { session, identity, loading, signIn, signUp, signOut, refresh };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(AuthCtx);
  if (!v) throw new Error("useAuth must be used inside <AuthProvider>");
  return v;
}

export async function getAccessToken(): Promise<string | null> {
  if (!SUPABASE_CONFIGURED) return null;
  const sb = supabase();
  const { data } = await sb.auth.getSession();
  return data.session?.access_token ?? null;
}
