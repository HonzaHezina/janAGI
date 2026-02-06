-- n8n Postgres node SQL templates (rag.*)
--
-- These snippets match the stored functions in 020_rag_schema.sql.
-- Use positional parameters ($1..$n) in n8n's "Query Parameters" field.
--
-- Functions available:
--   rag.start_run(client_key, project_key, conversation_key, run_type, metadata) → uuid
--   rag.log_event(run_id, event_type, actor_role, content, payload) → uuid
--   rag.finish_run(run_id, status) → void
--   rag.search_chunks(project_key, embedding, threshold, count) → table
--

-- =============================
-- 1) Start a new run
-- =============================
-- PARAMS:
--   $1 = client_key (text)       e.g. 'janagi'
--   $2 = project_key (text)      e.g. 'janagi'
--   $3 = conversation_key (text) e.g. Telegram chat_id as text
--   $4 = run_type (text)         e.g. 'chat', 'tool', 'spec_audit'
SELECT rag.start_run($1, $2, $3, $4) AS run_id;


-- =============================
-- 2) Log user message
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)     from start_run result
--   $2 = content (text)    the user's message text
--   $3 = payload (jsonb)   optional: raw Telegram message JSON
SELECT rag.log_event($1, 'message', 'user', $2, COALESCE($3::jsonb, '{}'::jsonb)) AS event_id;


-- =============================
-- 3) Log assistant response
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)
--   $2 = content (text)    the assistant's response text
--   $3 = payload (jsonb)   optional: model metadata, tokens used, etc.
SELECT rag.log_event($1, 'message', 'assistant', $2, COALESCE($3::jsonb, '{}'::jsonb)) AS event_id;


-- =============================
-- 4) Log action draft (approval pending)
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)
--   $2 = draft_json (jsonb)  the ACTION_DRAFT payload
SELECT rag.log_event($1, 'action_draft', 'assistant', NULL, $2::jsonb) AS event_id;


-- =============================
-- 5) Log approval callback
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)
--   $2 = approval_payload (jsonb)  e.g. {"decision": "approved", "callback_data": "..."}
SELECT rag.log_event($1, 'approval', 'user', NULL, $2::jsonb) AS event_id;


-- =============================
-- 6) Log tool call
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)
--   $2 = content (text)    tool name or description
--   $3 = payload (jsonb)   tool input/output
SELECT rag.log_event($1, 'tool_call', 'system', $2, $3::jsonb) AS event_id;


-- =============================
-- 7) Load recent conversation history
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)   — we look up conversation_id from the run
--   $2 = limit (int)     — number of recent events to load
SELECT e.event_type, e.actor_role, e.content, e.payload, e.created_at
FROM rag.events e
JOIN rag.runs r ON r.id = $1::uuid
WHERE e.run_id IN (
  SELECT id FROM rag.runs WHERE conversation_id = r.conversation_id
)
AND e.event_type = 'message'
AND e.actor_role IN ('user', 'assistant')
ORDER BY e.created_at DESC
LIMIT $2::int;


-- =============================
-- 8) Semantic search (RAG retrieval)
-- =============================
-- PARAMS:
--   $1 = project_key (text)     e.g. 'janagi'
--   $2 = embedding (vector)     the query embedding as string
--   $3 = threshold (float)      e.g. 0.5
--   $4 = match_count (int)      e.g. 5
SELECT * FROM rag.search_chunks($1, $2::vector, $3::float, $4::int);


-- =============================
-- 9) Save an artifact
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)
--   $2 = project_id (uuid)     from run context
--   $3 = key (text)            e.g. 'locked.json', 'spec.md'
--   $4 = type (text)           e.g. 'json', 'file', 'text'
--   $5 = content (text)        text content
--   $6 = data (jsonb)          structured data (nullable)
INSERT INTO rag.artifacts (run_id, project_id, key, type, content, data)
VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb)
ON CONFLICT (run_id, key) DO UPDATE SET content = EXCLUDED.content, data = EXCLUDED.data
RETURNING id AS artifact_id;


-- =============================
-- 10) Finish run
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)
--   $2 = status (text)   'completed' or 'failed'
SELECT rag.finish_run($1, COALESCE(NULLIF($2, ''), 'completed'));
