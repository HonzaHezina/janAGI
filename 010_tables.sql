-- Core operational tables
CREATE TABLE IF NOT EXISTS leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  source_type text NOT NULL,
  source_ref text NOT NULL,
  url text,
  status text NOT NULL DEFAULT 'NEW',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, source_type, source_ref)
);

CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  lead_id uuid NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  role text NOT NULL,
  text text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  lead_id uuid,
  type text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  trace_id uuid NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Vector store (n8n PGVector node friendly)
CREATE TABLE IF NOT EXISTS janagi_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content text NOT NULL,
  embedding vector(1024),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS janagi_documents_metadata_gin
  ON janagi_documents
  USING gin (metadata);

-- Analytics schema for MindsDB outputs
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.trends_daily (
  day date NOT NULL,
  client_id uuid NOT NULL,
  top_topics jsonb NOT NULL,
  top_keywords jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (day, client_id)
);

CREATE TABLE IF NOT EXISTS analytics.lead_scores (
  lead_id uuid PRIMARY KEY,
  client_id uuid NOT NULL,
  score int NOT NULL,
  confidence text,
  features jsonb,
  scored_at timestamptz NOT NULL DEFAULT now()
);
