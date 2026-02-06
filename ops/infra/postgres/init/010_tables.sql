-- Legacy skeleton kept for backwards compatibility with early templates.
-- The current source-of-truth schema is in 020_rag_schema.sql (rag.*).

CREATE TABLE IF NOT EXISTS janagi_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content text NOT NULL,
  embedding vector(1024),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS janagi_documents_metadata_gin
  ON janagi_documents
  USING gin (metadata);

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.lead_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid,
  lead_id uuid,
  score double precision NOT NULL,
  model_version text,
  created_at timestamptz NOT NULL DEFAULT now()
);

