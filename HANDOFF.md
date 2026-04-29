# Hand-off Notes

What's been built, what you need to do, and what to send to the interviewer.

---

## What I built (status)

| Block | Status | Notes |
|---|---|---|
| `CLAUDE.md` + `.claude/{settings, skills, agents}` | ✅ | Loaded every turn; pre-allowed shell commands; 3 skills + 2 review agents |
| Backend — FastAPI, schema, memory, LangGraph, DAG router, Tool Gateway, Policy Engine, Audit, eval suite, seeds | ✅ | All modules import; LangGraph compiles; router classifier passes 6/6; policy gateway returns correct allow/deny/hitl on 6/6 cases (verified locally) |
| Frontend — Next.js 15 + Tailwind, split-panel chat, memory inspector, trace panel, eval dashboard, demo controls, "Attack the Agent" buttons | ✅ | Static export ready (`pnpm build` produces `out/` mountable by FastAPI) |
| Dockerfile (multi-stage: node 20 build → python 3.12 runtime) | ✅ | `--platform linux/amd64` required when building on Apple Silicon |
| `apprunner.yaml`, `.dockerignore`, `.gitignore`, `.env.example` | ✅ | |
| README.md (the second deliverable) | ✅ | Architecture, 5-scenario script, security model, eval, cuts list, prod roadmap |
| Backend deps installed (`uv sync`) | ✅ | Verified imports clean |
| Frontend deps (`pnpm install`) | ⬜ | **You run this** — see "Local verification" below |
| RDS Postgres + pgvector provisioned | ⬜ | **You provision** — see "AWS provisioning" below |
| App Runner deployed | ⬜ | **You deploy** — `deploy-apprunner` skill walks through it |
| Loom walkthrough | ⬜ | Record after deploy works |

---

## Things you need to install / provide

### 1. AWS CLI (not currently on this machine)

```bash
# macOS via Homebrew
brew install awscli

# Verify
aws --version
aws configure   # enter access key, secret, region (e.g. us-east-1)
aws sts get-caller-identity
```

### 2. API keys

Create `/Users/bhargav/Desktop/TrustFlow AI/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
DATABASE_URL=postgresql://USER:PASS@HOST:5432/DBNAME
DEFAULT_TENANT_ID=tenant_acme
DEFAULT_USER_ID=alice
```

- **Anthropic key:** https://console.anthropic.com/ → API Keys
- **Voyage key:** https://www.voyageai.com/ — free tier covers seeded data + a few hundred eval queries
- (OpenAI key works as fallback if you'd rather not use Voyage; the embeddings module already supports it but Voyage is the default.)

### 3. Local Postgres (optional, for local dev before AWS)

Cleanest path: install via Homebrew with pgvector pre-built.

```bash
brew install postgresql@16
brew services start postgresql@16
brew install pgvector

createdb trustflow
psql trustflow -c "CREATE EXTENSION vector; CREATE EXTENSION pgcrypto;"
```

Then set `DATABASE_URL=postgresql://localhost:5432/trustflow` in `.env`.

---

## Local verification (do this first)

```bash
cd "/Users/bhargav/Desktop/TrustFlow AI"

# Backend deps already synced. If you need to refresh:
cd backend && uv sync

# Frontend deps — first time
cd ../frontend && pnpm install

# Bootstrap schema + seed
cd ../backend && uv run python -m app.db.bootstrap
uv run python -m app.seed.bob_seed
uv run python -m app.seed.tenant_isolation_seed

# Start backend (terminal 1)
uv run uvicorn app.main:app --reload --port 8080

# Start frontend (terminal 2)
cd ../frontend && pnpm dev
# Open http://localhost:3000

# Smoke-test (terminal 3)
cd ../backend && uv run python -m app.evals.smoke_test --url http://localhost:8080
```

**Expected:** all 5 smoke-test scenarios PASS. If anything fails, the trace endpoint will tell you what happened — `curl 'http://localhost:8080/api/trace?message_id=<id>' -H 'X-Tenant-Id: tenant_acme' -H 'X-User-Id: alice' -H 'X-Session-Id: xxx'`.

---

## AWS provisioning (one-time)

Two paths — pick one. **Supabase is faster (~10 min)**; RDS is more "AWS-native" but takes longer.

### Path A — Supabase (recommended for the 24h sprint)

1. Sign up at https://supabase.com/
2. Create a project (free tier is fine).
3. Database settings → Connection string → use the **Session pooler** URI (port 5432).
4. SQL Editor → run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   ```
5. Set `DATABASE_URL` in `.env` and in App Runner env vars (later).
6. Skip VPC connector entirely.

### Path B — RDS Postgres + VPC connector

1. RDS console → Create database → PostgreSQL 16 → Free tier or db.t4g.micro.
2. Single AZ. Public accessibility **No** (we'll use VPC connector). Note the security group.
3. Connect once via a temporary EC2 / Cloud9 / bastion to enable extensions:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   ```
4. App Runner → VPC connector (next step) needs to be in the same VPC and a security group allowed by RDS.

### ECR repo

```bash
aws ecr create-repository --repository-name trustflow-ai --region us-east-1
# Note the repositoryUri it returns
```

### Secrets Manager (optional but nice)

```bash
aws secretsmanager create-secret --name trustflow/anthropic --secret-string "$ANTHROPIC_API_KEY"
aws secretsmanager create-secret --name trustflow/voyage    --secret-string "$VOYAGE_API_KEY"
aws secretsmanager create-secret --name trustflow/db        --secret-string "$DATABASE_URL"
```

(For a 24h demo, plain App Runner env vars also work — Secrets Manager is the cleaner path but not required.)

### App Runner service

1. App Runner console → Create service → Source: container registry, ECR private, image `trustflow-ai:latest`.
2. Deployment trigger: Automatic (re-deploys on every `:latest` push).
3. Compute: 1 vCPU / 2 GB.
4. Port: 8080.
5. Health check path: `/healthz`.
6. Env vars (or secrets references):
   - `ANTHROPIC_API_KEY`
   - `VOYAGE_API_KEY`
   - `DATABASE_URL`
   - `DEFAULT_TENANT_ID=tenant_acme`
   - `DEFAULT_USER_ID=alice`
   - `LOG_LEVEL=INFO`
7. (Path B only) VPC connector pointing at the RDS VPC + the SG you allowed inbound 5432 on.
8. Create. Note the **Service ARN** — set as `APPRUNNER_SERVICE_ARN` in `.env`.

---

## Deploy (every code change)

Three options — easiest first.

### Option 1 — invoke the project skill

In Claude Code, just say **"deploy"**. That triggers the `deploy-apprunner` skill, which:
1. Checks all required env vars are set.
2. Builds image with `--platform linux/amd64`.
3. ECR login + tag + push.
4. `aws apprunner start-deployment`.
5. Polls until RUNNING.
6. Hits `/healthz` and runs the `smoke-test` skill.

### Option 2 — one-liner

```bash
cd "/Users/bhargav/Desktop/TrustFlow AI" && \
docker build --platform linux/amd64 -t trustflow-ai . && \
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com && \
docker tag trustflow-ai:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trustflow-ai:latest && \
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trustflow-ai:latest && \
aws apprunner start-deployment --service-arn $APPRUNNER_SERVICE_ARN
```

### Option 3 — manual

Deploy via App Runner console once, then re-deploy by pushing a new `:latest` to ECR.

---

## After first deploy

1. Get the URL: `aws apprunner describe-service --service-arn $APPRUNNER_SERVICE_ARN --query 'Service.ServiceUrl' --output text`
2. **First hit takes ~30s** (App Runner cold start). The frontend hits `/api/warmup` automatically on page load to mitigate this.
3. Bootstrap + seed against the deployed DB:
   ```bash
   # If your DATABASE_URL points at the production DB, this works from your laptop:
   cd backend && uv run python -m app.db.bootstrap
   uv run python -m app.seed.bob_seed
   uv run python -m app.seed.tenant_isolation_seed
   ```
   (Or App Runner's lifespan runs bootstrap on startup — but seeds need a manual trigger via `POST /api/seed`.)
4. Generate eval results:
   ```bash
   uv run python -m app.evals.run_evals --api https://YOUR-URL.awsapprunner.com
   ```
5. Smoke-test:
   ```bash
   uv run python -m app.evals.smoke_test --url https://YOUR-URL.awsapprunner.com
   ```
6. Open the URL in a browser, click through the 5 demo scenarios in the README.
7. **Update README.md** with the URL and Loom link before sharing.

---

## Loom recording (90 seconds)

Script:

> *"This is TrustFlow AI — a hybrid DAG + ReAct IT support agent.*
>
> *On the left is Alice, a new user. On the right is Bob, a returning user with pre-seeded memory. Watch what happens when I ask the same VPN question to both.*  **\[type "my VPN keeps dropping" into both\]**
>
> *Alice gets a generic ReAct loop. Bob gets recognized — the procedural-memory row is glowing in his inspector — and the agent applies the prior fix.*
>
> *Now I'll type "reset my password". The route badge flips to DAG; the latency pill shows under 800ms. Same prompt with Force ReAct on takes 3 seconds — that's the latency teaching moment.*
>
> *Now the security beat. I'll click the "Reset CEO password" attack chip. The agent refuses politely. I'll click 'Why?' on its response — the trace shows route → policy DENY with a human-readable reason.*
>
> *Finally, the eval dashboard. Routing 100%, prompt-injection block 100%, cross-tenant isolation 100%, memory recall measured against expected behavior. These are measured numbers, not asserted ones — the same trace I just showed feeds the judge.*
>
> *Full design rationale, what I cut, and the production roadmap are in the README."*

---

## Sending it to the interviewer

Email skeleton:

> *Hi Vivek,*
>
> *Live demo: https://...awsapprunner.com (first hit ~30s due to App Runner cold start)*
> *Walkthrough (90s Loom): https://...*
> *README with architecture, security model, eval results, and production roadmap: \[in repo\]*
> *Source: https://github.com/.../trustflow-ai*
>
> *I went with the hybrid DAG + ReAct + 3-tier memory shape, with policy-gated tools and a measurable eval suite — the security and evaluation pieces felt central to client-confidence given Atomicwork's domain. Happy to walk through any of the trade-offs.*
>
> *Bindu*

---

## Cost watch

Demo week (~7 days): ~**$25–30** total
- App Runner 1 vCPU / 2 GB always-on: ~$3/day
- RDS db.t4g.micro: ~$0.40/day (free tier first year)
- Anthropic API: <$5 across dev + demo (Sonnet 4.6 is cheap)
- Voyage embeddings: free tier covers seeded data + a few hundred queries
- ECR: <$0.10

After the interview window: pause App Runner (`aws apprunner pause-service`) and stop RDS — parked cost ~$1/week.

---

## What to do if something is broken

| Symptom | First check |
|---|---|
| `/healthz` returns degraded | Hit `/healthz` and read which sub-component is unhealthy. DB usually = wrong `DATABASE_URL` or missing pgvector extension. |
| Bob's panel doesn't show recognition | Run `POST /api/seed` from the demo controls or `python -m app.seed.bob_seed` locally. |
| App Runner deploy stuck | `aws apprunner describe-service ... --query 'Service.Status'` — if OPERATION_IN_PROGRESS another deploy is running. |
| ECR push 401 | Login token expires after 12h. Re-run `aws ecr get-login-password ...`. |
| LangGraph compile error after edit | `uv run python -c "from app.graph.agent import build_graph; build_graph()"` reproduces it. |
| Frontend blank after `pnpm build` | Check `frontend/out/index.html` exists. Then `frontend/out/_next/` should also exist. |
| Eval dashboard empty | Run `python -m app.evals.run_evals --api $URL` once first. |

---

## Hand-back checklist

When you're ready to send the URL to the interviewer:

- [ ] Deployed URL hit successfully (after warmup)
- [ ] All 5 smoke-test scenarios PASS against deployed URL
- [ ] `/eval` dashboard shows 100% on security and tenant_isolation rows
- [ ] README.md has the deployed URL and Loom link filled in
- [ ] Repo pushed to GitHub (public is fine for a personal demo)
- [ ] Email drafted with URL + Loom + README + repo links
