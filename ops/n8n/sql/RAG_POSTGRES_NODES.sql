-- n8n Postgres node snippets (rag.*)
--
-- Why this file exists:
-- - n8n Postgres node does NOT accept named placeholders like :client_id
-- - Use positional parameters ($1..$n) + the node's "Query Parameters" list
-- - Cast text literals to ::text to avoid "unknown" signature mismatches
--
-- Conventions used below:
-- - $1..$n are in the exact order shown in each snippet's "PARAMS" block
-- - Thread keys are stored as TEXT (Telegram chat_id can be negative)
--

-- ==================================
-- 0) Ensure IDs exist (one-time-ish)
-- ==================================
-- Use this when you want stable IDs driven by keys.
-- PARAMS:
--   $1 = client_key (text)  e.g. 'janagi'
--   $2 = client_name (text) e.g. 'janAGI'
--   $3 = project_key (text) e.g. 'main'
--   $4 = project_name (text) e.g. 'Main'
WITH c AS (
  SELECT rag.get_or_create_client($1::text, $2::text) AS client_id
), p AS (
  SELECT rag.get_or_create_project(c.client_id, $3::text, $4::text) AS project_id
  FROM c
)
SELECT (SELECT client_id FROM c) AS client_id,
       (SELECT project_id FROM p) AS project_id;


-- =============================
-- 1) Start run for a thread
-- =============================
-- PARAMS:
--   $1 = client_id (uuid)
--   $2 = project_id (uuid)
--   $3 = channel (text)     e.g. 'telegram'
--   $4 = thread_key (text)  e.g. chat_id as text
--   $5 = run_type (text)    e.g. 'chat'
--   $6 = title (text)       nullable
--   $7 = run_metadata (jsonb)
--   $8 = conversation_metadata (jsonb)
SELECT *
FROM rag.start_run_for_thread(
  $1::uuid,
  $2::uuid,
  $3::text,
  $4::text,
  $5::text,
  NULLIF($6::text, ''),
  COALESCE($7::jsonb, '{}'::jsonb),
  COALESCE($8::jsonb, '{}'::jsonb)
);


-- =============================
-- 2) Log an incoming user msg
-- =============================
-- PARAMS:
--   $1 = client_id (uuid)
--   $2 = project_id (uuid)
--   $3 = conversation_id (uuid)
--   $4 = run_id (uuid)
--   $5 = channel (text)     e.g. 'telegram'
--   $6 = content (text)
--   $7 = payload (jsonb)    raw Telegram message or normalized JSON
SELECT rag.log_event(
  $1::uuid,
  $2::uuid,
  $3::uuid,
  $4::uuid,
  'message'::text,
  'user'::text,
  $5::text,
  $6::text,
  COALESCE($7::jsonb, '{}'::jsonb),
  NULL
) AS event_id;


-- =================================
-- 3) Load recent history (events)
-- =================================
-- PARAMS:
--   $1 = conversation_id (uuid)
--   $2 = limit (int)
SELECT
  event_no,
  event_ts,
  actor_role,
  content,
  payload
FROM rag.events
WHERE conversation_id = $1::uuid
  AND event_type = 'message'::text
  AND actor_role IN ('user'::text, 'assistant'::text)
ORDER BY event_no DESC
LIMIT $2::int;


-- =====================================
-- 4) Log assistant response (non-draft)
-- =====================================
-- PARAMS:
--   $1 = client_id (uuid)
--   $2 = project_id (uuid)
--   $3 = conversation_id (uuid)
--   $4 = run_id (uuid)
--   $5 = channel (text)
--   $6 = content (text)
--   $7 = payload (jsonb)
SELECT rag.log_event(
  $1::uuid,
  $2::uuid,
  $3::uuid,
  $4::uuid,
  'message'::text,
  'assistant'::text,
  $5::text,
  $6::text,
  COALESCE($7::jsonb, '{}'::jsonb),
  NULL
) AS event_id;


-- ==================================
-- 5) Store Action Draft (pending)
-- ==================================
-- PARAMS:
--   $1 = client_id (uuid)
--   $2 = project_id (uuid)
--   $3 = conversation_id (uuid)
--   $4 = run_id (uuid)
--   $5 = channel (text)
--   $6 = draft_json (jsonb)  (2nd line payload from ACTION_DRAFT)
SELECT rag.log_event(
  $1::uuid,
  $2::uuid,
  $3::uuid,
  $4::uuid,
  'action_draft'::text,
  'assistant'::text,
  $5::text,
  NULL,
  COALESCE($6::jsonb, '{}'::jsonb),
  NULL
) AS event_id;


-- ==================================
-- 6) Log approval callback
-- ==================================
-- PARAMS:
--   $1 = client_id (uuid)
--   $2 = project_id (uuid)
--   $3 = conversation_id (uuid)
--   $4 = run_id (uuid)
--   $5 = channel (text)
--   $6 = approval_payload (jsonb)
SELECT rag.log_event(
  $1::uuid,
  $2::uuid,
  $3::uuid,
  $4::uuid,
  'approval'::text,
  'user'::text,
  $5::text,
  NULL,
  COALESCE($6::jsonb, '{}'::jsonb),
  NULL
) AS event_id;


-- =============================
-- 7) Save an artifact
-- =============================
-- PARAMS:
--   $1 = client_id (uuid)
--   $2 = project_id (uuid)
--   $3 = conversation_id (uuid) nullable
--   $4 = run_id (uuid) nullable
--   $5 = kind (text)
--   $6 = mime_type (text) nullable
--   $7 = text_content (text) nullable
--   $8 = json_content (jsonb) nullable
INSERT INTO rag.artifacts (
  client_id, project_id, conversation_id, run_id,
  kind, mime_type, text_content, json_content
) VALUES (
  $1::uuid,
  $2::uuid,
  NULLIF($3::text, '')::uuid,
  NULLIF($4::text, '')::uuid,
  $5::text,
  NULLIF($6::text, ''),
  NULLIF($7::text, ''),
  $8::jsonb
)
RETURNING id AS artifact_id;


-- =============================
-- 8) Finish run
-- =============================
-- PARAMS:
--   $1 = run_id (uuid)
--   $2 = status (text)
--   $3 = metadata_patch (jsonb)
SELECT rag.finish_run(
  $1::uuid,
  COALESCE(NULLIF($2::text, ''), 'finished'::text),
  COALESCE($3::jsonb, '{}'::jsonb)
);
