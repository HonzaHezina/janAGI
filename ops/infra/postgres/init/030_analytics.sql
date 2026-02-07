-- Analytics tables (written by MindsDB / batch jobs)
-- Keep analytics separate from rag.* so it can evolve independently.

CREATE SCHEMA IF NOT EXISTS analytics;

-- Daily topic/keyword aggregation per client (MindsDB daily_trends_job)
CREATE TABLE IF NOT EXISTS analytics.trends_daily (
  day           date        NOT NULL,
  client_id     uuid        NOT NULL,
  top_topics    jsonb       NOT NULL DEFAULT '[]'::jsonb,  -- [{topic, count, sample_text}, ...]
  top_keywords  jsonb       NOT NULL DEFAULT '[]'::jsonb,  -- [{keyword, count}, ...]
  created_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (day, client_id)
);

-- ML-scored leads with confidence and feature breakdown (MindsDB lead_scorer)
CREATE TABLE IF NOT EXISTS analytics.lead_scores (
  lead_id     uuid        PRIMARY KEY,
  client_id   uuid        NOT NULL,
  score       int         NOT NULL CHECK (score >= 0 AND score <= 100),
  confidence  text        CHECK (confidence IN ('high','medium','low')),
  features    jsonb,       -- {response_time_avg, message_count, active_days, ...}
  scored_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lead_scores_client
  ON analytics.lead_scores (client_id, score DESC);

CREATE INDEX IF NOT EXISTS idx_trends_daily_client
  ON analytics.trends_daily (client_id, day DESC);

-- ---- Read-only role for MindsDB ----
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mindsdb_ro') THEN
    CREATE ROLE mindsdb_ro WITH LOGIN PASSWORD 'change_me_mindsdb';
  END IF;
END
$$;

GRANT USAGE ON SCHEMA rag TO mindsdb_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA rag TO mindsdb_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA rag GRANT SELECT ON TABLES TO mindsdb_ro;

GRANT USAGE ON SCHEMA analytics TO mindsdb_ro;
GRANT ALL ON ALL TABLES IN SCHEMA analytics TO mindsdb_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON TABLES TO mindsdb_ro;
