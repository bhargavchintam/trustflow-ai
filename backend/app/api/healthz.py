"""Deep /healthz — checks DB, LLM, embedding service. Cached 30s."""
from __future__ import annotations

import asyncio
import time

import httpx
from fastapi import APIRouter

from app.config import get_settings
from app.db.connection import connection

router = APIRouter()

_CACHE: dict[str, object] = {"ts": 0.0, "result": None}
_CACHE_TTL_S = 30


async def _check_db() -> tuple[bool, str]:
    try:
        async with connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def _check_llm() -> tuple[bool, str]:
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=4.0) as c:
            r = await c.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": s.anthropic_api_key, "anthropic-version": "2023-06-01"},
            )
            return r.status_code == 200, f"status={r.status_code}"
    except Exception as e:
        return False, f"{type(e).__name__}"


async def _check_embedding() -> tuple[bool, str]:
    s = get_settings()
    if s.voyage_api_key:
        try:
            async with httpx.AsyncClient(timeout=4.0) as c:
                r = await c.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {s.voyage_api_key}"},
                    json={"input": ["health check"], "model": s.embedding_model},
                )
                return r.status_code == 200, f"voyage status={r.status_code}"
        except Exception as e:
            return False, f"voyage: {type(e).__name__}"
    return False, "no embedding provider configured"


@router.get("/healthz")
async def healthz():
    now = time.monotonic()
    if _CACHE["result"] is not None and now - _CACHE["ts"] < _CACHE_TTL_S:
        return _CACHE["result"]

    db_ok, db_msg = await _check_db()
    llm_ok, llm_msg = await _check_llm()
    emb_ok, emb_msg = await _check_embedding()

    result = {
        "status": "ok" if (db_ok and llm_ok and emb_ok) else "degraded",
        "db": {"ok": db_ok, "msg": db_msg},
        "llm": {"ok": llm_ok, "msg": llm_msg},
        "embedding": {"ok": emb_ok, "msg": emb_msg},
    }
    _CACHE["result"] = result
    _CACHE["ts"] = now
    return result


@router.get("/api/warmup")
async def warmup():
    asyncio.create_task(_check_db())
    asyncio.create_task(_check_llm())
    asyncio.create_task(_check_embedding())
    return {"status": "warming"}
