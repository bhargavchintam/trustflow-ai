"""POST /api/chat — runs the coordinator (DAG or ReAct) and streams the response via SSE."""
from __future__ import annotations

import json
import time
from uuid import uuid4

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.identity import resolve_identity
from app.audit.logger import log_event
from app.graph.agent import run_react
from app.models import ChatRequest, Identity
from app.policy import gateway
from app.router import coordinator
from app.router.dag_flows import password_reset

router = APIRouter()


@router.post("/api/chat")
async def chat(req: ChatRequest, identity: Identity = Depends(resolve_identity)):
    correlation_id = gateway.new_correlation_id()
    message_id = uuid4()

    async def event_stream():
        started = time.monotonic()
        decision = coordinator.classify(req.input, force_route=req.force_route)

        await log_event(
            correlation_id=correlation_id,
            identity=identity,
            message_id=message_id,
            event_type="route",
            payload={
                "route": decision.route,
                "intent": decision.intent,
                "confidence": decision.confidence,
                "matched_by": decision.matched_by,
                "input": req.input,
            },
        )
        yield {
            "event": "route",
            "data": json.dumps(
                {
                    "correlation_id": str(correlation_id),
                    "message_id": str(message_id),
                    "session_id": identity.session_id,
                    **decision.model_dump(),
                }
            ),
        }

        if decision.route == "dag" and decision.intent == "password_reset":
            response = await password_reset.run(
                identity=identity,
                user_input=req.input,
                correlation_id=correlation_id,
                message_id=message_id,
            )
        else:
            response = await run_react(
                identity=identity,
                user_input=req.input,
                correlation_id=correlation_id,
                message_id=message_id,
            )

        total_ms = int((time.monotonic() - started) * 1000)
        yield {
            "event": "message",
            "data": json.dumps(
                {
                    "content": response,
                    "latency_ms": total_ms,
                    "message_id": str(message_id),
                    "session_id": identity.session_id,
                }
            ),
        }
        yield {"event": "done", "data": json.dumps({"latency_ms": total_ms})}

    return EventSourceResponse(event_stream())
