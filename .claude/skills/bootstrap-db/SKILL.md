---
name: bootstrap-db
description: Apply the schema (CREATE EXTENSION vector + pgcrypto, all tables/indexes idempotently) and run the seed scripts (Bob + tenant_globex/charlie + user roles). Use when starting fresh, after schema changes, or after wipe.
---

# bootstrap-db

Apply schema + run seeds against the configured DATABASE_URL.

## Pre-flight

Check that `DATABASE_URL` is set in `.env` and the host is reachable:

```bash
cd backend && uv run python -c "import os; from dotenv import load_dotenv; load_dotenv('../.env'); print('DATABASE_URL set:', bool(os.environ.get('DATABASE_URL')))"
```

If unset, stop and tell the user to fill it.

## Steps

```bash
cd "/Users/bhargav/Desktop/TrustFlow AI/backend"

# 1. Apply schema (idempotent — CREATE TABLE IF NOT EXISTS)
uv run python -m app.db.bootstrap

# 2. Seed Bob (VPN history + procedural row + tenant_acme user roles incl. fake CEO)
uv run python -m app.seed.bob_seed

# 3. Seed Charlie at tenant_globex (for cross-tenant isolation eval cases)
uv run python -m app.seed.tenant_isolation_seed
```

## Verify

```bash
psql $DATABASE_URL -c "SELECT count(*) FROM episodic_memory;"
psql $DATABASE_URL -c "SELECT count(*) FROM procedural_memory;"
psql $DATABASE_URL -c "SELECT user_id, role FROM user_roles ORDER BY tenant_id, user_id;"
```

Expected:
- episodic: 6 rows for Bob + 2 for Charlie
- procedural: 1 row (vpn_disconnect_on_wake_macos)
- user_roles: alice/bob/charlie=employee, ceo=executive, plus charlie at tenant_globex

## Failure modes

- `extension "vector" is not available` — pgvector isn't installed. On RDS, enable via parameter group or use a region/version that supports it. On local Postgres: `brew install pgvector`. On Supabase: enable in Dashboard -> Database -> Extensions.
- `role "trustflow" does not exist` — connection string user is wrong. Check DATABASE_URL.
- `permission denied for schema public` — your DB user can't CREATE TABLE. Grant or use the owner.
