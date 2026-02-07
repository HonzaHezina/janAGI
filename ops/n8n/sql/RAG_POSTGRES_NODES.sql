-- n8n Postgres node SQL templates (rag.*)
--
-- Matches the LIVE function signatures in 020_rag_schema.sql.
-- Copy-paste into n8n Postgres nodes and map parameters.
--
-- Functions:
--   rag.start_run_for_thread(client_id, project_id, channel, thread_key, kind, title, run_meta, conv_meta) → (conversation_id, run_id, is_new_conversation)
--   rag.log_event(client_id, project_id, conversation_id, run_id, actor_type, actor_name, event_type, name, payload) → event_id
--   rag.finish_run(run_id, status, summary, metadata) → void
--   rag.search_chunks(project_key, embedding, threshold, count) → (id, content, similarity, metadata)
--

-- =============================
-- 1) Start a run (with thread resolution)
-- =============================
-- PARAMS (n8n expressions):
--   client_id  (uuid)   — e.g. '781594f6-...'
--   project_id (uuid)   — e.g. '56c83308-...'
--   channel    (text)   — 'telegram'
--   thread_key (text)   — chat_id from Telegram
--   kind       (text)   — 'chat', 'web_fetch', 'spec_build'
--   title      (text)   — e.g. 'Telegram chat 717801484'
SELECT * FROM rag.start_run_for_thread(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  'telegram',
  '{{ $json.message.chat.id }}'::text,
  'chat',
  ('Telegram chat ' || '{{ $json.message.chat.id }}')::text,
  '{}'::jsonb,
  '{}'::jsonb
);


-- =============================
-- 2) Log user message
-- =============================
SELECT rag.log_event(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  '{{ $json.run_id }}'::uuid,
  'user',
  '{{ $json.message.from.id }}'::text,
  'message',
  NULL,
  jsonb_build_object(
    'role', 'user',
    'text', to_jsonb('{{ $json.message.text }}'::text),
    'channel', 'telegram',
    'chat_id', to_jsonb('{{ $json.message.chat.id }}'::text)
  )
) AS event_id;


-- =============================
-- 3) Log assistant response
-- =============================
SELECT rag.log_event(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  '{{ $json.run_id }}'::uuid,
  'n8n',
  'ai_jackie',
  'message',
  NULL,
  jsonb_build_object(
    'role', 'assistant',
    'text', to_jsonb('{{ $json.response_text }}'::text),
    'channel', 'telegram'
  )
) AS event_id;


-- =============================
-- 4) Log action draft
-- =============================
SELECT rag.log_event(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  '{{ $json.run_id }}'::uuid,
  'n8n',
  'ai_jackie',
  'tool_call',
  'action_draft',
  jsonb_build_object(
    'type', 'action_draft',
    'raw', to_jsonb('{{ $json.draft_text }}'::text)
  )
) AS event_id;


-- =============================
-- 5) Log action draft sent (Telegram message ID for callback matching)
-- =============================
SELECT rag.log_event(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  '{{ $json.run_id }}'::uuid,
  'n8n',
  'telegram',
  'tool_result',
  'action_draft_sent',
  jsonb_build_object(
    'status', 'sent',
    'telegram_message_id', '{{ $json.telegram_message_id }}'::text,
    'channel', 'telegram'
  )
) AS event_id;


-- =============================
-- 6) Log approval callback
-- =============================
SELECT rag.log_event(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  NULL,
  'user',
  '{{ $json.telegram_user_id }}'::text,
  'message',
  'approval',
  jsonb_build_object(
    'role', 'user',
    'text', CASE WHEN '{{ $json.decision }}' = 'approved' THEN '[APPROVED]' ELSE '[REJECTED]' END,
    'decision', '{{ $json.decision }}',
    'channel', 'telegram'
  )
) AS event_id;


-- =============================
-- 7) Log tool call (e.g. OpenClaw web action)
-- =============================
SELECT rag.log_event(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  '{{ $json.run_id }}'::uuid,
  'n8n',
  'subwf:web',
  'tool_call',
  'openclaw',
  jsonb_build_object(
    'type', 'web',
    'target', 'openclaw',
    'mode', '{{ $json.mode }}',
    'model', '{{ $json.model }}',
    'input', '{{ $json.input }}'
  )
) AS event_id;


-- =============================
-- 8) Log tool result
-- =============================
SELECT rag.log_event(
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  '{{ $json.run_id }}'::uuid,
  'openclaw',
  '{{ $json.model }}'::text,
  'tool_result',
  'openclaw',
  jsonb_build_object(
    'status', 'success',
    'mode', '{{ $json.mode }}',
    'artifact_id', '{{ $json.artifact_id }}'::text
  )
) AS event_id;


-- =============================
-- 9) Load conversation history
-- =============================
-- Used by WF_40 "Load history" node.
-- Returns last N messages (user + assistant) for AI context injection.
SELECT role, content, ts
FROM (
  SELECT
    COALESCE(payload->>'role', actor_type) AS role,
    COALESCE(
      payload->>'text',
      payload->>'content',
      payload->>'message',
      payload->>'raw'
    ) AS content,
    ts
  FROM rag.events
  WHERE conversation_id = '{{ $json.conversation_id }}'::uuid
    AND event_type = 'message'
    AND COALESCE(payload->>'role', actor_type) IN ('user', 'assistant')
    AND COALESCE(payload->>'text', payload->>'content', payload->>'message', payload->>'raw') IS NOT NULL
  ORDER BY ts DESC
  LIMIT 20
) t
ORDER BY ts ASC;


-- =============================
-- 10) Insert artifact
-- =============================
-- Used by WF_41 "Insert Artifact" node.
INSERT INTO rag.artifacts (
  client_id, project_id, conversation_id, run_id,
  kind, title, content_text, metadata
)
VALUES (
  '{{ $json.client_id }}'::uuid,
  '{{ $json.project_id }}'::uuid,
  '{{ $json.conversation_id }}'::uuid,
  '{{ $json.run_id }}'::uuid,
  '{{ $json.kind }}',
  '{{ $json.title }}'::text,
  '{{ $json.content_text }}'::text,
  '{{ $json.metadata }}'::jsonb
)
RETURNING id AS artifact_id;


-- =============================
-- 11) Semantic search (RAG retrieval)
-- =============================
-- Used by memory_workflows.json "Postgres Search" node.
SELECT * FROM rag.search_chunks(
  '{{ $json.namespace || "janagi" }}',
  '{{ $json.embedding_vec }}'::vector,
  0.5,
  {{ $json.top_k || 5 }}
);


-- =============================
-- 12) Memory upsert (direct chunk insert)
-- =============================
-- Used by memory_workflows.json "Postgres Insert" node.
INSERT INTO rag.chunks (project_id, content, embedding, metadata)
SELECT p.id, '{{ $json.content }}', '{{ $json.embedding_vec }}'::vector, '{{ $json.metadata }}'::jsonb
FROM rag.projects p
WHERE p.project_key = '{{ $json.namespace || "janagi" }}'
RETURNING id;


-- =============================
-- 13) Finish run
-- =============================
-- Used by WF_41 "Finish run" node.
SELECT rag.finish_run(
  '{{ $json.run_id }}'::uuid,
  '{{ $json.status || "success" }}',
  '{{ $json.summary || "" }}',
  '{{ $json.metadata || "{}" }}'::jsonb
);


-- =============================
-- 14) Find conversation by action draft telegram_message_id
-- =============================
-- Used by WF_41 "Start SubRun" to link a callback to its original conversation.
SELECT e.conversation_id
FROM rag.events e
WHERE e.event_type = 'tool_result'
  AND e.name = 'action_draft_sent'
  AND e.payload->>'telegram_message_id' = '{{ $json.telegram_message_id }}'
ORDER BY e.ts DESC
LIMIT 1;
