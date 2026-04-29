"use client";

import { LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/useAuth";
import { HealthDot } from "./HealthDot";

export function Header() {
  const { identity, signOut } = useAuth();
  if (!identity) return null;

  const initials = identity.user_id.slice(0, 2).toUpperCase();
  const isAdmin = identity.role === "admin";

  return (
    <header className="border-b border-border bg-surface/80 backdrop-blur-md sticky top-0 z-20">
      <div className="max-w-[1400px] mx-auto px-5 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-accent" />
          <span className="font-semibold tracking-tight">TrustFlow AI</span>
        </div>
        <div className="flex items-center gap-3">
          <HealthDot />
          <div className="chip">
            <span className="text-subtle">tenant</span>
            <span className="font-mono text-zinc-200">{identity.tenant_id}</span>
          </div>
          {isAdmin && (
            <span className="pill border-accent/40 text-accent bg-accent/10">admin</span>
          )}
          <div className="flex items-center gap-2 pl-3 border-l border-border">
            <div className="w-8 h-8 rounded-full bg-accent/15 border border-accent/40 flex items-center justify-center text-sm font-semibold text-accent-soft">
              {initials}
            </div>
            <div className="text-sm leading-tight">
              <div className="font-medium text-zinc-100">{identity.user_id}</div>
              <div className="text-[10px] text-muted uppercase tracking-wide">
                {identity.role}
              </div>
            </div>
            <button
              onClick={signOut}
              className="btn-ghost ml-1"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
