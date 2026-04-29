---
name: local-dev
description: Start the local dev environment — backend (uvicorn :8080) and frontend (Next.js dev :3000) in parallel. Use when the user says "run locally", "start dev", or "fire it up".
---

# local-dev

Start the full local dev stack.

## Pre-flight

- `.env` filled with `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `DATABASE_URL`
- DB schema applied (run the `bootstrap-db` skill if fresh)
- `frontend/node_modules/` exists (run `pnpm install` if not)

## Steps

Run both in the background — the user wants to interact with the running app, not block on terminal output.

```bash
# Backend (port 8080)
cd "/Users/bhargav/Desktop/TrustFlow AI/backend"
uv run uvicorn app.main:app --reload --port 8080
```

Run with `run_in_background=true`. Note the bash_id.

```bash
# Frontend (port 3000)
cd "/Users/bhargav/Desktop/TrustFlow AI/frontend"
pnpm dev
```

Run with `run_in_background=true`. Note the bash_id.

## Verify

After ~5s for backend, ~10s for frontend:

```bash
curl -fsS http://localhost:8080/healthz | jq
curl -fsS http://localhost:3000 -o /dev/null -w "%{http_code}\n"
```

Print:
- Healthz status (db/llm/embedding sub-components)
- Frontend HTTP code (expect 200)
- Both URLs to open

## Stopping

Either kill the bash sessions explicitly when the user is done, or leave them running for the next operation. Don't run more than one instance per port.
