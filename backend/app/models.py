from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

Role = Literal["user", "assistant", "tool", "system"]
Tier = Literal["episodic", "semantic", "procedural"]
RouteName = Literal["dag", "react"]
PolicyDecisionLiteral = Literal["allow", "deny", "hitl"]
EventType = Literal["route", "policy", "tool_call", "memory_read", "memory_write", "llm_call"]


class Identity(BaseModel):
    tenant_id: str
    user_id: str
    session_id: str
    role: Literal["employee", "executive", "admin"] = "employee"


class ChatRequest(BaseModel):
    input: str
    force_route: RouteName | None = None


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    proposed_by: RouteName | None = None


class ToolResult(BaseModel):
    blocked: bool = False
    hitl: bool = False
    error: bool = False
    reason: str | None = None
    data: dict[str, Any] | None = None


class PolicyDecision(BaseModel):
    decision: PolicyDecisionLiteral
    reason: str


class RouteDecision(BaseModel):
    route: RouteName
    intent: str | None = None
    confidence: float = 0.0
    matched_by: Literal["keyword", "llm", "fallback", "forced"] = "fallback"


class TraceEvent(BaseModel):
    id: UUID | None = None
    correlation_id: UUID
    tenant_id: str
    user_id: str
    session_id: str
    message_id: UUID
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    decision: PolicyDecisionLiteral | None = None
    reason: str | None = None
    latency_ms: int | None = None
    created_at: datetime | None = None


class EpisodicRow(BaseModel):
    id: UUID
    tenant_id: str
    user_id: str
    session_id: str
    role: Role
    content: str
    embedding_status: str = "ok"
    created_at: datetime


class SemanticRow(BaseModel):
    id: UUID
    tenant_id: str
    user_id: str
    fact: str
    confidence: float
    corroboration_count: int
    last_updated_at: datetime
    created_at: datetime


class ProceduralRow(BaseModel):
    id: UUID
    tenant_id: str
    problem_signature: str
    steps: list[dict[str, Any]]
    success_count: int
    last_used_at: datetime | None
    created_at: datetime


class TicketRow(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    action: str
    status: str
    created_at: datetime


class EvalCase(BaseModel):
    id: str
    category: Literal["routing", "security", "memory", "tenant_isolation"]
    input: str
    user: str | None = None
    tenant: str | None = None
    expected: dict[str, Any] = Field(default_factory=dict)


class EvalSummary(BaseModel):
    run_id: str
    routing_accuracy: float
    security_block_rate: float
    cross_tenant_block_rate: float
    memory_recall: float
    memory_precision: float
    latency_p50_ms: int
    latency_p95_ms: int
    cost_per_request_usd: float
    total_cases: int
    total_passed: int
    last_run_at: datetime
