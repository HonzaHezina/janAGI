-- janAGI unified RAG + audit schema (rag.*)
-- Optimized for: Chat History, Spec-Kit CLI usage, and Vector Search
--
-- STRUCTURE:
-- 1. Clients (Tenants/Users)
-- 2. Projects (Repositories/Workspaces) -> NEW for CLI support
-- 3. Conversations (Threads in Telegram/CLI)
-- 4. Runs (Agent executions)
-- 5. Events (Chat log / Audit trail)
-- 6. Janagi Documents (Unified Vector Store)

CREATE SCHEMA IF NOT EXISTS rag;

-- 1. Clients (Tenants)
CREATE TABLE IF NOT EXISTS rag.clients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_key text NOT NULL,
  name text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_key)
);

-- 2. Projects (Workspace/Repo contexts) - Enables separation of "n8n chat" vs "CLI tool work"
CREATE TABLE IF NOT EXISTS rag.projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_key text NOT NULL,  -- e.g. 'janagi-core', 'cli-tool-x'
  name text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, project_key)
);

-- 3. Conversations (Threads/Channels)
CREATE TABLE IF NOT EXISTS rag.conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  channel text NOT NULL,            -- 'telegram', 'cli', 'n8n', 'openclaw'
  thread_key text NOT NULL,         -- 'chat_123', 'pr_456'
  title text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_event_at timestamptz,
  UNIQUE (client_id, project_id, channel, thread_key)
);

-- 4. Runs (Agent executions / Spec-Kit jobs)
CREATE TABLE IF NOT EXISTS rag.runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  conversation_id uuid NOT NULL REFERENCES rag.conversations(id) ON DELETE CASCADE,
  run_type text NOT NULL,           -- 'chat', 'spec_kit_init', 'cli_exec', 'web_browsing'
  status text NOT NULL DEFAULT 'running',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

-- 5. Events (Atomic Chat History & Audit Log)
-- This is where your n8n chats and CLI outputs are stored.
CREATE TABLE IF NOT EXISTS rag.events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES rag.projects(id) ON DELETE CASCADE,
  conversation_id uuid NOT NULL REFERENCES rag.conversations(id) ON DELETE CASCADE,
  run_id uuid REFERENCES rag.runs(id) ON DELETE SET NULL,

  event_no bigserial NOT NULL,
  event_ts timestamptz NOT NULL DEFAULT now(),

  event_type text NOT NULL,         -- 'message', 'tool_call', 'stdout', 'error', 'spec_kit_step'
  actor_role text NOT NULL,         -- 'user', 'assistant', 'tool', 'system'
  channel text NOT NULL,
  content text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,  -- structured data
  
  -- Optimized indexes
  CONSTRAINT events_content_check CHECK (content IS NOT NULL OR payload != '{}'::jsonb)
);

CREATE INDEX IF NOT EXISTS rag_events_conversation_order_idx ON rag.events (conversation_id, event_no);
CREATE INDEX IF NOT EXISTS rag_events_run_idx ON rag.events (run_id);
CREATE INDEX IF NOT EXISTS rag_events_payload_gin ON rag.events USING gin (payload);

-- 6. Unified Vector Store (janagi_documents)
-- Serves as knowledge base for both chats and CLI specs.
CREATE TABLE IF NOT EXISTS rag.janagi_documents (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   uuid NOT NULL REFERENCES rag.clients(id) ON DELETE CASCADE,
  project_id  uuid REFERENCES rag.projects(id) ON DELETE CASCADE, -- Scoped to project!
  
  doc_type    text NOT NULL,  -- 'expert_knowledge', 'sop', 'spec', 'code_snippet', 'memory'
  namespace   text NOT NULL DEFAULT 'janagi',
  
  content     text NOT NULL,
  embedding   vector(1536), -- Optimized for OpenAI text-embedding-3-small
  
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Optimization Indexes
CREATE INDEX IF NOT EXISTS janagi_documents_client_idx ON rag.janagi_documents (client_id);
CREATE INDEX IF NOT EXISTS janagi_documents_project_idx ON rag.janagi_documents (project_id);
CREATE INDEX IF NOT EXISTS janagi_documents_type_idx ON rag.janagi_documents (doc_type);

-- IVFFlat index for similarity search (lists=100 is good for up to ~100k rows)
CREATE INDEX IF NOT EXISTS janagi_documents_embedding_ivfflat
  ON rag.janagi_documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- 7. Helper: Auto-create Project Context
CREATE OR REPLACE FUNCTION rag.get_or_create_project(
  p_client_key text,
  p_project_key text
) RETURNS TABLE(client_id uuid, project_id uuid)
LANGUAGE plpgsql
AS $$
DECLARE
  v_client_id uuid;
  v_project_id uuid;
BEGIN
  -- 1. Client
  SELECT id INTO v_client_id FROM rag.clients WHERE client_key = p_client_key;
  IF v_client_id IS NULL THEN
    INSERT INTO rag.clients (client_key, name) VALUES (p_client_key, p_client_key) RETURNING id INTO v_client_id;
  END IF;

  -- 2. Project
  SELECT id INTO v_project_id FROM rag.projects WHERE client_id = v_client_id AND project_key = p_project_key;
  IF v_project_id IS NULL THEN
    INSERT INTO rag.projects (client_id, project_key, name, metadata) 
    VALUES (v_client_id, p_project_key, p_project_key, '{}'::jsonb) 
    RETURNING id INTO v_project_id;
  END IF;

  client_id := v_client_id;
  project_id := v_project_id;
  RETURN NEXT;
END;
$$;

-- 7. Chat Logs (Audit Trail - Simple)
-- Stores raw messages for audit and debugging, distinct from the semantic 'Events'.
CREATE SCHEMA IF NOT EXISTS chat;

CREATE TABLE IF NOT EXISTS chat.messages (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform    text NOT NULL DEFAULT 'telegram', -- 'telegram', 'web', 'cli'
  chat_id     text NOT NULL,
  role        text NOT NULL,                 -- 'user', 'assistant', 'system', 'tool'
  content     text NOT NULL,
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_messages_chat_idx ON chat.messages (platform, chat_id, created_at);

