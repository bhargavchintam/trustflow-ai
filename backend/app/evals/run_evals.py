"""Run the synthetic eval suite. Hits the deployed (or local) API for each case,
captures the trace, judges it, and writes results to eval_results."""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx
from psycopg.types.json import Jsonb

from app.db.connection import close_pool, connection, init_pool
from app.evals.judge import judge

EVAL_PATH = Path(__file__).parent / "synthetic_eval.json"


async def _run_case(client: httpx.AsyncClient, api_url: str, case: dict, run_id: str) -> dict:
    session_id = f"eval_{run_id}_{case['id']}"
    tenant = case.get("tenant", "tenant_acme")
    user = case.get("user", "sam")
    headers = {
        "X-Tenant-Id": tenant,
        "X-User-Id": user,
        "X-Session-Id": session_id,
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    # Reset the new-user persona before any memory case so the
    # "no personal context" check is deterministic (independent of prior cases).
    if case["category"] == "memory" and user == "sam":
        await client.post(f"{api_url}/api/reset", headers=headers)
    body = {"input": case["input"]}

    started = time.monotonic()
    route_decision: dict = {}
    final_message: dict = {}
    message_id: str | None = None

    async with client.stream("POST", f"{api_url}/api/chat", headers=headers, json=body) as r:
        r.raise_for_status()
        async for line in r.aiter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                last_event = line[len("event: "):]
            elif line.startswith("data: "):
                payload = json.loads(line[len("data: "):])
                if last_event == "route":
                    route_decision = payload
                    message_id = payload.get("message_id")
                elif last_event == "message":
                    final_message = payload

    latency_ms = int((time.monotonic() - started) * 1000)

    trace_events: list[dict] = []
    if message_id:
        await asyncio.sleep(0.2)
        params = {"message_id": message_id}
        tr = await client.get(f"{api_url}/api/trace", headers=headers, params=params)
        if tr.status_code == 200:
            trace_events = tr.json().get("events", [])

    actual = {
        "route_decision": route_decision,
        "final_message": final_message,
        "trace_events": trace_events,
    }
    passed, reason = judge(case, actual)

    cost = 0.0
    for e in trace_events:
        if e.get("event_type") == "llm_call":
            cost += float(e.get("payload", {}).get("cost_usd") or 0)

    return {
        "run_id": run_id,
        "category": case["category"],
        "case_id": case["id"],
        "input": case["input"],
        "expected": case.get("expected", {}),
        "actual": {"summary": reason, "route": route_decision, "events_count": len(trace_events)},
        "passed": passed,
        "latency_ms": latency_ms,
        "cost_usd": cost,
    }


async def _persist(results: list[dict]) -> None:
    async with connection() as conn:
        async with conn.cursor() as cur:
            for r in results:
                await cur.execute(
                    """
                    INSERT INTO eval_results (run_id, category, case_id, input, expected,
                                              actual, passed, latency_ms, cost_usd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        r["run_id"],
                        r["category"],
                        r["case_id"],
                        r["input"],
                        Jsonb(r["expected"]),
                        Jsonb(r["actual"]),
                        r["passed"],
                        r["latency_ms"],
                        r["cost_usd"],
                    ),
                )
        await conn.commit()


async def run_all(api_url: str, category: str | None = None) -> list[dict]:
    cases = json.loads(EVAL_PATH.read_text())
    if category:
        cases = [c for c in cases if c["category"] == category]

    run_id = f"run_{int(time.time())}"
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for case in cases:
            try:
                r = await _run_case(client, api_url, case, run_id)
                results.append(r)
                status = "PASS" if r["passed"] else "FAIL"
                print(f"  [{status}] {case['category']:20s} {case['id']:14s} {case['input'][:55]}")
            except Exception as e:
                results.append(
                    {
                        "run_id": run_id,
                        "category": case["category"],
                        "case_id": case["id"],
                        "input": case["input"],
                        "expected": case.get("expected", {}),
                        "actual": {"error": str(e)},
                        "passed": False,
                        "latency_ms": 0,
                        "cost_usd": 0,
                    }
                )
                print(f"  [ERROR] {case['id']}: {e}")

    await init_pool()
    await _persist(results)
    return results


def _summary(results: list[dict]) -> None:
    print("\n=== Summary ===")
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)
    for cat, items in by_cat.items():
        passed = sum(1 for i in items if i["passed"])
        rate = passed / len(items) if items else 0
        print(f"  {cat:20s} {passed}/{len(items)} ({rate*100:.0f}%)")
    latencies = sorted(r["latency_ms"] for r in results if r.get("latency_ms"))
    if latencies:
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95) - 1] if len(latencies) > 1 else latencies[-1]
        print(f"  latency p50/p95 ms: {p50}/{p95}")
    costs = [r.get("cost_usd", 0) for r in results]
    if costs:
        print(f"  avg cost/request: ${sum(costs)/len(costs):.6f}")


async def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8080")
    parser.add_argument("--category", default=None)
    args = parser.parse_args()
    try:
        results = await run_all(args.api, args.category)
        _summary(results)
        critical = [r for r in results if r["category"] in ("security", "tenant_isolation") and not r["passed"]]
        if critical:
            print(f"\nCRITICAL: {len(critical)} failures in security/tenant_isolation. Blocking deploy.")
            raise SystemExit(2)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(_main())
