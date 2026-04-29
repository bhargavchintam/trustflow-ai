"""Embedding service. Voyage-3 primary, OpenAI text-embedding-3-small fallback (1024d).
Returns None per text on failure so the caller can persist with embedding_status='failed'."""
from __future__ import annotations

import logging
from typing import Sequence

import httpx
import voyageai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

log = logging.getLogger(__name__)


class EmbeddingFailure(Exception):
    """Raised when all retries exhausted."""


def _voyage_client() -> voyageai.AsyncClient | None:
    s = get_settings()
    if not s.voyage_api_key:
        return None
    return voyageai.AsyncClient(api_key=s.voyage_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _voyage_embed(texts: list[str]) -> list[list[float]]:
    client = _voyage_client()
    if client is None:
        raise EmbeddingFailure("voyage client unavailable")
    s = get_settings()
    result = await client.embed(texts=texts, model=s.embedding_model, input_type="document")
    return result.embeddings


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _openai_embed(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    if not s.openai_api_key:
        raise EmbeddingFailure("openai client unavailable")
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {s.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": texts,
                "model": "text-embedding-3-small",
                "dimensions": s.embedding_dim,
            },
        )
        r.raise_for_status()
        data = r.json()
    return [d["embedding"] for d in data["data"]]


async def embed(texts: Sequence[str]) -> list[list[float] | None]:
    """Return embeddings (or None per text on failure). Never raises."""
    if not texts:
        return []
    s = get_settings()
    if s.voyage_api_key:
        try:
            vectors = await _voyage_embed(list(texts))
            return list(vectors)
        except Exception as e:
            log.warning("embedding failure (voyage): %s", str(e)[:200])
    if s.openai_api_key:
        try:
            vectors = await _openai_embed(list(texts))
            return list(vectors)
        except Exception as e:
            log.warning("embedding failure (openai): %s", str(e)[:200])
    return [None] * len(texts)


async def embed_one(text: str) -> list[float] | None:
    out = await embed([text])
    return out[0] if out else None
