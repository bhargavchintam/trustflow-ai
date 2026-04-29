"""Tool Gateway — the only execution path for tools.

The LLM may only PROPOSE tool calls (in <tool_call> blocks). The orchestrator parses
those, constructs ToolCall objects, and calls execute() here. This module:
1. Looks up the policy rule for the proposed tool.
2. Decides allow / deny / hitl.
3. Writes a `policy` audit event before execution.
4. If allowed, runs the tool from the registry.
5. Writes a `tool_call` audit event after.

Bypassing this module is a CRITICAL security violation (caught by the policy-auditor agent).
"""
from __future__ import annotations

import time
from uuid import UUID, uuid4

from app.audit.logger import log_event
from app.models import Identity, PolicyDecision, ToolCall, ToolResult
from app.policy.rules import POLICY_RULES, deny_reason
from app.tools.registry import TOOL_REGISTRY


def check_policy(call: ToolCall, identity: Identity) -> PolicyDecision:
    rule = POLICY_RULES.get(call.tool)
    if rule is None:
        return PolicyDecision(decision="deny", reason=f"Tool '{call.tool}' is not registered")

    target = call.args.get("target_user", identity.user_id)
    max_target = rule.get("max_target_user", "self")

    if max_target == "self" and target != identity.user_id:
        return PolicyDecision(
            decision="deny",
            reason=deny_reason(call.tool, call.args, identity.user_id, identity.role),
        )
    if isinstance(max_target, list) and target not in max_target:
        return PolicyDecision(
            decision="deny",
            reason=deny_reason(call.tool, call.args, identity.user_id, identity.role),
        )

    hitl_roles = rule.get("requires_hitl_for", [])
    if identity.role in hitl_roles:
        return PolicyDecision(
            decision="hitl",
            reason=f"{call.tool} requires admin approval for role={identity.role}",
        )

    return PolicyDecision(decision="allow", reason="ok")


async def execute(
    *,
    call: ToolCall,
    identity: Identity,
    correlation_id: UUID,
    message_id: UUID,
) -> ToolResult:
    decision = check_policy(call, identity)

    await log_event(
        correlation_id=correlation_id,
        identity=identity,
        message_id=message_id,
        event_type="policy",
        payload={
            "tool": call.tool,
            "args": call.args,
            "proposed_by": call.proposed_by,
        },
        decision=decision.decision,
        reason=decision.reason,
    )

    if decision.decision == "deny":
        return ToolResult(blocked=True, reason=decision.reason)
    if decision.decision == "hitl":
        return ToolResult(blocked=True, hitl=True, reason=decision.reason)

    impl = TOOL_REGISTRY.get(call.tool)
    if impl is None:
        await log_event(
            correlation_id=correlation_id,
            identity=identity,
            message_id=message_id,
            event_type="tool_call",
            payload={"tool": call.tool, "args": call.args},
            decision="deny",
            reason="tool_not_in_registry",
        )
        return ToolResult(blocked=True, reason=f"Tool '{call.tool}' has no implementation")

    started = time.monotonic()
    try:
        data = await impl(call.args, identity)
    except Exception as e:
        latency = int((time.monotonic() - started) * 1000)
        await log_event(
            correlation_id=correlation_id,
            identity=identity,
            message_id=message_id,
            event_type="tool_call",
            payload={"tool": call.tool, "args": call.args, "error": str(e)},
            decision="deny",
            reason=f"tool_error: {type(e).__name__}",
            latency_ms=latency,
        )
        return ToolResult(error=True, reason=f"Tool failed: {type(e).__name__}")

    latency = int((time.monotonic() - started) * 1000)
    await log_event(
        correlation_id=correlation_id,
        identity=identity,
        message_id=message_id,
        event_type="tool_call",
        payload={"tool": call.tool, "args": call.args, "result": data},
        decision="allow",
        reason="ok",
        latency_ms=latency,
    )
    return ToolResult(data=data)


def new_correlation_id() -> UUID:
    return uuid4()
