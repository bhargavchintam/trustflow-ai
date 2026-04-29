// Mirrors backend/app/models.py — kept in sync by hand (per CLAUDE.md conventions).

export type Role = "user" | "assistant" | "tool" | "system";
export type RouteName = "dag" | "react";
export type IdentityRole = "employee" | "executive" | "admin";

export interface Identity {
  tenant_id: string;
  user_id: string;
  session_id: string;
  role: IdentityRole;
}
export type EventType =
  | "route"
  | "policy"
  | "tool_call"
  | "memory_read"
  | "memory_write"
  | "llm_call";

export interface RouteDecision {
  route: RouteName;
  intent?: string | null;
  confidence: number;
  matched_by: "keyword" | "llm" | "fallback" | "forced";
  message_id?: string;
  session_id?: string;
  correlation_id?: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  route?: RouteDecision;
  latencyMs?: number;
  messageId?: string;
  promptTokens?: number;
  completionTokens?: number;
  costUsd?: number;
  streaming?: boolean;
  phase?: string;
}

export interface HealthStatus {
  status: "ok" | "degraded" | "error" | "unknown";
  db: { ok: boolean; msg?: string };
  llm: { ok: boolean; msg?: string };
  embedding: { ok: boolean; msg?: string };
}

export interface TraceEvent {
  id: string;
  correlation_id: string;
  tenant_id: string;
  user_id: string;
  session_id: string;
  message_id: string;
  event_type: EventType;
  payload: Record<string, any>;
  decision?: "allow" | "deny" | "hitl" | null;
  reason?: string | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface EpisodicRow {
  id: string;
  role: string;
  content: string;
  created_at: string;
  session_id?: string;
}

export interface SemanticRow {
  id: string;
  fact: string;
  confidence: number;
  corroboration_count: number;
  last_updated_at: string;
}

export interface ProceduralRow {
  id: string;
  problem_signature: string;
  steps: Array<{ action: string; tool?: string | null }>;
  success_count: number;
  last_used_at?: string | null;
}

export interface MemoryAll {
  episodic: EpisodicRow[];
  semantic: SemanticRow[];
  procedural: ProceduralRow[];
}

export interface EvalSummary {
  routing?: { passed: number; total: number; rate: number };
  security?: { passed: number; total: number; rate: number };
  memory?: { passed: number; total: number; rate: number };
  tenant_isolation?: { passed: number; total: number; rate: number };
  latency_p50_ms?: number;
  latency_p95_ms?: number;
  avg_cost_usd?: number;
  total_cases?: number;
  total_passed?: number;
}

export interface EvalCase {
  category: string;
  case_id: string;
  input: string;
  expected: any;
  actual: any;
  passed: boolean;
  latency_ms?: number;
  cost_usd?: number;
  created_at?: string;
}

export interface EvalDashboardData {
  run_id: string | null;
  summary: EvalSummary | null;
  cases: EvalCase[];
}
