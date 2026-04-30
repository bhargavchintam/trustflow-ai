import type { RouteDecision } from "@/lib/types";

export function RouteExplainer({ route }: { route?: RouteDecision }) {
  if (!route) return null;
  const text = explain(route);
  return (
    <div className="text-[11px] text-muted italic mb-1.5 leading-snug">
      {text}
    </div>
  );
}

function explain(route: RouteDecision): string {
  if (route.matched_by === "forced") {
    return "Force-ReAct enabled — bypassing the deterministic router for comparison.";
  }
  if (route.route === "dag") {
    const intent = route.intent ?? "dag";
    return `Coordinator routed to deterministic ${intent} flow (matched ${route.matched_by}).`;
  }
  return "No deterministic match — coordinator handed off to ReAct (max 4 iterations, shared context store).";
}
