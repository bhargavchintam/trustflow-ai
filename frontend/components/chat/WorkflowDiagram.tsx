"use client";

import { ChevronRight, RotateCw } from "lucide-react";
import type { RouteDecision, TraceEvent } from "@/lib/types";
import { useTrace } from "@/lib/useTrace";
import { cn } from "@/lib/utils";

type Tone = "ok" | "deny" | "hitl" | "muted" | "accent";

const TONES: Record<Tone, string> = {
  ok: "border-ok/50 text-ok bg-ok/10",
  deny: "border-deny/50 text-deny bg-deny/10",
  hitl: "border-warn/50 text-warn bg-warn/10",
  muted: "border-zinc-600 text-zinc-300 bg-zinc-800/40",
  accent: "border-accent/50 text-accent bg-accent/10",
};

interface DagNode {
  label: string;
  tone: Tone;
  detail?: string;
}

interface ReactNode {
  label: string;
  tone: Tone;
  detail?: string;
}

export function WorkflowDiagram({
  route,
  tenant,
  user,
  sessionId,
  messageId,
}: {
  route?: RouteDecision;
  tenant: string;
  user: string;
  sessionId: string;
  messageId?: string;
}) {
  const enabled = !!messageId;
  const { events, loading } = useTrace(tenant, user, sessionId, messageId, enabled);

  if (!route || !messageId) return null;

  const isDag = route.route === "dag";
  if (loading && !events) {
    return (
      <div className="mt-2 text-[11px] text-muted italic">Building workflow…</div>
    );
  }
  const trace = events ?? [];

  return (
    <div className="mt-2 border border-border rounded-md p-2 bg-bg/40">
      <div className="flex items-center justify-between mb-1.5">
        <div className="text-[10px] uppercase tracking-wider text-muted">
          {isDag ? "Deterministic DAG flow" : "ReAct reasoning loop"}
        </div>
        <div className="text-[10px] text-subtle">
          matched_by={route.matched_by}
          {route.intent && <> · {route.intent}</>}
        </div>
      </div>
      {isDag ? <DagFlow route={route} trace={trace} /> : <ReactLoop trace={trace} />}
    </div>
  );
}

function DagFlow({ route, trace }: { route: RouteDecision; trace: TraceEvent[] }) {
  const nodes = buildDagNodes(route, trace);
  return (
    <div className="flex items-center flex-wrap gap-1">
      {nodes.map((n, i) => (
        <div key={i} className="flex items-center gap-1">
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded border text-[11px]",
              TONES[n.tone],
            )}
            title={n.detail}
          >
            {n.label}
          </span>
          {i < nodes.length - 1 && (
            <ChevronRight className="w-3 h-3 text-zinc-500" />
          )}
        </div>
      ))}
    </div>
  );
}

function ReactLoop({ trace }: { trace: TraceEvent[] }) {
  const { nodes, iterations } = buildReactNodes(trace);
  return (
    <div className="flex items-center flex-wrap gap-1">
      {nodes.map((n, i) => (
        <div key={i} className="flex items-center gap-1">
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded border text-[11px]",
              TONES[n.tone],
            )}
            title={n.detail}
          >
            {n.label}
          </span>
          {i < nodes.length - 1 && (
            <ChevronRight className="w-3 h-3 text-zinc-500" />
          )}
        </div>
      ))}
      {iterations > 1 && (
        <span className="ml-1 inline-flex items-center gap-1 text-[10px] text-muted">
          <RotateCw className="w-3 h-3" /> ×{iterations}
        </span>
      )}
    </div>
  );
}

function buildDagNodes(route: RouteDecision, trace: TraceEvent[]): DagNode[] {
  const nodes: DagNode[] = [
    { label: `route: ${route.intent ?? "dag"}`, tone: "accent", detail: `matched_by=${route.matched_by}` },
  ];
  const policy = trace.find((e) => e.event_type === "policy");
  const tools = trace.filter((e) => e.event_type === "tool_call");
  if (policy) {
    const tone: Tone = policy.decision === "deny" ? "deny" : policy.decision === "hitl" ? "hitl" : "ok";
    nodes.push({
      label: `policy: ${policy.decision ?? "checked"}`,
      tone,
      detail: policy.reason ?? undefined,
    });
  }
  if (tools.length === 0) {
    nodes.push({ label: "templated response", tone: "muted" });
  } else {
    for (const t of tools) {
      const tone: Tone = t.decision === "deny" ? "deny" : t.decision === "hitl" ? "hitl" : "ok";
      const tool = (t.payload || {}).tool || "tool";
      nodes.push({ label: `tool: ${tool}`, tone, detail: t.reason ?? undefined });
    }
  }
  const writes = trace.filter((e) => e.event_type === "memory_write");
  if (writes.length > 0) {
    nodes.push({
      label: `write × ${writes.length}`,
      tone: "muted",
      detail: writes.map((w) => (w.payload || {}).tier).filter(Boolean).join(", "),
    });
  }
  return nodes;
}

function buildReactNodes(trace: TraceEvent[]): { nodes: ReactNode[]; iterations: number } {
  const nodes: ReactNode[] = [{ label: "triage", tone: "accent" }];
  const reads = trace.filter((e) => e.event_type === "memory_read");
  if (reads.length > 0) {
    const totalHits = reads.reduce((s, r) => {
      const p = r.payload || {};
      return (
        s +
        (Number(p.tier_episodic_hits || 0) +
          Number(p.tier_semantic_hits || 0) +
          Number(p.tier_procedural_hits || 0))
      );
    }, 0);
    nodes.push({
      label: `retrieve · ${totalHits} hits`,
      tone: totalHits > 0 ? "accent" : "muted",
      detail: reads.map((r) => `${r.payload?.tier ?? ""}=${r.payload?.hit_count ?? ""}`).join(" "),
    });
  } else {
    nodes.push({ label: "retrieve", tone: "muted" });
  }
  const tools = trace.filter((e) => e.event_type === "tool_call");
  for (const t of tools) {
    const tone: Tone = t.decision === "deny" ? "deny" : t.decision === "hitl" ? "hitl" : "ok";
    nodes.push({
      label: `tool: ${(t.payload || {}).tool ?? "tool"}`,
      tone,
      detail: t.reason ?? undefined,
    });
  }
  const llmCalls = trace.filter((e) => e.event_type === "llm_call");
  const iterations = Math.max(1, llmCalls.length);
  nodes.push({ label: `diagnose × ${iterations}`, tone: "accent" });
  nodes.push({ label: "resolve", tone: "ok" });
  const writes = trace.filter((e) => e.event_type === "memory_write");
  if (writes.length > 0) {
    nodes.push({
      label: `memwrite × ${writes.length}`,
      tone: "muted",
      detail: writes.map((w) => (w.payload || {}).tier).filter(Boolean).join(", "),
    });
  }
  return { nodes, iterations };
}
