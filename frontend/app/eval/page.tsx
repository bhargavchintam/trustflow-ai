"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchEval, triggerEvalRun } from "@/lib/api";
import type { EvalDashboardData } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function EvalPage() {
  const [data, setData] = useState<EvalDashboardData | null>(null);
  const [running, setRunning] = useState(false);

  async function load() {
    try {
      const d = await fetchEval();
      setData(d);
    } catch {}
  }

  useEffect(() => {
    load();
  }, []);

  async function rerun() {
    setRunning(true);
    try {
      await triggerEvalRun();
      let attempts = 0;
      const id = setInterval(async () => {
        attempts++;
        await load();
        if (attempts > 30) clearInterval(id);
      }, 4000);
      setTimeout(() => {
        clearInterval(id);
        setRunning(false);
      }, 130_000);
    } catch {
      setRunning(false);
    }
  }

  return (
    <main className="max-w-5xl mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Eval Dashboard</h1>
          <p className="text-muted text-sm mt-1">
            Synthetic eval suite — measured numbers, not asserted ones.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/" className="btn">
            ← Back to chat
          </Link>
          <button onClick={rerun} disabled={running} className="btn-accent">
            {running ? "Re-running…" : "Re-run evals"}
          </button>
        </div>
      </header>

      {!data && <div className="text-muted">Loading…</div>}
      {data && !data.run_id && (
        <div className="card text-sm text-muted">
          No eval results yet. Click <em>Re-run evals</em> to generate the first run, or run
          locally with <code>uv run python -m app.evals.run_evals</code>.
        </div>
      )}

      {data && data.summary && (
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Stat
            label="Routing accuracy"
            n={data.summary.routing?.passed}
            d={data.summary.routing?.total}
            rate={data.summary.routing?.rate}
            critical={false}
          />
          <Stat
            label="Policy decisions (block/allow)"
            n={data.summary.security?.passed}
            d={data.summary.security?.total}
            rate={data.summary.security?.rate}
            critical
          />
          <Stat
            label="Cross-tenant isolation"
            n={data.summary.tenant_isolation?.passed}
            d={data.summary.tenant_isolation?.total}
            rate={data.summary.tenant_isolation?.rate}
            critical
          />
          <Stat
            label="Memory recall/precision"
            n={data.summary.memory?.passed}
            d={data.summary.memory?.total}
            rate={data.summary.memory?.rate}
            critical={false}
          />
          <div className="card col-span-2">
            <div className="text-xs text-muted mb-1">Latency</div>
            <div className="font-mono">
              p50 {data.summary.latency_p50_ms ?? 0}ms · p95 {data.summary.latency_p95_ms ?? 0}ms
            </div>
          </div>
          <div className="card col-span-2">
            <div className="text-xs text-muted mb-1">Cost / request (avg)</div>
            <div className="font-mono">
              ${(data.summary.avg_cost_usd ?? 0).toFixed(6)}
            </div>
          </div>
        </section>
      )}

      {data && data.cases.length > 0 && (
        <section className="card">
          <div className="text-sm font-semibold mb-3">Cases (run {data.run_id})</div>
          <table className="w-full text-xs">
            <thead className="text-muted">
              <tr className="text-left">
                <th className="py-1">status</th>
                <th>category</th>
                <th>id</th>
                <th>input</th>
                <th>summary</th>
                <th>ms</th>
              </tr>
            </thead>
            <tbody>
              {data.cases.map((c) => (
                <tr key={c.case_id} className="border-t border-border align-top">
                  <td className="py-1.5">
                    <span
                      className={cn(
                        "pill text-[10px]",
                        c.passed
                          ? "border-ok/50 text-ok bg-ok/10"
                          : "border-deny/50 text-deny bg-deny/10",
                      )}
                    >
                      {c.passed ? "PASS" : "FAIL"}
                    </span>
                  </td>
                  <td className="py-1.5 opacity-80">{c.category}</td>
                  <td className="py-1.5 font-mono opacity-80">{c.case_id}</td>
                  <td className="py-1.5">{c.input}</td>
                  <td className="py-1.5 opacity-80 font-mono">
                    {(c.actual as any)?.summary ?? "—"}
                  </td>
                  <td className="py-1.5 opacity-80">{c.latency_ms ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}

function Stat({
  label,
  n,
  d,
  rate,
  critical,
}: {
  label: string;
  n?: number;
  d?: number;
  rate?: number;
  critical: boolean;
}) {
  const pct = rate != null ? Math.round(rate * 100) : null;
  const color =
    pct == null
      ? "text-zinc-300"
      : critical && pct < 100
        ? "text-deny"
        : pct >= 90
          ? "text-ok"
          : "text-warn";
  return (
    <div className="card">
      <div className="text-xs text-muted mb-1">{label}</div>
      <div className={cn("text-xl font-semibold", color)}>
        {n ?? 0}/{d ?? 0}
        {pct != null && (
          <span className="ml-2 text-sm opacity-80">({pct}%)</span>
        )}
      </div>
    </div>
  );
}
