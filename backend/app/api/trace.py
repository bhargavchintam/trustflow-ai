"""GET /api/trace?session_id=&message_id= — return the audit timeline."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.identity import resolve_identity
from app.audit.logger import fetch_trace
from app.models import Identity

router = APIRouter()


def _serialize(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        item: dict = {}
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            else:
                item[k] = str(v) if isinstance(v, UUID) else v
        out.append(item)
    return out


@router.get("/api/trace")
async def get_trace(
    message_id: UUID | None = Query(default=None),
    correlation_id: UUID | None = Query(default=None),
    identity: Identity = Depends(resolve_identity),
):
    rows = await fetch_trace(
        tenant_id=identity.tenant_id,
        session_id=identity.session_id,
        message_id=message_id,
        correlation_id=correlation_id,
    )
    return {"events": _serialize(rows)}
