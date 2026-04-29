"use client";

import { useEffect, useRef, useState } from "react";
import { fetchMemory } from "@/lib/api";
import type { MemoryAll } from "@/lib/types";
import { cn, getOrCreateSessionId } from "@/lib/utils";

type Tab = "episodic" | "semantic" | "procedural";

export function MemoryInspector({
  tenant,
  user,
  label,
  refreshKey,
}: {
  tenant: string;
  user: string;
  label: string;
  refreshKey?: number;
}) {
  const [tab, setTab] = useState<Tab>("episodic");
  const [data, setData] = useState<MemoryAll | null>(null);
  const [flash, setFlash] = useState<Record<string, boolean>>({});
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    let alive = true;
    const sid = getOrCreateSessionId(user);

    async function tick() {
      try {
        const m = await fetchMemory(tenant, user, sid);
        if (!alive) return;
        const newSeen = new Set(seen.current);
        const flashing: Record<string, boolean> = {};
        for (const tier of ["episodic", "semantic", "procedural"] as const) {
          for (const r of m[tier]) {
            const key = `${tier}:${r.id}`;
            if (!newSeen.has(key)) {
              flashing[key] = true;
              newSeen.add(key);
            }
          }
        }
        seen.current = newSeen;
        setData(m);
        if (Object.keys(flashing).length) {
          setFlash((f) => ({ ...f, ...flashing }));
          setTimeout(() => {
            setFlash((f) => {
              const next = { ...f };
              for (const k of Object.keys(flashing)) delete next[k];
              return next;
            });
          }, 3000);
        }
      } catch {
        // network blip; keep last data
      }
    }

    tick();
    const id = setInterval(tick, 2500);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [tenant, user, refreshKey]);

  return (
    <div className="card flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-semibold">{label} memory</div>
        <div className="flex gap-1">
          {(["episodic", "semantic", "procedural"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "btn text-xs",
                tab === t && "border-accent text-accent",
              )}
            >
              {t}
              <span className="ml-1 opacity-60">
                {data ? data[t].length : 0}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-y-auto max-h-72 text-xs space-y-1.5">
        {!data && <div className="text-muted">Loading…</div>}
        {data && tab === "episodic" && (
          <EpisodicList rows={data.episodic} flash={flash} />
        )}
        {data && tab === "semantic" && (
          <SemanticList rows={data.semantic} flash={flash} />
        )}
        {data && tab === "procedural" && (
          <ProceduralList rows={data.procedural} flash={flash} />
        )}
      </div>
    </div>
  );
}

function EpisodicList({
  rows,
  flash,
}: {
  rows: MemoryAll["episodic"];
  flash: Record<string, boolean>;
}) {
  if (rows.length === 0) return <div className="text-muted py-2">empty</div>;
  return (
    <ul>
      {rows.map((r) => (
        <li
          key={r.id}
          className={cn(
            "py-1.5 px-2 rounded border border-border",
            flash[`episodic:${r.id}`] && "row-flash",
          )}
        >
          <div className="flex items-center gap-2 mb-0.5">
            <span
              className={cn(
                "pill text-[10px]",
                r.role === "user"
                  ? "border-accent/50 text-accent"
                  : "border-zinc-600 text-zinc-300",
              )}
            >
              {r.role}
            </span>
            <span className="text-[10px] text-muted">
              {new Date(r.created_at).toLocaleTimeString()}
            </span>
          </div>
          <div className="text-zinc-200">{r.content}</div>
        </li>
      ))}
    </ul>
  );
}

function SemanticList({
  rows,
  flash,
}: {
  rows: MemoryAll["semantic"];
  flash: Record<string, boolean>;
}) {
  if (rows.length === 0) return <div className="text-muted py-2">empty</div>;
  return (
    <ul>
      {rows.map((r) => (
        <li
          key={r.id}
          className={cn(
            "py-1.5 px-2 rounded border border-border",
            flash[`semantic:${r.id}`] && "row-flash",
          )}
        >
          <div className="text-zinc-200">{r.fact}</div>
          <div className="mt-0.5 flex gap-2 text-[10px] text-muted">
            <span>conf {r.confidence.toFixed(2)}</span>
            <span>×{r.corroboration_count}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function ProceduralList({
  rows,
  flash,
}: {
  rows: MemoryAll["procedural"];
  flash: Record<string, boolean>;
}) {
  if (rows.length === 0) return <div className="text-muted py-2">empty</div>;
  return (
    <ul className="space-y-2">
      {rows.map((r) => (
        <li
          key={r.id}
          className={cn(
            "py-2 px-2 rounded border border-border",
            flash[`procedural:${r.id}`] && "row-flash",
            r.last_used_at && "glow-procedural",
          )}
        >
          <div className="text-accent font-medium">{r.problem_signature}</div>
          <div className="text-[10px] text-muted">
            success_count={r.success_count}
            {r.last_used_at && (
              <> · last_used={new Date(r.last_used_at).toLocaleString()}</>
            )}
          </div>
          <ol className="mt-1 list-decimal list-inside space-y-0.5 text-zinc-300">
            {r.steps?.map((s, i) => (
              <li key={i}>
                {s.action}
                {s.tool && (
                  <span className="ml-1 text-[10px] text-muted">via {s.tool}</span>
                )}
              </li>
            ))}
          </ol>
        </li>
      ))}
    </ul>
  );
}
