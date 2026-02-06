-- Analytics tables (written by MindsDB / batch jobs)
-- Keep analytics separate from rag.* so it can evolve independently.

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
