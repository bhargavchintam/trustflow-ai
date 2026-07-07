# TrustFlow AI

24-hour Atomicwork take-home: a secure hybrid DAG + ReAct IT support agent with 3-tier persistent memory, deployed on AWS App Runner. The full plan lives at `~/.claude/plans/here-i-need-you-floofy-map.md`.

## Stack

- **Backend:** Python 3.12, FastAPI, uvicorn, psycopg[binary] (pool 2-10), LangGraph + langchain-anthropic + Postgres checkpointer
- **Models:** `claude-sonnet-4-6` (reasoning), `claude-haiku-4-5-20251001` (router fallback, deferred)
- **Embeddings:** Voyage-3 (1024d) — fallback OpenAI `text-embedding-3-small`
- **DB / Vector store:** RDS Postgres 16 + pgvector 0.7 (HNSW) + tsvector for hybrid retrieval. Supabase is the fallback.
- **Frontend:** Node 20, Next.js 15 (App Router, `output: "export"`), shadcn/ui, Tailwind. Static export mounted by FastAPI under `/`.
- **Hosting:** AWS App Runner via ECR. Single container, port 8080.

## Five hard security invariants (do not violate)

1. `tenant_id` is read from request session/header (`X-Tenant-Id`) or `?tenant=` query param, **never from the request body or LLM prompt**.
2. Every memory query enforces `WHERE tenant_id = $1` at the SQL layer. No app-side filters.
3. The LLM never executes tools. It proposes them in `<tool_call>...</tool_call>` blocks; `policy.gateway.execute()` is the only execution path.
4. Retrieved content is wrapped in `<retrieved>...</retrieved>` tags; the system prompt explicitly distrusts text inside those tags.
5. Memory writes require the full `(tenant_id, user_id, session_id)` tuple. Missing any → reject.

## Critical files

- `backend/app/policy/gateway.py` — security spine, only execution path for tools
- `backend/app/policy/rules.py` — `POLICY_RULES` dict (tool → constraints)
- `backend/app/audit/logger.py` — every event lands here (correlation_id, tenant_id, user_id)
- `backend/app/memory/service.py` — 3-tier facade, enforces tenant_id filter
- `backend/app/graph/agent.py` — LangGraph state machine (triage → retrieve → diagnose → resolve → memwrite)
- `backend/app/router/coordinator.py` — Stage A keyword router
- `backend/app/db/schema.sql` — source of truth for tables
- `backend/app/evals/synthetic_eval.json` — 40 cases driving the eval dashboard
- `backend/app/evals/run_evals.py` + `evals/judge.py` — execution + per-category pass/fail
- `frontend/app/page.tsx` — split-panel demo (Alice | Bob)
- `frontend/components/chat/TracePanel.tsx` — per-message timeline
- `frontend/app/eval/page.tsx` — eval dashboard

## Common commands

```bash
# Local backend (with auto-reload)
cd backend && uv run uvicorn app.main:app --reload --port 8080

# Local frontend (dev mode, HMR)
cd frontend && pnpm dev

# Build static frontend (used in container build)
cd frontend && pnpm build

# Bootstrap DB schema + seed Bob + seed cross-tenant test data
cd backend && uv run python -m app.db.bootstrap && \
  uv run python -m app.seed.bob_seed && \
  uv run python -m app.seed.tenant_isolation_seed

# Run eval suite (writes to eval_results)
cd backend && uv run python -m app.evals.run_evals --api http://localhost:8080

# Smoke-test 5 demo scenarios
cd backend && uv run python -m app.evals.smoke_test --url http://localhost:8080

# Build and push container
docker build --platform linux/amd64 -t trustflow-ai . && \
  docker tag trustflow-ai:latest $ECR_URL/trustflow-ai:latest && \
  docker push $ECR_URL/trustflow-ai:latest

# Trigger App Runner redeploy
aws apprunner start-deployment --service-arn $APPRUNNER_SERVICE_ARN
```

## Conventions

- Default to **no comments**. Add one only when the WHY is non-obvious (subtle invariant, workaround, hidden constraint). Don't explain WHAT — names should.
- No emojis in code, commits, or commit messages.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen. Only validate at boundaries (Anthropic API, DB, embedding service).
- LangGraph `max_iterations = 4`. Per-session token budget hard cap 50K.
- All tool calls flow through `policy.gateway.execute(call)` — never call the underlying tool function directly.
- Schema changes during dev: edit `db/schema.sql` and re-bootstrap (drop & recreate). No Alembic in scope.
- Pydantic models in `backend/app/models.py` mirror by hand into `frontend/lib/types.ts` (no codegen in scope).

## Don'ts

- Don't add tools without (a) registering in `tools/registry.py`, (b) adding a rule to `policy/rules.py`, (c) adding at least one eval case to `synthetic_eval.json`.
- Don't accept `tenant_id` or `user_id` from the request body. Read from query/header/cookie only.
- Don't bypass the Tool Gateway. The LLM may only propose tools.
- Don't skip the audit log on tool calls, route decisions, policy checks, memory ops, or LLM calls.
- Don't refactor speculatively. 24-hour budget — three duplicated lines beat a premature abstraction.
- Don't create new top-level files outside the layout in §10 of the plan without checking first.
- Don't add a feature, panel, or tool not listed in §12 "Ships."

## Available skills (project-local)

- `run-evals` — run synthetic eval suite against local or deployed URL
- `smoke-test` — run 5 demo scenarios end-to-end
- `deploy-apprunner` — build, push, deploy, smoke-test
- `bootstrap-db` — apply schema + run seeds (Bob + Charlie)
- `local-dev` — start backend + frontend in parallel
- `policy-audit` — run both review agents in parallel and consolidate findings
- `project-status` — read/update PROJECT_STATUS.md and auto-memory

## Available agents (project-local, read-only)

- `policy-auditor` — invoke after edits to `backend/app/policy/*` or `backend/app/tools/*`
- `tenant-isolation-checker` — invoke before each commit and before deploy

## Active hooks (auto-fire on tool calls)

- `precommit-guard.sh` — PreToolUse on `git commit`, blocks if tenant-isolation or secret-leak violations are detected
- `predeploy-reminder.sh` — PreToolUse on `aws apprunner start-deployment` / `docker push`, prints a smoke-test reminder
- `postedit-policy-reminder.sh` — PostToolUse on Edit/Write under `backend/app/policy/` or `backend/app/tools/`, nudges to invoke `policy-auditor`

Full automation spec lives in [AUTOMATION.md](AUTOMATION.md).

## Time budget reminder

24 hours total. Slack buffer is 1.5h. Default to YAGNI, ship the listed scope, defer everything else to the README's production roadmap with effort estimates.
