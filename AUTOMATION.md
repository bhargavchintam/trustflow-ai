# Automation — Hooks, Skills, and Agents

TrustFlow AI ships with project-local Claude Code automation in `.claude/` that enforces the security model and reduces friction during the 24h sprint. Three layers, ordered by how often they fire:

1. **Hooks** — fire automatically on tool calls, can block destructive actions
2. **Skills** — invoked on demand (user types `/skill-name` or asks Claude to "run X")
3. **Agents** — read-only specialist reviewers, invoked at risk points

All three are committed to the repo so the configuration travels with the code.

---

## Hooks (auto-fire)

Configured in `.claude/settings.json` under `hooks.PreToolUse` and `hooks.PostToolUse`. The matcher narrows what triggers them; the script reads the tool input as JSON on stdin and decides whether to allow, warn, or block.

### `precommit-guard.sh` — blocks unsafe commits

**Trigger:** PreToolUse on Bash, when the command contains `git commit`.
**Effect:** exits non-zero (with a stderr message Claude Code surfaces as a system reminder) to block the commit if any of the following are detected:

| Check | Severity | Catches |
|---|---|---|
| `FROM/UPDATE/DELETE (episodic|semantic|procedural)_memory` without `WHERE tenant_id = ...` | CRITICAL | accidental cross-tenant query |
| `INSERT INTO ..._memory` missing `tenant_id` column | CRITICAL | tenant-leaking writes |
| `tenant_id` read from `request.json()` / body / payload | CRITICAL | identity sourced from user input instead of session |
| Direct `TOOL_REGISTRY[...]` access outside `policy/gateway.py` or `tools/registry.py` | CRITICAL | tool execution that bypasses the policy gateway |
| Real-looking API key (`sk-ant-api…`, `pa-…`, `sk-…`) in a staged tracked file | CRITICAL | secret leakage; `.env` is the only place keys live |

Allow-list exceptions: `db/schema.sql` and `bootstrap.py` don't need `WHERE tenant_id` in DDL.

**Verified:** the hook was tested with a synthetic violation (`SELECT * FROM episodic_memory WHERE user_id = %s`) and correctly blocked the commit; clean tree passes.

### `predeploy-reminder.sh` — soft reminder before deploy

**Trigger:** PreToolUse on Bash, when the command contains `aws apprunner start-deployment` or `docker push ...trustflow-ai...`.
**Effect:** prints a reminder (does NOT block) — run smoke-test against the deployed URL, update PROJECT_STATUS.md with the new image digest, pre-warm via `/api/warmup` if demoing within an hour.

### `postedit-policy-reminder.sh` — nudge after security-spine edits

**Trigger:** PostToolUse on Edit/Write, when the path contains `backend/app/policy/` or `backend/app/tools/`.
**Effect:** reminds Claude to invoke the `policy-auditor` agent (or the `policy-audit` skill which runs both review agents in parallel) before committing.

### Why these three specifically

Hooks add friction. To earn their place, each must catch real classes of bugs:

- **`precommit-guard`** is the highest-value: it enforces the Five Hard Security Invariants from `CLAUDE.md` mechanically, so the demo's security narrative can't accidentally regress.
- **`predeploy-reminder`** caught the "stale eval results in dashboard" case during this build — a soft nudge rather than a hard block.
- **`postedit-policy-reminder`** ties together the agents with the workflow — if you edit `policy/`, you should run `policy-auditor` before committing.

Hooks not added (and why):
- *Auto-format on Python edit* — adds an edit cycle to every save; we use ruff manually instead
- *Stop hook to update PROJECT_STATUS* — the `project-status` skill handles this on demand, no need for a session-end trigger
- *UserPromptSubmit context injection* — too aggressive; CLAUDE.md is loaded every turn already

---

## Skills (on-demand)

Each skill lives in `.claude/skills/<name>/SKILL.md`. The frontmatter `description` is what Claude matches against user intent. To invoke: type `/<skill-name>` or ask Claude to "run X" / "check Y".

| Skill | When to use | Verified |
|---|---|---|
| **`run-evals`** | "run evals", before deploy, to populate the dashboard | Used during build — produced the 17/17 dashboard run |
| **`smoke-test`** | After deploy or before sharing the URL | Used on local + deployed URL — both 5/5 PASS |
| **`deploy-apprunner`** | "deploy", "ship", "push to prod" | Used to push the live URL |
| **`bootstrap-db`** | Fresh start, after schema changes | Used to apply schema + seeds against Supabase |
| **`local-dev`** | "run locally", "start dev" | Spec'd; user can invoke when wanting parallel backend+frontend |
| **`policy-audit`** | Before commit, before deploy, after policy/tools edits | Spec'd; runs both review agents in parallel |
| **`project-status`** | "where are we", "what's left", session start after a break | Spec'd; reads PROJECT_STATUS.md and auto-memory, updates if state changed |

Each skill has a SKILL.md with frontmatter (`name`, `description`) and step-by-step instructions Claude follows. Skills are NOT executable scripts — they're prompts. The actual commands live inside the skill body and Claude runs them via the Bash tool.

---

## Agents (specialist reviewers)

Each agent lives in `.claude/agents/<name>.md` with frontmatter declaring `name`, `description`, and allowed `tools`. Both project-local agents are read-only (`tools: Read, Bash`) — they never edit code.

### `policy-auditor`

**When to invoke:** proactively after edits to `backend/app/policy/*` or `backend/app/tools/*`. Also fires automatically via the `postedit-policy-reminder` hook.

**What it checks** (full spec in [.claude/agents/policy-auditor.md](.claude/agents/policy-auditor.md)):
1. Tool registered in `TOOL_REGISTRY`
2. Policy rule exists in `POLICY_RULES` (default-deny otherwise)
3. Tenant boundary check on `target_user`
4. Role check (`requires_hitl_for`) on privileged actions
5. Audit log calls before AND after execution
6. Deny reasons are human-readable
7. No direct `TOOL_REGISTRY[...]` access outside the gateway

**Latest run against the current tree:** `0 CRITICAL · 2 WARNING · 1 NIT`. Both warnings are minor: eval coverage doesn't name `check_vpn_status` or `reset_password` by literal string (functionally covered via input prompts), and a tiny inconsistency in audit-trail wording when a registered rule lacks a tool implementation (currently impossible — all rules have implementations).

### `tenant-isolation-checker`

**When to invoke:** before each commit and before deploy. Note: the `precommit-guard` hook covers a subset of these checks mechanically — the agent goes deeper.

**What it checks** (full spec in [.claude/agents/tenant-isolation-checker.md](.claude/agents/tenant-isolation-checker.md)):
1. SQL on memory tables includes `WHERE tenant_id`
2. INSERTs into memory tables include `tenant_id` column
3. `tenant_id` never sourced from request body
4. Vector retrievals always filter by `tenant_id`
5. Memory write functions accept the full `(tenant_id, user_id, session_id)` tuple
6. Frontend doesn't send `tenant_id` in JSON body

**Latest run against the current tree:** `0 CRITICAL · 0 WARNING · 0 NIT`. Fully clean.

---

## How they interlock

```
Edit a policy file
      |
      v
postedit-policy-reminder.sh fires (PostToolUse)
      |
      v
Claude is reminded to invoke policy-auditor
      |
      v
policy-auditor reviews, returns CRITICAL/WARNING/NIT
      |
      v
Claude fixes any CRITICAL findings
      |
      v
Try `git commit -m ...`
      |
      v
precommit-guard.sh fires (PreToolUse)
      +-- mechanical grep for tenant-isolation + secret-leak violations
      |
      v
If clean: commit proceeds. If not: blocked with file:line.

Try `aws apprunner start-deployment ...`
      |
      v
predeploy-reminder.sh fires (soft) — run smoke-test, warm cold start
      |
      v
Deploy proceeds; user runs smoke-test skill against deployed URL
```

This stack is what makes the security narrative more than aspirational — the demo's own development workflow is checked by the same primitives that check production behavior at runtime.

---

## Verifying the automation works

Every claim in this doc has been verified during the live build:

| Claim | How verified |
|---|---|
| `precommit-guard` blocks violations | Synthetic `SELECT * FROM episodic_memory WHERE user_id = ...` (no tenant_id) → exit 2 with file:line |
| `precommit-guard` allows clean tree | `git commit` simulated → exit 0 |
| `predeploy-reminder` fires on deploy commands | Simulated `aws apprunner start-deployment` → reminder printed |
| `postedit-policy-reminder` fires on policy/tools edits | Simulated edit on `backend/app/policy/rules.py` → reminder printed |
| `postedit-policy-reminder` ignores unrelated edits | Simulated edit on `frontend/app/page.tsx` → no output |
| `policy-auditor` agent works | Run live against tree → 0 CRITICAL findings, 2 minor warnings reported with file:line |
| `tenant-isolation-checker` agent works | Run live against tree → 0 findings across all 6 checks |
| `run-evals` skill produces dashboard data | Used to populate `eval_results` (17/17 cases) |
| `smoke-test` skill validates 5 demo scenarios | Run against local + deployed → both 5/5 PASS |
| `deploy-apprunner` skill builds + pushes + deploys | Used to ship the live URL |

If any of these fall over in the future, the verifying command is one shell line away — no infrastructure to debug.
