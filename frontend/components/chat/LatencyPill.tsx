import { cn } from "@/lib/utils";

export function LatencyPill({ ms }: { ms?: number }) {
  if (ms == null) return null;
  const fast = ms < 800;
  const slow = ms > 4000;
  return (
    <span
      className={cn(
        "pill",
        fast
          ? "border-ok/60 text-ok bg-ok/10"
          : slow
            ? "border-warn/60 text-warn bg-warn/10"
            : "border-zinc-600 text-zinc-300 bg-zinc-800/40",
      )}
    >
      {ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`}
    </span>
  );
}
