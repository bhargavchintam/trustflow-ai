---
name: project-status
description: Memory keeper for TrustFlow AI. Reads/updates PROJECT_STATUS.md, refreshes auto-memory entries, and prints a tight project-state summary. Use when context feels lost, after a long break, or before handing off.
---

# project-status

Keep project context coherent across long sessions. The 24-hour build has many moving parts — this skill is the anchor.

## When to invoke

- User says "what's the status", "where are we", "what's left", "remind me"
- After a multi-hour break in the conversation
- Before a context-heavy operation (deploy, demo recording, sending to interviewer)
- Whenever a key fact changes: deployed URL, GitHub repo URL, scope decision

## Steps

1. **Read** `PROJECT_STATUS.md` at repo root (`/Users/bhargav/Desktop/TrustFlow AI/PROJECT_STATUS.md`).

2. **Read** the auto-memory index at `/Users/bhargav/.claude/projects/-Users-bhargav-Desktop-TrustFlow-AI/memory/MEMORY.md` and any referenced files.

3. **Read** the plan file at `/Users/bhargav/.claude/plans/here-i-need-you-floofy-map.md` (skim, especially §11 schedule and §12 ships/cuts).

4. **Print a tight summary**:
   - Current schedule block (e.g. "H19-H21 Production deploy")
   - What's done (✅) vs in-progress (⏳) vs pending (⬜)
   - Known live decision points (e.g. "RDS+VPC vs Supabase fallback")
   - Deployed URL + repo URL + Loom URL (or "not yet")
   - Next 1–2 actions

5. **If something has changed** (new URL, new decision, scope update):
   - Update `PROJECT_STATUS.md` with the change
   - Update the relevant auto-memory file (e.g. `project_atomicwork_takehome.md`) if the change is durable
   - Save a new memory entry only if it's novel and applicable to future conversations

## What to KEEP in `PROJECT_STATUS.md`

- Current block / phase
- Done / in-progress / pending checklist (mirrors plan §11)
- Critical URLs once they exist (deployed app, GitHub repo, Loom)
- Live decisions still open

## What NOT to put in `PROJECT_STATUS.md`

- Code snippets (the code is the source of truth)
- Schema (lives in `backend/app/db/schema.sql`)
- Architecture diagrams (in README)
- Detailed scope cuts (in plan §12 and README)

## What to KEEP in auto-memory

- User identity and preferences (`user_role.md`, `feedback_*.md`)
- Project-level facts that survive past this conversation (`project_*.md`)
- External system references (`reference_*.md`)

## What NOT to save to auto-memory

- "What I just did" — that's git history
- Code patterns / conventions — those are in CLAUDE.md and the code itself
- Anything trivially derivable from reading current files
