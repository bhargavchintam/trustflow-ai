"""3-tier memory facade. ALL queries enforce tenant_id at the SQL layer."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.db.connection import connection
from app.memory.embeddings import embed_one

SEMANTIC_DEDUP_THRESHOLD = 0.92
HYBRID_BM25_WEIGHT = 0.4
HYBRID_VECTOR_WEIGHT = 0.6


def _vec_literal(vec: list[float] | None) -> str | None:
    if vec is None:
        return None
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"


# ---------- Episodic ----------


async def write_episodic(
    *,
    tenant_id: str,
    user_id: str,
    session_id: str,
    role: str,
    content: str,
) -> UUID:
    embedding = await embed_one(content)
    vec_literal = _vec_literal(embedding)
    status = "ok" if embedding is not None else "failed"

    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO episodic_memory (tenant_id, user_id, session_id, role, content,
                                             embedding, embedding_status)
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
                RETURNING id
                """,
                (tenant_id, user_id, session_id, role, content, vec_literal, status),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row[0]


async def read_episodic(
    *,
    tenant_id: str,
    user_id: str,
    query: str | None = None,
    limit: int = 10,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    if query:
        embedding = await embed_one(query)
        vec_literal = _vec_literal(embedding)
        if vec_literal is not None:
            async with connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        f"""
                        SELECT id, role, content, created_at, session_id,
                               (1 - (embedding <=> %s::vector)) AS vec_score,
                               ts_rank(content_tsv, plainto_tsquery('english', %s)) AS bm25_score
                        FROM episodic_memory
                        WHERE tenant_id = %s AND user_id = %s
                          AND embedding IS NOT NULL
                        ORDER BY ({HYBRID_VECTOR_WEIGHT} * (1 - (embedding <=> %s::vector))
                                  + {HYBRID_BM25_WEIGHT} * ts_rank(content_tsv,
                                       plainto_tsquery('english', %s))) DESC
                        LIMIT %s
                        """,
                        (vec_literal, query, tenant_id, user_id, vec_literal, query, limit),
                    )
                    return list(await cur.fetchall())

    async with connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            if session_id is not None:
                await cur.execute(
                    """
                    SELECT id, role, content, created_at, session_id
                    FROM episodic_memory
                    WHERE tenant_id = %s AND user_id = %s AND session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (tenant_id, user_id, session_id, limit),
                )
            else:
                await cur.execute(
                    """
                    SELECT id, role, content, created_at, session_id
                    FROM episodic_memory
                    WHERE tenant_id = %s AND user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (tenant_id, user_id, limit),
                )
            return list(await cur.fetchall())


async def list_episodic(
    *, tenant_id: str, user_id: str, limit: int = 50, session_id: str | None = None
) -> list[dict[str, Any]]:
    return await read_episodic(
        tenant_id=tenant_id, user_id=user_id, query=None, limit=limit, session_id=session_id
    )


# ---------- Semantic ----------


async def write_semantic(
    *,
    tenant_id: str,
    user_id: str,
    fact: str,
    source_episode_id: UUID | None = None,
    confidence: float = 0.8,
) -> UUID:
    embedding = await embed_one(fact)
    vec_literal = _vec_literal(embedding)

    if vec_literal is not None:
        async with connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id FROM semantic_memory
                    WHERE tenant_id = %s AND user_id = %s AND embedding IS NOT NULL
                      AND (1 - (embedding <=> %s::vector)) > %s
                    ORDER BY (embedding <=> %s::vector) ASC
                    LIMIT 1
                    """,
                    (tenant_id, user_id, vec_literal, SEMANTIC_DEDUP_THRESHOLD, vec_literal),
                )
                near = await cur.fetchone()
            if near is not None:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE semantic_memory
                        SET corroboration_count = corroboration_count + 1,
                            confidence = LEAST(0.99, confidence + 0.05),
                            last_updated_at = now()
                        WHERE id = %s AND tenant_id = %s AND user_id = %s
                        RETURNING id
                        """,
                        (near[0], tenant_id, user_id),
                    )
                    row = await cur.fetchone()
                await conn.commit()
                return row[0]

    status = "ok" if embedding is not None else "failed"
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO semantic_memory (tenant_id, user_id, fact, source_episode_id,
                                             confidence, embedding, embedding_status)
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
                RETURNING id
                """,
                (tenant_id, user_id, fact, source_episode_id, confidence, vec_literal, status),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row[0]


async def read_semantic(
    *, tenant_id: str, user_id: str, query: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    if query:
        embedding = await embed_one(query)
        vec_literal = _vec_literal(embedding)
        if vec_literal is not None:
            async with connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        SELECT id, fact, confidence, corroboration_count, last_updated_at,
                               (1 - (embedding <=> %s::vector)) AS score
                        FROM semantic_memory
                        WHERE tenant_id = %s AND user_id = %s AND embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector ASC
                        LIMIT %s
                        """,
                        (vec_literal, tenant_id, user_id, vec_literal, limit),
                    )
                    return list(await cur.fetchall())

    async with connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, fact, confidence, corroboration_count, last_updated_at
                FROM semantic_memory
                WHERE tenant_id = %s AND user_id = %s
                ORDER BY last_updated_at DESC
                LIMIT %s
                """,
                (tenant_id, user_id, limit),
            )
            return list(await cur.fetchall())


# ---------- Procedural ----------


async def write_procedural(
    *,
    tenant_id: str,
    problem_signature: str,
    steps: list[dict[str, Any]],
) -> UUID:
    text = problem_signature + " " + " ".join(s.get("action", "") for s in steps)
    embedding = await embed_one(text)
    vec_literal = _vec_literal(embedding)
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO procedural_memory (tenant_id, problem_signature, steps,
                                               success_count, embedding)
                VALUES (%s, %s, %s, 1, %s::vector)
                RETURNING id
                """,
                (tenant_id, problem_signature, Jsonb(steps), vec_literal),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row[0]


async def read_procedural(
    *, tenant_id: str, query: str | None = None, limit: int = 5
) -> list[dict[str, Any]]:
    if query:
        embedding = await embed_one(query)
        vec_literal = _vec_literal(embedding)
        if vec_literal is not None:
            async with connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        SELECT id, problem_signature, steps, success_count, last_used_at,
                               (1 - (embedding <=> %s::vector)) AS score
                        FROM procedural_memory
                        WHERE tenant_id = %s AND embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector ASC
                        LIMIT %s
                        """,
                        (vec_literal, tenant_id, vec_literal, limit),
                    )
                    return list(await cur.fetchall())

    async with connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, problem_signature, steps, success_count, last_used_at
                FROM procedural_memory
                WHERE tenant_id = %s
                ORDER BY success_count DESC, last_used_at DESC NULLS LAST
                LIMIT %s
                """,
                (tenant_id, limit),
            )
            return list(await cur.fetchall())


async def bump_procedural_used(*, tenant_id: str, procedural_id: UUID) -> None:
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE procedural_memory
                SET last_used_at = now(), success_count = success_count + 1
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, procedural_id),
            )
        await conn.commit()


# ---------- Reset / wipe ----------


async def wipe_user(*, tenant_id: str, user_id: str) -> None:
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM episodic_memory WHERE tenant_id = %s AND user_id = %s",
                (tenant_id, user_id),
            )
            await cur.execute(
                "DELETE FROM semantic_memory WHERE tenant_id = %s AND user_id = %s",
                (tenant_id, user_id),
            )
        await conn.commit()
