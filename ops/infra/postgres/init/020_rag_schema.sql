-- janAGI unified RAG + audit schema (rag.*)
--
-- Goals:
-- - Single source of truth for everything that happens (rag.events)
-- - Optional large payload storage (rag.artifacts)
-- - Retrieval index (rag.documents + rag.chunks) without duplicating semantics
--
-- NOTE: This script is designed for greenfield init (docker-entrypoint-initdb.d).

CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.clients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_key text NOT NULL,
  name text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_key)
);

CREATE TABLE IF NOT EXISTS rag.projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_key text NOT NULL,
  name text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, project_key)
);

CREATE TABLE IF NOT EXISTS rag.conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  channel text NOT NULL,            -- e.g. 'telegram'
  thread_key text NOT NULL,         -- e.g. chat_id or thread id as text
  title text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_event_at timestamptz,
  UNIQUE (client_id, project_id, channel, thread_key)
);

CREATE TABLE IF NOT EXISTS rag.runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  conversation_id uuid NOT NULL REFERENCES rag.conversations(id) ON DELETE CASCADE,
  run_type text NOT NULL,           -- e.g. 'chat', 'tool', 'web'
  status text NOT NULL DEFAULT 'running',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS rag.artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  conversation_id uuid REFERENCES rag.conversations(id) ON DELETE SET NULL,
  run_id uuid REFERENCES rag.runs(id) ON DELETE SET NULL,
  kind text NOT NULL,               -- e.g. 'openclaw.request', 'openclaw.response', 'diff', 'log'
  mime_type text,
  text_content text,
  json_content jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag.events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  conversation_id uuid NOT NULL REFERENCES rag.conversations(id) ON DELETE CASCADE,
  run_id uuid REFERENCES rag.runs(id) ON DELETE SET NULL,

  event_no bigserial NOT NULL,
  event_ts timestamptz NOT NULL DEFAULT now(),

  event_type text NOT NULL,         -- 'message', 'tool_call', 'tool_result', 'error', 'approval', ...
  actor_role text NOT NULL,         -- 'user', 'assistant', 'tool', 'system'
  channel text NOT NULL,            -- 'telegram', 'n8n', 'openclaw', 'cli'
  content text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  artifact_id uuid REFERENCES rag.artifacts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS rag_events_conversation_order_idx
  ON rag.events (conversation_id, event_no);

CREATE INDEX IF NOT EXISTS rag_events_run_idx
  ON rag.events (run_id);

CREATE INDEX IF NOT EXISTS rag_events_payload_gin
  ON rag.events USING gin (payload);

CREATE TABLE IF NOT EXISTS rag.sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  source_type text NOT NULL,        -- 'telegram', 'web', 'file', 'sop', ...
  source_key text,                  -- external stable id if available
  uri text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Dedupe across optional identifiers (NULL-safe uniqueness)
CREATE UNIQUE INDEX IF NOT EXISTS rag_sources_dedupe_idx
  ON rag.sources (
    client_id,
    project_id,
    source_type,
    COALESCE(source_key, ''),
    COALESCE(uri, '')
  );

CREATE TABLE IF NOT EXISTS rag.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  source_id uuid REFERENCES rag.sources(id) ON DELETE SET NULL,
  external_id text,
  title text,
  content text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rag_documents_metadata_gin
  ON rag.documents USING gin (metadata);

CREATE UNIQUE INDEX IF NOT EXISTS rag_documents_dedupe_idx
  ON rag.documents (source_id, COALESCE(external_id, ''));

CREATE TABLE IF NOT EXISTS rag.chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES rag.documents(id) ON DELETE CASCADE,
  chunk_no int NOT NULL,
  content text NOT NULL,
  embedding vector(1024),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, chunk_no)
);

CREATE INDEX IF NOT EXISTS rag_chunks_document_idx
  ON rag.chunks (document_id, chunk_no);

CREATE INDEX IF NOT EXISTS rag_chunks_metadata_gin
  ON rag.chunks USING gin (metadata);

-- -------------------------
-- Helper functions for n8n
-- -------------------------

CREATE OR REPLACE FUNCTION rag.get_or_create_client(
  p_client_key text,
  p_name text DEFAULT NULL,
  p_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_id uuid;
BEGIN
  SELECT id INTO v_id
  FROM rag.clients
  WHERE client_key = p_client_key;

  IF v_id IS NOT NULL THEN
    RETURN v_id;
  END IF;

  INSERT INTO rag.clients (client_key, name, metadata)
  VALUES (p_client_key, p_name, COALESCE(p_metadata, '{}'::jsonb))
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

CREATE OR REPLACE FUNCTION rag.get_or_create_project(
  p_client_id uuid,
  p_project_key text,
  p_name text DEFAULT NULL,
  p_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_id uuid;
BEGIN
  SELECT id INTO v_id
  FROM rag.projects
  WHERE client_id = p_client_id
    AND project_key = p_project_key;

  IF v_id IS NOT NULL THEN
    RETURN v_id;
  END IF;

  INSERT INTO rag.projects (client_id, project_key, name, metadata)
  VALUES (p_client_id, p_project_key, p_name, COALESCE(p_metadata, '{}'::jsonb))
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

CREATE OR REPLACE FUNCTION rag.get_or_create_conversation_for_thread(
  p_client_id uuid,
  p_project_id uuid,
  p_channel text,
  p_thread_key text,
  p_title text DEFAULT NULL,
  p_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_id uuid;
BEGIN
  SELECT id INTO v_id
  FROM rag.conversations
  WHERE client_id = p_client_id
    AND project_id = p_project_id
    AND channel = p_channel
    AND thread_key = p_thread_key;

  IF v_id IS NOT NULL THEN
    RETURN v_id;
  END IF;

  INSERT INTO rag.conversations (client_id, project_id, channel, thread_key, title, metadata, last_event_at)
  VALUES (p_client_id, p_project_id, p_channel, p_thread_key, p_title, COALESCE(p_metadata, '{}'::jsonb), now())
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

CREATE OR REPLACE FUNCTION rag.start_run_for_thread(
  p_client_id uuid,
  p_project_id uuid,
  p_channel text,
  p_thread_key text,
  p_run_type text,
  p_title text DEFAULT NULL,
  p_run_metadata jsonb DEFAULT '{}'::jsonb,
  p_conversation_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS TABLE(conversation_id uuid, run_id uuid)
LANGUAGE plpgsql
AS $$
DECLARE
  v_conversation_id uuid;
  v_run_id uuid;
BEGIN
  v_conversation_id := rag.get_or_create_conversation_for_thread(
    p_client_id,
    p_project_id,
    p_channel,
    p_thread_key,
    p_title,
    COALESCE(p_conversation_metadata, '{}'::jsonb)
  );

  INSERT INTO rag.runs (client_id, project_id, conversation_id, run_type, metadata)
  VALUES (
    p_client_id,
    p_project_id,
    v_conversation_id,
    p_run_type,
    COALESCE(p_run_metadata, '{}'::jsonb)
  )
  RETURNING id INTO v_run_id;

  -- Best-effort update
  UPDATE rag.conversations
  SET last_event_at = now()
  WHERE id = v_conversation_id;

  conversation_id := v_conversation_id;
  run_id := v_run_id;
  RETURN NEXT;
END;
$$;

CREATE OR REPLACE FUNCTION rag.log_event(
  p_client_id uuid,
  p_project_id uuid,
  p_conversation_id uuid,
  p_run_id uuid,
  p_event_type text,
  p_actor_role text,
  p_channel text,
  p_content text,
  p_payload jsonb DEFAULT '{}'::jsonb,
  p_artifact_id uuid DEFAULT NULL
) RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_id uuid;
BEGIN
  INSERT INTO rag.events (
    client_id,
    project_id,
    conversation_id,
    run_id,
    event_type,
    actor_role,
    channel,
    content,
    payload,
    artifact_id
  ) VALUES (
    p_client_id,
    p_project_id,
    p_conversation_id,
    p_run_id,
    p_event_type,
    p_actor_role,
    p_channel,
    p_content,
    COALESCE(p_payload, '{}'::jsonb),
    p_artifact_id
  )
  RETURNING id INTO v_id;

  UPDATE rag.conversations
  SET last_event_at = now()
  WHERE id = p_conversation_id;

  RETURN v_id;
END;
$$;

CREATE OR REPLACE FUNCTION rag.finish_run(
  p_run_id uuid,
  p_status text DEFAULT 'finished',
  p_metadata_patch jsonb DEFAULT '{}'::jsonb
) RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE rag.runs
  SET status = p_status,
      finished_at = now(),
      metadata = COALESCE(metadata, '{}'::jsonb) || COALESCE(p_metadata_patch, '{}'::jsonb)
  WHERE id = p_run_id;
END;
$$;
