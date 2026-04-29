"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/useAuth";
import { SUPABASE_CONFIGURED } from "@/lib/supabase";
import { cn } from "@/lib/utils";

const DEMO_PASSWORD = "DemoPass123!";
const DEMO_ACCOUNTS = [
  {
    email: "alice@acme.demo",
    label: "Alice",
    sub: "tenant_acme · employee · no prior history (new-user demo)",
  },
  {
    email: "bob@acme.demo",
    label: "Bob",
    sub: "tenant_acme · employee · pre-seeded VPN history (returning-user demo)",
  },
  {
    email: "charlie@globex.demo",
    label: "Charlie",
    sub: "tenant_globex · employee · open second browser to prove tenant isolation",
  },
  {
    email: "admin@acme.demo",
    label: "Admin",
    sub: "tenant_acme · admin · unlocks demo controls + /eval dashboard",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { session, loading, signIn, signUp } = useAuth();
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && session) router.replace("/");
  }, [loading, session, router]);

  if (!SUPABASE_CONFIGURED) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6 bg-bg">
        <div className="card max-w-md text-sm space-y-2">
          <div className="text-warn font-semibold">Supabase Auth not configured</div>
          <p className="text-muted">
            Set <code className="text-zinc-200">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
            <code className="text-zinc-200">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in{" "}
            <code className="text-zinc-200">frontend/.env.local</code>, then restart the dev server.
          </p>
        </div>
      </main>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(mode);
    try {
      if (mode === "sign-in") await signIn(email, password);
      else await signUp(email, password);
    } catch (err: any) {
      setError(err?.message ?? "auth failed");
    } finally {
      setBusy(null);
    }
  }

  async function quickSignIn(email: string) {
    setError(null);
    setBusy(email);
    try {
      await signIn(email, DEMO_PASSWORD);
    } catch (err: any) {
      setError(`${email}: ${err?.message ?? "auth failed"}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-zinc-100 flex items-center justify-center p-6">
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-6">
        <section className="card bg-gradient-to-b from-panel to-surface border-border-strong p-8 space-y-5">
          <div className="flex items-center gap-2 text-accent">
            <ShieldCheck className="w-5 h-5" />
            <span className="text-xs uppercase tracking-wider font-semibold">
              TrustFlow AI
            </span>
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Sign in</h1>
            <p className="text-muted text-sm mt-1">
              Hybrid DAG + ReAct IT support · 3-tier memory · policy-gated tools.
            </p>
          </div>

          <div className="flex gap-1 rounded-md border border-border bg-surface p-1 w-fit text-sm">
            {(["sign-in", "sign-up"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={cn(
                  "px-3 py-1.5 rounded-md transition-colors",
                  mode === m
                    ? "bg-elevated text-zinc-100"
                    : "text-muted hover:text-zinc-200",
                )}
              >
                {m === "sign-in" ? "Sign in" : "Sign up"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="block text-xs text-muted mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@company.com"
                autoComplete="email"
              />
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="••••••"
                autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
              />
            </div>
            {error && (
              <div className="text-deny text-xs bg-deny/10 border border-deny/40 rounded-md px-3 py-2">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={busy !== null}
              className="btn-accent w-full justify-center inline-flex items-center gap-2"
            >
              {busy === mode && <Loader2 className="w-4 h-4 animate-spin" />}
              {mode === "sign-in" ? "Sign in" : "Create account"}
            </button>
          </form>

          <p className="text-xs text-subtle">
            {mode === "sign-in"
              ? "New here? Use the Sign up tab — sign-up is open for any email domain."
              : "After signing up you'll land in your own tenant (derived from your email domain)."}
          </p>
        </section>

        <section className="card border-border-strong p-6 space-y-4">
          <div className="flex items-center gap-2 text-accent">
            <Sparkles className="w-4 h-4" />
            <span className="text-xs uppercase tracking-wider font-semibold">
              Demo accounts
            </span>
          </div>
          <p className="text-muted text-xs leading-relaxed">
            Pre-seeded for the demo so you can start exploring in one click. Open the
            same URL in a second browser/incognito window and sign in as a different
            account to see tenant isolation in action.
          </p>
          <ul className="space-y-2">
            {DEMO_ACCOUNTS.map((a) => (
              <li key={a.email}>
                <button
                  onClick={() => quickSignIn(a.email)}
                  disabled={busy !== null}
                  className="w-full text-left px-3 py-2.5 rounded-md border border-border bg-surface hover:border-accent/60 hover:bg-elevated transition-colors group"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-medium text-zinc-100 text-sm">
                        {a.label}{" "}
                        <span className="text-muted font-mono text-xs">
                          {a.email}
                        </span>
                      </div>
                      <div className="text-xs text-muted mt-0.5">{a.sub}</div>
                    </div>
                    <div className="text-xs text-accent opacity-0 group-hover:opacity-100 transition-opacity">
                      Sign in →
                    </div>
                  </div>
                  {busy === a.email && (
                    <div className="mt-2 text-xs text-accent inline-flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" /> signing in…
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <p className="text-xs text-subtle border-t border-border pt-3">
            Demo password (shared, all accounts):{" "}
            <code className="text-zinc-300 font-mono">{DEMO_PASSWORD}</code>
          </p>
        </section>
      </div>
    </main>
  );
}
