"""GET /api/eval — eval dashboard data. POST /api/eval/run — re-run evals server-side."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks
from psycopg.rows import dict_row

from app.db.connection import connection
from app.evals.run_evals import run_all

router = APIRouter()


def _serialize(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        item: dict = {}
        for k, v in r.items():
            item[k] = v.isoformat() if hasattr(v, "isoformat") else v
        out.append(item)
    return out


@router.get("/api/eval")
async def get_eval():
    async with connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT MAX(run_id) AS run_id FROM eval_results")
            row = await cur.fetchone()
            run_id = row["run_id"] if row else None
            if not run_id:
                return {"run_id": None, "summary": None, "cases": []}

            await cur.execute(
                """
                SELECT category, case_id, input, expected, actual, passed,
                       latency_ms, cost_usd, created_at
                FROM eval_results
                WHERE run_id = %s
                ORDER BY category, case_id
                """,
                (run_id,),
            )
            rows = list(await cur.fetchall())

    summary = _summarize(rows)
    return {"run_id": run_id, "summary": summary, "cases": _serialize(rows)}


def _summarize(rows: list[dict]) -> dict:
    by_cat: dict[str, list[dict]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)
    out: dict = {}
    for cat, items in by_cat.items():
        passed = sum(1 for i in items if i["passed"])
        out[cat] = {"passed": passed, "total": len(items), "rate": round(passed / len(items), 3)}
    latencies = sorted(r["latency_ms"] for r in rows if r["latency_ms"] is not None)
    if latencies:
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95) - 1] if len(latencies) > 1 else latencies[-1]
        out["latency_p50_ms"] = p50
        out["latency_p95_ms"] = p95
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    out["avg_cost_usd"] = round(sum(costs) / len(costs), 6) if costs else 0
    out["total_cases"] = len(rows)
    out["total_passed"] = sum(1 for r in rows if r["passed"])
    return out


@router.post("/api/eval/run")
async def trigger_run(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_evals_in_background)
    return {"status": "started"}


async def _run_evals_in_background():
    try:
        await run_all(api_url="http://localhost:8080")
    except Exception:
        pass
