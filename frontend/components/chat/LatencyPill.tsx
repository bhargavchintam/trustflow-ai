import { cn } from "@/lib/utils";

export function LatencyPill({
  ms,
  promptTokens,
  completionTokens,
  costUsd,
}: {
  ms?: number;
  promptTokens?: number;
  completionTokens?: number;
  costUsd?: number;
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
    </span>
  );
}
