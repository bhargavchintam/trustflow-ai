import { cn } from "@/lib/utils";
import type { RouteName } from "@/lib/types";

const DAG_AVG_MS = 700;
const REACT_AVG_MS = 4500;

export function LatencyPill({
  ms,
  promptTokens,
  completionTokens,
  costUsd,
  route,
}: {
  ms?: number;
  promptTokens?: number;
  completionTokens?: number;
  costUsd?: number;
  route?: RouteName;
}) {
  if (ms == null) return null;
  const fast = ms < 800;
  const slow = ms > 4000;
  const hasCost = (promptTokens ?? 0) + (completionTokens ?? 0) > 0;
  const tooltipParts: string[] = [];
  if (hasCost) {
    if (promptTokens != null) tooltipParts.push(`input: ${promptTokens} tok`);
    if (completionTokens != null) tooltipParts.push(`output: ${completionTokens} tok`);
    if (costUsd != null) tooltipParts.push(`$${costUsd.toFixed(6)}`);
  }
  const tooltip = tooltipParts.length > 0 ? tooltipParts.join(" · ") : undefined;
  const compare = comparison(ms, route);
  return (
    <span
      className={cn(
        "pill",
        fast
          ? "border-ok/60 text-ok bg-ok/10"
          : slow
            ? "border-warn/60 text-warn bg-warn/10"
            : "border-zinc-600 text-zinc-300 bg-zinc-800/40",
        tooltip && "cursor-help",
      )}
      title={tooltip}
    >
      {ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`}
      {hasCost && costUsd != null && costUsd > 0 && (
        <span className="ml-1 opacity-70">${costUsd.toFixed(4)}</span>
      )}
      {compare && <span className="ml-1 opacity-70">· {compare}</span>}
    </span>
  );
}

function comparison(ms: number, route?: RouteName): string | null {
  if (!route) return null;
  if (route === "dag") {
    const ratio = REACT_AVG_MS / Math.max(ms, 1);
    if (ratio >= 1.5) return `${ratio.toFixed(1)}× faster than ReAct`;
    return null;
  }
  if (ms <= 5000) return "within ReAct budget";
  return "above ReAct budget";
}
