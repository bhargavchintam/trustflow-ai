"""GET /api/memory?tier=... — read memory inspector data for the current identity."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.identity import resolve_identity
from app.memory import service as memory
from app.models import Identity

router = APIRouter()


def _serialize(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        item: dict = {}
        for k, v in r.items():
            item[k] = str(v) if hasattr(v, "isoformat") else v
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
        out.append(item)
    return out


@router.get("/api/memory")
async def get_memory(
    tier: Literal["episodic", "semantic", "procedural", "all"] = Query(default="all"),
    limit: int = Query(default=50, le=200),
    identity: Identity = Depends(resolve_identity),
):
    if tier == "episodic":
        rows = await memory.list_episodic(
            tenant_id=identity.tenant_id, user_id=identity.user_id, limit=limit
        )
        return {"tier": "episodic", "rows": _serialize(rows)}
    if tier == "semantic":
        rows = await memory.read_semantic(
            tenant_id=identity.tenant_id, user_id=identity.user_id, limit=limit
        )
        return {"tier": "semantic", "rows": _serialize(rows)}
    if tier == "procedural":
        rows = await memory.read_procedural(tenant_id=identity.tenant_id, limit=limit)
        return {"tier": "procedural", "rows": _serialize(rows)}
    if tier == "all":
        ep = await memory.list_episodic(
            tenant_id=identity.tenant_id, user_id=identity.user_id, limit=limit
        )
        sem = await memory.read_semantic(
            tenant_id=identity.tenant_id, user_id=identity.user_id, limit=limit
        )
        proc = await memory.read_procedural(tenant_id=identity.tenant_id, limit=limit)
        return {
            "episodic": _serialize(ep),
            "semantic": _serialize(sem),
            "procedural": _serialize(proc),
        }
    raise HTTPException(400, "invalid tier")
