"use client";

import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api";
import type { HealthStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function HealthDot() {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const h = await fetchHealth();
        if (alive) setHealth(h);
      } catch {
        if (alive)
          setHealth({
            status: "error",
            db: { ok: false },
            llm: { ok: false },
            embedding: { ok: false },
          });
      }
    }
    tick();
    const id = setInterval(tick, 30_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const color =
    health == null
      ? "bg-zinc-600"
      : health.status === "ok"
        ? "bg-ok"
        : health.status === "degraded"
          ? "bg-warn"
          : "bg-deny";

  const label =
    health == null
      ? "checking…"
      : health.status === "ok"
        ? "all systems ok"
        : health.status === "degraded"
          ? "degraded"
          : "error";

  const tooltip = health
    ? [
        `status: ${health.status}`,
        `db: ${health.db.ok ? "ok" : `down — ${health.db.msg ?? ""}`}`,
        `llm: ${health.llm.ok ? "ok" : `down — ${health.llm.msg ?? ""}`}`,
        `embedding: ${health.embedding.ok ? "ok" : `down — ${health.embedding.msg ?? ""}`}`,
      ].join("\n")
    : "checking…";

  return (
    <span
      className="inline-flex items-center gap-1.5 cursor-help"
      title={tooltip}
    >
      <span
        className={cn(
          "inline-block w-2 h-2 rounded-full",
          color,
          health?.status === "ok" && "shadow-[0_0_6px_rgba(22,163,74,0.6)]",
        )}
      />
      <span className="text-xs text-muted">{label}</span>
    </span>
  );
}
