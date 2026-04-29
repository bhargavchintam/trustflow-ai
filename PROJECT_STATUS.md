# PROJECT_STATUS

Living checkpoint for the TrustFlow AI 24-hour build. Updated by the `project-status` skill.

---

## Current phase

**Block: H22-H23.5 README polish + Loom recording** — App Runner deployed and healthy, all 5 smoke-test scenarios PASS against the deployed URL.

## Critical URLs

| | |
|---|---|
| Deployed app | https://2fgmvxxdt3.us-east-1.awsapprunner.com |
| GitHub repo | https://github.com/bhargavchintam/trustflow-ai (private) |
| Loom walkthrough | _record next_ |
| App Runner ARN | arn:aws:apprunner:us-east-1:772706200954:service/trustflow-ai/e0b75207b1e343569aacc1b3804a521d |
| ECR image | 772706200954.dkr.ecr.us-east-1.amazonaws.com/trustflow-ai:latest |

## Done ✅

- Pre-build setup: CLAUDE.md, `.claude/settings.json`, 5 skills (run-evals, smoke-test, deploy-apprunner, bootstrap-db, local-dev, policy-audit, project-status), 2 review agents (policy-auditor, tenant-isolation-checker)
- Backend: FastAPI scaffold; full schema (8 tables incl. tenant-aware memory + audit + tickets + user_roles + eval_results); Pydantic models; identity resolver
- Memory: 3-tier facade (`episodic`, `semantic`, `procedural`); hybrid retrieval (BM25 + pgvector cosine, weighted blend); write-time semantic dedup; transactional writes with NULL-on-embedding-failure
- Policy spine: Tool Gateway as the only execution path; POLICY_RULES with self/HITL/role checks; correlation IDs threaded through all events; PII redaction in audit logger
- Tools: 3 mock tools (vpn_diagnostic, check_vpn_status, reset_password)
- Router: Stage A keyword classifier (Stage B Haiku judge deferred); password_reset DAG flow that also writes episodic memory
- LangGraph ReAct: triage → retrieve → diagnose (loop) → resolve → memwrite; max_iterations=4; per-session token cap; LLM cost tracking; system prompt with prompt-injection defense + "<retrieved>" untrusted-data wrap
- API: chat (SSE), memory, trace, eval, healthz (deep, 30s cached), warmup, seed, reset
- Eval suite: 17 cases × 4 categories (routing, security, memory, tenant_isolation); per-category judge.py; run_evals.py; smoke_test.py
- Seeds: Bob (VPN history + procedural row + roles incl. fake CEO); Charlie at tenant_globex (cross-tenant test data)
- Frontend: Next.js 15 static-export; split-panel chat (Alice | Bob); RouteBadge; LatencyPill; TracePanel ("Why?" → /api/trace timeline); MemoryInspector (3 tabs, 2.5s polling, diff-flash, procedural-glow); Eval dashboard at `/eval` with category cards + per-case PASS/FAIL; DemoControls (Reseed / Wipe / Force ReAct / Warm up); Attack-the-agent chips
- Top-level: Dockerfile (multi-stage node→python, ~250MB), apprunner.yaml, .dockerignore, .gitignore, README.md, HANDOFF.md
- Backend deps installed and verified — all modules import, LangGraph compiles, router classifier passes 6/6, policy gateway returns correct allow/deny/hitl on 6/6

## In progress ⏳

- Auto-memory entries (user, feedback, project, scope cuts, plan reference) — saved to `~/.claude/projects/-Users-bhargav-Desktop-TrustFlow-AI/memory/`
- `.env` template written — Bindu fills `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `DATABASE_URL`
- GitHub repo creation via `gh`

## Pending ⬜

- Frontend `pnpm install` already done by Bindu
- Bindu provisions Postgres (Supabase recommended; RDS as alternative)
- Bindu fills `.env` with real keys
- Run `bootstrap-db` skill (apply schema + seeds)
- Run `local-dev` skill (start backend + frontend)
- Run `smoke-test` skill against local URL
- Run `run-evals` skill (populate eval_results)
- AWS infra: ECR repo, App Runner service, env-vars/secrets configured
- Run `deploy-apprunner` skill
- Run `smoke-test` against deployed URL
- Update README + PROJECT_STATUS with deployed URL
- Record 90s Loom
- Send URL + Loom + repo to interviewer

## Live decisions still open

1. **At deploy time:** RDS+VPC connector vs Supabase fallback. Schemas identical. ~20-min swap. Decision rule: not green by H20 → switch.

## Hard constraints (do not violate)

- 5 security invariants (see CLAUDE.md): tenant_id from session not body; SQL has `WHERE tenant_id`; LLM proposes only via Tool Gateway; retrieved content in `<retrieved>` tags; memory writes need full tuple
- 24-hour budget — slack buffer is the LAST thing to spend; don't refactor speculatively
- Vector store decision is locked: pgvector for demo, Qdrant in README as production roadmap

## Cost watch

Demo week (~7 days): ~$25-30 total. Pause App Runner + stop RDS post-interview to drop to ~$1/week.
