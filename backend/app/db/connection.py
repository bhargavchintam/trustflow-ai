from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings

_pool: AsyncConnectionPool | None = None


async def init_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    settings = get_settings()
    _pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=2,
        max_size=10,
        open=False,
        kwargs={"autocommit": False},
    )
    await _pool.open(wait=True)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() in app startup.")
    return _pool


@asynccontextmanager
async def connection() -> AsyncIterator[AsyncConnection]:
    p = pool()
    async with p.connection() as conn:
        yield conn
