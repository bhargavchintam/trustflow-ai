import type {
  EvalDashboardData,
  HealthStatus,
  HistoryResponse,
  MemoryAll,
  RouteDecision,
  TraceEvent,
} from "./types";
import { getAccessToken } from "./useAuth";

export const API_BASE =
  typeof window === "undefined"
    ? ""
    : process.env.NEXT_PUBLIC_API_BASE ?? "";

async function headers(
  tenant: string,
  user: string,
  sessionId: string,
): Promise<HeadersInit> {
  const h: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
    "X-Tenant-Id": tenant,
    "X-User-Id": user,
    "X-Session-Id": sessionId,
  };
  const token = await getAccessToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

export interface ChatStreamMessage {
  content: string;
  latency_ms: number;
  message_id: string;
  session_id: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  cost_usd?: number;
}

export interface StreamResult {
  route?: RouteDecision;
  message?: ChatStreamMessage;
}

export async function streamChat(opts: {
  tenant: string;
  user: string;
  sessionId: string;
  input: string;
  forceRoute?: "dag" | "react";
  onRoute?: (r: RouteDecision) => void;
  onDelta?: (text: string) => void;
  onPhase?: (phase: string) => void;
  onMessage?: (m: ChatStreamMessage) => void;
  onDone?: () => void;
}): Promise<StreamResult> {
  const body = JSON.stringify({ input: opts.input, force_route: opts.forceRoute ?? null });
  const r = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: await headers(opts.tenant, opts.user, opts.sessionId),
    body,
  });
  if (!r.ok || !r.body) throw new Error(`chat failed: ${r.status}`);

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastEvent = "message";
  const out: StreamResult = {};

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        lastEvent = line.slice("event: ".length).trim();
      } else if (line.startsWith("data: ")) {
        let data: any;
        try {
          data = JSON.parse(line.slice("data: ".length));
        } catch {
          continue;
        }
        if (lastEvent === "route") {
          out.route = data;
          opts.onRoute?.(data);
        } else if (lastEvent === "delta") {
          opts.onDelta?.(data.text ?? "");
        } else if (lastEvent === "phase") {
          opts.onPhase?.(data.phase ?? "");
        } else if (lastEvent === "message") {
          out.message = data;
          opts.onMessage?.(data);
        } else if (lastEvent === "done") {
          opts.onDone?.();
        }
      }
    }
  }
  return out;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const r = await fetch(`${API_BASE}/healthz`, { cache: "no-store" });
  if (!r.ok) {
    return {
      status: "error",
      db: { ok: false },
      llm: { ok: false },
      embedding: { ok: false },
    };
  }
  return (await r.json()) as HealthStatus;
}

export async function fetchMemory(
  tenant: string,
  user: string,
  sessionId: string,
): Promise<MemoryAll> {
  const r = await fetch(`${API_BASE}/api/memory?tier=all`, {
    headers: await headers(tenant, user, sessionId),
  });
  if (!r.ok) throw new Error(`memory failed: ${r.status}`);
  return r.json();
}

export async function fetchTrace(
  tenant: string,
  user: string,
  sessionId: string,
  messageId: string,
): Promise<TraceEvent[]> {
  const r = await fetch(`${API_BASE}/api/trace?message_id=${messageId}`, {
    headers: await headers(tenant, user, sessionId),
  });
  if (!r.ok) throw new Error(`trace failed: ${r.status}`);
  return (await r.json()).events as TraceEvent[];
}

export async function fetchHistory(
  tenant: string,
  user: string,
  sessionId: string,
  limit = 100,
): Promise<HistoryResponse> {
  const r = await fetch(
    `${API_BASE}/api/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`,
    { headers: await headers(tenant, user, sessionId) },
  );
  if (!r.ok) throw new Error(`history failed: ${r.status}`);
  return r.json();
}

export interface BackendAuthResponse {
  access_token: string;
  refresh_token: string | null;
  user: { id: string | null; email: string | null };
  identity: { tenant_id: string; user_id: string; session_id: string; role: string };
}

export async function backendSignUp(
  email: string,
  password: string,
): Promise<BackendAuthResponse> {
  const r = await fetch(`${API_BASE}/api/auth/sign-up`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const text = await r.text();
    let detail = `sign-up failed: ${r.status}`;
    try {
      const j = JSON.parse(text);
      if (j?.detail) detail = String(j.detail);
    } catch {}
    throw new Error(detail);
  }
  return r.json();
}

export async function fetchEval(): Promise<EvalDashboardData> {
  const r = await fetch(`${API_BASE}/api/eval`);
  if (!r.ok) throw new Error(`eval failed: ${r.status}`);
  return r.json();
}

export async function triggerEvalRun(): Promise<void> {
  await fetch(`${API_BASE}/api/eval/run`, { method: "POST" });
}

export async function reseedAll(): Promise<void> {
  await fetch(`${API_BASE}/api/seed`, { method: "POST" });
}

export async function wipeUser(tenant: string, user: string, sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/api/reset`, {
    method: "POST",
    headers: await headers(tenant, user, sessionId),
  });
}

export async function warmup(): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/warmup`);
  } catch {
    // ignore
  }
}
