"use client";

import { useEffect, useState } from "react";
import { fetchTrace } from "@/lib/api";
import type { TraceEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

export function TracePanel({
  tenant,
  user,
  sessionId,
  messageId,
}: {
  tenant: string;
  user: string;
  sessionId: string;
  messageId: string;
}) {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<TraceEvent[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || events) return;
    setLoading(true);
    fetchTrace(tenant, user, sessionId, messageId)
      .then((evs) => setEvents(evs))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [open, events, tenant, user, sessionId, messageId]);

  return (
    <div className="mt-2 text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-zinc-400 hover:text-zinc-200 inline-flex items-center gap-1"
      >
        <span className="opacity-60">{open ? "▾" : "▸"}</span>
        Why?
      </button>
      {open && (
        <div className="mt-2 border border-border rounded-md p-2 bg-bg/60 font-mono text-[11px] leading-relaxed">
          {loading && <div className="opacity-70">Loading trace…</div>}
          {!loading && events && events.length === 0 && (
            <div className="opacity-70">No trace events for this message yet.</div>
          )}
          {!loading && events && events.length > 0 && (
            <ol className="space-y-1">
              {events.map((e, i) => (
                <li key={e.id} className="flex items-start gap-2">
                  <span className="opacity-50 w-5">{i + 1}.</span>
                  <span className={cn("flex-1", decisionColor(e.decision))}>
                    <span className="font-semibold">{e.event_type}</span>
                    {e.decision && (
                      <span className="opacity-80"> · {e.decision}</span>
                    )}
                    {e.reason && <span className="opacity-70"> · {e.reason}</span>}
                    <PayloadSummary e={e} />
                    {e.latency_ms != null && (
                      <span className="opacity-60"> · {e.latency_ms}ms</span>
                    )}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

function decisionColor(d?: string | null): string {
  if (d === "deny") return "text-deny";
  if (d === "hitl") return "text-warn";
  if (d === "allow") return "text-ok";
  return "text-zinc-300";
}

function asText(v: unknown): string {
  return v === null || v === undefined ? "" : String(v);
}

function PayloadSummary({ e }: { e: TraceEvent }) {
  const p = e.payload || {};
  if (e.event_type === "route") {
    return (
      <span className="opacity-80">
        {" "}
        · route={asText(p.route)} {p.intent ? `intent=${asText(p.intent)}` : ""}
      </span>
    );
  }
  if (e.event_type === "memory_read") {
    return (
      <span className="opacity-80">
        {" "}
        · ep={asText(p.tier_episodic_hits)} sem={asText(p.tier_semantic_hits)} proc={asText(p.tier_procedural_hits)}
      </span>
    );
  }
  if (e.event_type === "tool_call" || e.event_type === "policy") {
    return <span className="opacity-80"> · tool={asText(p.tool)}</span>;
  }
  if (e.event_type === "llm_call") {
    const costUsd = p.cost_usd as number | undefined;
    return (
      <span className="opacity-80">
        {" "}
        · in={asText(p.input_tokens)} out={asText(p.output_tokens)} {costUsd ? `$${costUsd.toFixed(5)}` : ""}
      </span>
    );
  }
  if (e.event_type === "memory_write") {
    return <span className="opacity-80"> · tier={asText(p.tier)}</span>;
  }
  return null;
}
