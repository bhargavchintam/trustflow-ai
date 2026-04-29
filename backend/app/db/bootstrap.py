"""Apply schema.sql idempotently. Safe to run on every container start."""
import asyncio
from pathlib import Path

from app.db.connection import close_pool, connection, init_pool

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def bootstrap() -> None:
    await init_pool()
    sql = SCHEMA_PATH.read_text()
    async with connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
        await conn.commit()


async def main() -> None:
    try:
        await bootstrap()
        print("[bootstrap] schema applied")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
