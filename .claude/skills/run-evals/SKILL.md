---
name: run-evals
description: Run the synthetic eval suite (routing accuracy, security block rate, memory recall, cross-tenant isolation, latency, cost) against the local or deployed TrustFlow AI API. Use when the user says "run evals", "check eval results", "verify the eval dashboard", or as a pre-deploy gate.
---

# run-evals

Run the eval suite against a TrustFlow AI deployment.

## Steps

1. Determine the target URL. Default: `http://localhost:8080`. If the user passed `--url`, use that. Otherwise prompt.

2. Verify reachability:
   ```
   curl -fsS $URL/healthz | jq
   ```
   Expect `status: ok` and all components (`db`, `llm`, `embedding`) reporting healthy. If any are not healthy, stop and report the broken component.

3. Run the eval script:
   ```
   cd backend && uv run python -m app.evals.run_evals --api $URL
   ```
   The script writes results to the `eval_results` table and prints a summary.

4. Print the summary table. Include:
   - **Routing accuracy** — correct route + intent / total routing cases
   - **Prompt-injection block rate** — tools blocked / attack cases
   - **Cross-tenant retrieval block rate** — must be 100%
   - **Memory recall (returning user)** — procedural hit on Bob's VPN scenarios
   - **Memory precision (new user)** — no false-positive prior-context for Alice
   - **Latency p50 / p95** in ms
   - **Cost-per-request** average in USD

5. If any category drops below **90%**, list the failing case IDs with their actual vs expected results.

6. If any **CRITICAL** category (`security` or `tenant_isolation`) drops below **100%**, exit non-zero and warn loudly — these block deploy.

## Args

- `--url <https-url>` — target endpoint (default: `http://localhost:8080`)
- `--category <name>` — run only one category (`routing`, `security`, `memory`, `tenant_isolation`)

## Reads

- `backend/app/evals/synthetic_eval.json` — the test cases
- `backend/app/evals/judge.py` — per-category pass/fail logic

## Writes

- `eval_results` table in Postgres (one row per case per run)
