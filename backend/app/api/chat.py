"""POST /api/chat — runs the coordinator (DAG or ReAct) and streams the response via SSE."""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from uuid import uuid4

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.identity import resolve_identity
from app.audit.logger import log_event
from app.graph.agent import SONNET_INPUT_PER_MTOK, SONNET_OUTPUT_PER_MTOK, run_react_streaming
from app.models import ChatRequest, Identity
from app.policy import gateway
from app.router import coordinator
from app.router.dag_flows import (
    account_unlock,
    distribution_list,
    mfa_reset,
    password_reset,
    request_software,
)

router = APIRouter()

_IDEMPOTENCY: dict[str, tuple[float, dict]] = {}
_IDEMPOTENCY_TTL_S = 5.0


def _idempotency_key(identity: Identity, body: ChatRequest) -> str:
    h = hashlib.sha256()
    h.update(identity.tenant_id.encode())
    h.update(b"|")
    h.update(identity.user_id.encode())
    h.update(b"|")
    h.update(identity.session_id.encode())
    h.update(b"|")
    h.update(body.input.encode())
    h.update(b"|")
    h.update((body.force_route or "").encode())
    return h.hexdigest()


def _purge_idempotency_cache() -> None:
    now = time.monotonic()
    stale = [k for k, (ts, _) in _IDEMPOTENCY.items() if now - ts > _IDEMPOTENCY_TTL_S]
    for k in stale:
        _IDEMPOTENCY.pop(k, None)


@router.post("/api/chat")
async def chat(req: ChatRequest, identity: Identity = Depends(resolve_identity)):
    correlation_id = gateway.new_correlation_id()
    message_id = uuid4()

    _purge_idempotency_cache()
    idem_key = _idempotency_key(identity, req)
    cached = _IDEMPOTENCY.get(idem_key)
    if cached is not None:
        cached_payload = cached[1]

        async def replay_stream():
            await log_event(
                correlation_id=correlation_id,
                identity=identity,
                message_id=message_id,
                event_type="route",
                payload={
                    "idempotent_replay": True,
                    "original_message_id": cached_payload["message"]["message_id"],
                    "route": cached_payload["route"].get("route"),
                    "intent": cached_payload["route"].get("intent"),
                },
            )
            yield {
                "event": "route",
                "data": json.dumps(
                    {
                        **cached_payload["route"],
                        "idempotent_replay": True,
                    }
                ),
            }
            text = cached_payload["message"]["content"]
            for i in range(0, len(text), 8):
                yield {"event": "delta", "data": json.dumps({"text": text[i:i + 8]})}
                await asyncio.sleep(0.01)
            yield {"event": "message", "data": json.dumps(cached_payload["message"])}
            yield {
                "event": "done",
                "data": json.dumps({"latency_ms": cached_payload["message"]["latency_ms"]}),
            }

        return EventSourceResponse(replay_stream())

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
        route_payload = {
            "correlation_id": str(correlation_id),
            "message_id": str(message_id),
            "session_id": identity.session_id,
            **decision.model_dump(),
        }
        yield {"event": "route", "data": json.dumps(route_payload)}

        DAG_DISPATCH = {
            "password_reset": password_reset.run,
            "request_software": request_software.run,
            "account_unlock": account_unlock.run,
            "mfa_reset": mfa_reset.run,
            "distribution_list_access": distribution_list.run,
        }
        if decision.route == "dag" and decision.intent in DAG_DISPATCH:
            response = await DAG_DISPATCH[decision.intent](
                identity=identity,
                user_input=req.input,
                correlation_id=correlation_id,
                message_id=message_id,
            )
            for i in range(0, len(response), 8):
                yield {"event": "delta", "data": json.dumps({"text": response[i:i + 8]})}
                await asyncio.sleep(0.01)
            total_ms = int((time.monotonic() - started) * 1000)
            message_payload = {
                "content": response,
                "latency_ms": total_ms,
                "message_id": str(message_id),
                "session_id": identity.session_id,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost_usd": 0.0,
            }
            yield {"event": "message", "data": json.dumps(message_payload)}
            yield {"event": "done", "data": json.dumps({"latency_ms": total_ms})}
            _IDEMPOTENCY[idem_key] = (
                time.monotonic(),
                {"route": route_payload, "message": message_payload},
            )
            return

        full_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        cost_usd = 0.0

        async for evt_type, payload in run_react_streaming(
            identity=identity,
            user_input=req.input,
            correlation_id=correlation_id,
            message_id=message_id,
        ):
            if evt_type == "delta":
                full_text += payload
                yield {"event": "delta", "data": json.dumps({"text": payload})}
            elif evt_type == "phase":
                yield {"event": "phase", "data": json.dumps({"phase": payload})}
            elif evt_type == "done":
                prompt_tokens = payload.get("prompt_tokens", 0)
                completion_tokens = payload.get("completion_tokens", 0)
                cost_usd = payload.get("cost_usd", 0.0)
                full_text = payload.get("final_response", full_text)

        total_ms = int((time.monotonic() - started) * 1000)
        message_payload = {
            "content": full_text,
            "latency_ms": total_ms,
            "message_id": str(message_id),
            "session_id": identity.session_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
        }
        yield {"event": "message", "data": json.dumps(message_payload)}
        yield {"event": "done", "data": json.dumps({"latency_ms": total_ms})}

        _IDEMPOTENCY[idem_key] = (
            time.monotonic(),
            {"route": route_payload, "message": message_payload},
        )

    return EventSourceResponse(event_stream())
