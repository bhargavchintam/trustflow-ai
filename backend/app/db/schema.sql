CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS episodic_memory (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    text NOT NULL,
  user_id      text NOT NULL,
  session_id   text NOT NULL,
  role         text NOT NULL,
  content      text NOT NULL,
  content_tsv  tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  embedding        vector(1024),
  embedding_status text NOT NULL DEFAULT 'ok',
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS episodic_memory_tenant_user_created_idx
  ON episodic_memory (tenant_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS episodic_memory_embedding_idx
  ON episodic_memory USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS episodic_memory_content_tsv_idx
  ON episodic_memory USING GIN (content_tsv);

CREATE TABLE IF NOT EXISTS semantic_memory (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           text NOT NULL,
  user_id             text NOT NULL,
  fact                text NOT NULL,
  source_episode_id   uuid REFERENCES episodic_memory(id) ON DELETE SET NULL,
  confidence          float NOT NULL DEFAULT 0.8,
  corroboration_count int NOT NULL DEFAULT 1,
  embedding           vector(1024),
  embedding_status    text NOT NULL DEFAULT 'ok',
  last_updated_at     timestamptz NOT NULL DEFAULT now(),
  created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS semantic_memory_tenant_user_idx
  ON semantic_memory (tenant_id, user_id);
CREATE INDEX IF NOT EXISTS semantic_memory_embedding_idx
  ON semantic_memory USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS procedural_memory (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           text NOT NULL,
  problem_signature   text NOT NULL,
  steps               jsonb NOT NULL,
  success_count       int NOT NULL DEFAULT 0,
  last_used_at        timestamptz,
  embedding           vector(1024),
  created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS procedural_memory_tenant_idx
  ON procedural_memory (tenant_id);
CREATE INDEX IF NOT EXISTS procedural_memory_embedding_idx
  ON procedural_memory USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS tickets (
  id              text PRIMARY KEY,
  tenant_id       text NOT NULL,
  user_id         text NOT NULL,
  action          text NOT NULL,
  status          text NOT NULL DEFAULT 'open',
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tickets_tenant_user_created_idx
  ON tickets (tenant_id, user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tool_audit (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  correlation_id  uuid NOT NULL,
  tenant_id       text NOT NULL,
  user_id         text NOT NULL,
  session_id      text NOT NULL,
  message_id      uuid NOT NULL,
  event_type      text NOT NULL,
  payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
  decision        text,
  reason          text,
  latency_ms      int,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tool_audit_tenant_user_session_idx
  ON tool_audit (tenant_id, user_id, session_id, created_at);
CREATE INDEX IF NOT EXISTS tool_audit_correlation_idx
  ON tool_audit (correlation_id);
CREATE INDEX IF NOT EXISTS tool_audit_message_idx
  ON tool_audit (message_id);

CREATE TABLE IF NOT EXISTS user_roles (
  tenant_id   text NOT NULL,
  user_id     text NOT NULL,
  role        text NOT NULL DEFAULT 'employee',
  PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS eval_results (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id          text NOT NULL,
  category        text NOT NULL,
  case_id         text NOT NULL,
  input           text,
  expected        jsonb,
  actual          jsonb,
  passed          boolean NOT NULL,
  latency_ms      int,
  cost_usd        float,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS eval_results_run_idx
  ON eval_results (run_id, category);
