"""GET /api/history — return the user's prior chat history.

Reads episodic memory rows for (tenant_id, user_id), optionally filtered to
a single session_id, and returns them in chronological (ascending) order so
the frontend can rehydrate the chat thread on page load.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.identity import resolve_identity
from app.memory import service as memory
from app.models import Identity

router = APIRouter()


@router.get("/api/history")
async def get_history(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    identity: Identity = Depends(resolve_identity),
) -> dict[str, Any]:
    rows = await memory.list_episodic(
        tenant_id=identity.tenant_id,
        user_id=identity.user_id,
        limit=limit,
    )
    if session_id:
        rows = [r for r in rows if str(r.get("session_id") or "") == session_id]
    rows = list(reversed(rows))
    messages = [
        {
            "id": str(r["id"]),
            "role": r["role"],
            "content": r["content"],
            "session_id": str(r.get("session_id") or ""),
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
        }
        for r in rows
    ]
    return {"messages": messages}
