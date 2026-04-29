"""Embedding service. Voyage-3 primary, OpenAI fallback. Returns None on failure
so the caller can persist with embedding_status='failed' and retry-mark."""
from __future__ import annotations

import logging
from typing import Sequence

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


async def embed(texts: Sequence[str]) -> list[list[float] | None]:
    """Return embeddings (or None per text on failure). Never raises."""
    if not texts:
        return []
    try:
        if get_settings().voyage_api_key:
            vectors = await _voyage_embed(list(texts))
            return list(vectors)
    except Exception as e:
        log.warning("embedding failure (voyage): %s", e)
    return [None] * len(texts)


async def embed_one(text: str) -> list[float] | None:
    out = await embed([text])
    return out[0] if out else None
