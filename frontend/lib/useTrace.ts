"use client";

import { useEffect, useState } from "react";
import { fetchTrace } from "./api";
import type { TraceEvent } from "./types";

const cache = new Map<string, TraceEvent[]>();

export function useTrace(
  tenant: string,
  user: string,
  sessionId: string,
  messageId: string | undefined,
  enabled: boolean,
): { events: TraceEvent[] | null; loading: boolean } {
  const [events, setEvents] = useState<TraceEvent[] | null>(
    messageId && cache.has(messageId) ? cache.get(messageId)! : null,
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled || !messageId) return;
    if (cache.has(messageId)) {
      setEvents(cache.get(messageId)!);
      return;
    }
    setLoading(true);
    let cancelled = false;
    fetchTrace(tenant, user, sessionId, messageId)
      .then((evs) => {
        if (cancelled) return;
        cache.set(messageId, evs);
        setEvents(evs);
      })
      .catch(() => {
        if (cancelled) return;
        setEvents([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, messageId, tenant, user, sessionId]);

  return { events, loading };
}
