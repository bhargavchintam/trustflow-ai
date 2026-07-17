"use client";

import { useTrace } from "@/lib/useTrace";

export function MemoryWriteSummary({
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
  const { events } = useTrace(tenant, user, sessionId, messageId, true);
  if (!events) return null;
  const writes = events.filter((e) => e.event_type === "memory_write");
  if (writes.length === 0) return null;
  const tally: Record<string, number> = {};
  for (const w of writes) {
    const tier = (w.payload?.tier as string | undefined) ?? "unknown";
    tally[tier] = (tally[tier] ?? 0) + 1;
  }
  const parts = Object.entries(tally).map(([tier, n]) => `${n} ${tier}`);
  return (
    <div className="mt-1.5 text-[11px] text-muted leading-snug">
      <span className="opacity-70">Saved to shared context store:</span>{" "}
      {parts.join(" · ")}. Available on the next turn for any session of this user.
    </div>
  );
}
