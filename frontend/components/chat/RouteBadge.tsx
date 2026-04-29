import type { RouteDecision } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RouteBadge({ route }: { route?: RouteDecision }) {
  if (!route) return null;
  const isDag = route.route === "dag";
  return (
    <span
      className={cn(
        "pill",
        isDag
          ? "border-accent/60 text-accent bg-accent/10"
          : "border-zinc-600 text-zinc-300 bg-zinc-800/40",
      )}
      title={`matched_by=${route.matched_by} confidence=${route.confidence.toFixed(2)}`}
    >
      <span className="font-medium">{isDag ? "DAG" : "ReAct"}</span>
      {route.intent && <span className="opacity-80">· {route.intent}</span>}
    </span>
  );
}
