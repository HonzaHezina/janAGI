-- janAGI RAG + Agent Schema
-- Source of truth for the janagi business database.
-- Matches the LIVE n8n workflows (WF_40, WF_41, memory_workflows).
--
-- Tables:  rag.clients, projects, conversations, runs, events, artifacts,
--          sources, documents, chunks
-- Functions: start_run_for_thread, log_event, finish_run, search_chunks
-- View:    v_messages

-- ==========================================
-- 0. PREREQUISITES
-- ==========================================

CREATE SCHEMA IF NOT EXISTS rag;
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- 1. CORE ENTITIES
-- ==========================================

-- Clients (Tenants)
CREATE TABLE IF NOT EXISTS rag.clients (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_key text        NOT NULL,
  name       text,
  metadata   jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_key)
);

-- Projects (Workspaces)
CREATE TABLE IF NOT EXISTS rag.projects (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   uuid        NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_key text        NOT NULL,
  name        text,
  metadata    jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, project_key)
);

-- Conversations (Threads)
CREATE TABLE IF NOT EXISTS rag.conversations (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id     uuid        NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id    uuid        REFERENCES rag.projects(id) ON DELETE CASCADE,
  channel       text        NOT NULL DEFAULT 'telegram',
  thread_key    text        NOT NULL,
  title         text,
  metadata      jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  last_event_at timestamptz,
  UNIQUE (client_id, project_id, channel, thread_key)
);

-- Runs (Execution sessions)
CREATE TABLE IF NOT EXISTS rag.runs (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       uuid        REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id      uuid        REFERENCES rag.projects(id) ON DELETE CASCADE,
  conversation_id uuid        REFERENCES rag.conversations(id) ON DELETE SET NULL,
  kind            text        NOT NULL,           -- 'chat', 'web_fetch', 'web_search', 'spec_build'
  status          text        NOT NULL DEFAULT 'running', -- 'running', 'success', 'failed'
  summary         text,                            -- outcome description (set by finish_run)
  metadata        jsonb       NOT NULL DEFAULT '{}'::jsonb,
  started_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz
);

-- Events (Append-only audit log)
-- Column names match WF_40/WF_41 live queries exactly.
CREATE TABLE IF NOT EXISTS rag.events (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id          uuid        REFERENCES rag.runs(id) ON DELETE CASCADE,
  client_id       uuid        REFERENCES rag.clients(id),
  project_id      uuid        REFERENCES rag.projects(id),
  conversation_id uuid        REFERENCES rag.conversations(id),
  actor_type      text        NOT NULL,            -- 'user', 'n8n', 'openclaw', 'system'
  actor_name      text,                            -- 'ai_jackie', 'telegram', 'subwf:web'
  event_type      text        NOT NULL,            -- 'message', 'tool_call', 'tool_result', 'error'
  name            text,                            -- sub-type: 'approval', 'action_draft', 'openclaw', 'action_draft_sent'
  payload         jsonb       NOT NULL DEFAULT '{}'::jsonb,
  ts              timestamptz NOT NULL DEFAULT now()
);

-- Artifacts (Generated outputs)
-- Column names match WF_41 INSERT INTO rag.artifacts exactly.
CREATE TABLE IF NOT EXISTS rag.artifacts (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       uuid        REFERENCES rag.clients(id),
  project_id      uuid        REFERENCES rag.projects(id),
  conversation_id uuid        REFERENCES rag.conversations(id),
  run_id          uuid        REFERENCES rag.runs(id) ON DELETE CASCADE,
  kind            text        NOT NULL,            -- 'openclaw_web_result', 'locked.json', 'spec.md'
  title           text,
  content_text    text,                            -- text content
  metadata        jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- ==========================================
-- 2. KNOWLEDGE BASE (RAG)
-- ==========================================

-- Sources (Where data comes from)
CREATE TABLE IF NOT EXISTS rag.sources (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid        REFERENCES rag.projects(id) ON DELETE CASCADE,
  type       text        NOT NULL,                -- 'url', 'file', 'telegram'
  uri        text        NOT NULL,
  metadata   jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Documents (Parent content units)
CREATE TABLE IF NOT EXISTS rag.documents (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id  uuid        REFERENCES rag.sources(id) ON DELETE CASCADE,
  project_id uuid        REFERENCES rag.projects(id) ON DELETE CASCADE,
  hash       text,
  metadata   jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Chunks (Vector store — RAG retrieval target)
-- Uses vector() without fixed dimension — allows any embedding model.
CREATE TABLE IF NOT EXISTS rag.chunks (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid        REFERENCES rag.documents(id) ON DELETE CASCADE,
  project_id  uuid        REFERENCES rag.projects(id) ON DELETE CASCADE,
  content     text        NOT NULL,
  embedding   vector,                              -- flexible: any embedding model / dimension
  chunk_index int,
  metadata    jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ==========================================
-- 3. VIEW
-- ==========================================

-- Convenience view: human-readable message log
CREATE OR REPLACE VIEW rag.v_messages AS
  SELECT
    id, ts, client_id, project_id, conversation_id, run_id,
    actor_type,
    payload->>'role'  AS role,
    payload->>'text'  AS text
  FROM rag.events
  WHERE event_type = 'message';

-- ==========================================
-- 4. INDEXES
-- ==========================================

-- Vector search: HNSW requires fixed-dimension column.
-- Create AFTER first data insert when you know the embedding dimension:
--   CREATE INDEX idx_chunks_embedding_hnsw
--     ON rag.chunks USING hnsw (embedding vector_cosine_ops);

-- Events: history loading (WF_40 "Load history" node)
CREATE INDEX IF NOT EXISTS idx_events_conv_type_ts
  ON rag.events (conversation_id, event_type, ts DESC);

-- Events: action draft lookup (WF_41 CTEs)
CREATE INDEX IF NOT EXISTS idx_events_type_name
  ON rag.events (event_type, name);

-- Events: run timeline
CREATE INDEX IF NOT EXISTS idx_events_run_id
  ON rag.events (run_id, ts);

-- Runs: conversation lookup
CREATE INDEX IF NOT EXISTS idx_runs_conversation
  ON rag.runs (conversation_id, started_at DESC);

-- Artifacts: per-run listing
CREATE INDEX IF NOT EXISTS idx_artifacts_run
  ON rag.artifacts (run_id, created_at);

-- ==========================================
-- 5. FUNCTIONS
-- ==========================================

-- FUNCTION: start_run_for_thread
-- Used by WF_40 "Start run" and WF_41 "Start SubRun".
-- Resolves or creates a conversation, then creates a new run.
-- Returns: conversation_id, run_id, is_new_conversation
CREATE OR REPLACE FUNCTION rag.start_run_for_thread(
  p_client_id  uuid,
  p_project_id uuid,
  p_channel    text,
  p_thread_key text,
  p_kind       text,
  p_title      text,
  p_run_meta   jsonb DEFAULT '{}'::jsonb,
  p_conv_meta  jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE (conversation_id uuid, run_id uuid, is_new_conversation boolean)
LANGUAGE plpgsql
AS $$
DECLARE
  v_conv_id uuid;
  v_run_id  uuid;
  v_is_new  boolean := false;
BEGIN
  -- 1. Resolve or create conversation
  SELECT c.id INTO v_conv_id
  FROM rag.conversations c
  WHERE c.client_id  = p_client_id
    AND c.project_id = p_project_id
    AND c.channel    = p_channel
    AND c.thread_key = p_thread_key;

  IF v_conv_id IS NULL THEN
    INSERT INTO rag.conversations (client_id, project_id, channel, thread_key, title, metadata)
      VALUES (p_client_id, p_project_id, p_channel, p_thread_key, p_title, p_conv_meta)
      RETURNING id INTO v_conv_id;
    v_is_new := true;
  END IF;

  -- 2. Create run
  INSERT INTO rag.runs (client_id, project_id, conversation_id, kind, metadata)
  VALUES (p_client_id, p_project_id, v_conv_id, p_kind, p_run_meta)
  RETURNING id INTO v_run_id;

  -- 3. Touch conversation
  UPDATE rag.conversations SET last_event_at = now() WHERE id = v_conv_id;

  RETURN QUERY SELECT v_conv_id, v_run_id, v_is_new;
END;
$$;

-- FUNCTION: log_event (9-argument version)
-- Used by WF_40 "Log user message", "Log assistant message", "Log action draft".
-- Used by WF_41 "Log approval", "Log tool_call", "Log tool_result", "Log Error".
CREATE OR REPLACE FUNCTION rag.log_event(
  p_client_id       uuid,
  p_project_id      uuid,
  p_conversation_id uuid,
  p_run_id          uuid,
  p_actor_type      text,
  p_actor_name      text,
  p_event_type      text,
  p_name            text,
  p_payload         jsonb DEFAULT '{}'::jsonb
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_id uuid;
BEGIN
  INSERT INTO rag.events (
    run_id, client_id, project_id, conversation_id,
    actor_type, actor_name, event_type, name, payload
  )
  VALUES (
    p_run_id, p_client_id, p_project_id, p_conversation_id,
    p_actor_type, p_actor_name, p_event_type, p_name, p_payload
  )
  RETURNING id INTO v_id;

  -- Touch conversation timestamp
  IF p_conversation_id IS NOT NULL THEN
    UPDATE rag.conversations SET last_event_at = now()
    WHERE id = p_conversation_id;
  END IF;

  RETURN v_id;
END;
$$;

-- FUNCTION: finish_run
-- Used by WF_41 "Finish run" node.
CREATE OR REPLACE FUNCTION rag.finish_run(
  p_run_id   uuid,
  p_status   text  DEFAULT 'completed',
  p_summary  text  DEFAULT NULL,
  p_metadata jsonb DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE rag.runs
  SET status      = p_status,
      finished_at = now(),
      summary     = COALESCE(p_summary, summary),
      metadata    = CASE
                      WHEN p_metadata IS NOT NULL THEN metadata || p_metadata
                      ELSE metadata
                    END
  WHERE id = p_run_id;
END;
$$;

-- FUNCTION: search_chunks (Semantic search)
-- Used by memory_workflows.json "Postgres Search" node.
CREATE OR REPLACE FUNCTION rag.search_chunks(
  p_project_key     text,
  p_embedding       vector,
  p_match_threshold float,
  p_match_count     int
)
RETURNS TABLE (
  id         uuid,
  content    text,
  similarity float,
  metadata   jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.content,
    (1 - (c.embedding <=> p_embedding))::float AS similarity,
    c.metadata
  FROM rag.chunks c
  JOIN rag.projects p ON c.project_id = p.id
  WHERE p.project_key = p_project_key
    AND 1 - (c.embedding <=> p_embedding) > p_match_threshold
  ORDER BY c.embedding <=> p_embedding
  LIMIT p_match_count;
END;
$$;

-- ==========================================
-- 6. SEED DATA
-- ==========================================
-- These UUIDs are hardcoded in WF_40 and WF_41.

INSERT INTO rag.clients (id, client_key, name)
VALUES ('781594f6-132b-4d47-9933-6499223dbd56', 'default', 'Default')
ON CONFLICT (client_key) DO NOTHING;

INSERT INTO rag.projects (id, client_id, project_key, name)
VALUES (
  '56c83308-384e-4e27-8893-2aa46b845851',
  '781594f6-132b-4d47-9933-6499223dbd56',
  'janagi',
  'janAGI'
)
ON CONFLICT (client_id, project_key) DO NOTHING;
