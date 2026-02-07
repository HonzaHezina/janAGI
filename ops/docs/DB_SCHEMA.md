# Database Schema

> **Single source of truth.** This file documents every table, column, index, and
> function in the `janagi` database. The canonical SQL is
> [`020_rag_schema.sql`](../infra/postgres/init/020_rag_schema.sql) and
> [`030_analytics.sql`](../infra/postgres/init/030_analytics.sql).

## Extensions

| Extension | Purpose |
|-----------|---------|
| `vector` (pgvector) | Vector similarity search (1536-dim embeddings) |
| `pgcrypto` | UUID generation (`gen_random_uuid()`) |
| `pg_trgm` | Trigram similarity (fuzzy text search) |
| `unaccent` | Diacritics removal |

---

## Schema: `rag.*`

### Entity Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `rag.clients` | Tenants | `id` (uuid PK), `client_key` (unique text), `name`, `metadata` (jsonb) |
| `rag.projects` | Workspaces per client | `id`, `client_id` → clients, `project_key` (unique per client), `name`, `metadata` |
| `rag.conversations` | Chat threads | `id`, `client_id`, `project_id`, `channel`, `thread_key`, `title`, `metadata`, `last_event_at` |
| `rag.runs` | Execution sessions | `id`, `client_id`, `project_id`, `conversation_id`, `run_type`, `status`, `summary`, `metadata`, `started_at`, `finished_at` |
| `rag.events` | Append-only audit log | `id`, `run_id`, `client_id`, `project_id`, `conversation_id`, `actor_type`, `actor_name`, `event_type`, `name`, `payload` (jsonb), `ts` |
| `rag.artifacts` | Generated outputs | `id`, `client_id`, `project_id`, `conversation_id`, `run_id`, `kind`, `title`, `content_text`, `metadata` (jsonb), `created_at` |

#### `rag.events` Column Details

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `actor_type` | text | Who created the event | `'user'`, `'n8n'`, `'openclaw'`, `'system'` |
| `actor_name` | text | Specific identity | `'ai_jackie'`, `'telegram'`, `'subwf:web'` |
| `event_type` | text | Event category | `'message'`, `'tool_call'`, `'tool_result'`, `'error'` |
| `name` | text | Sub-type / label | `'approval'`, `'action_draft'`, `'action_draft_sent'`, `'openclaw'` |
| `payload` | jsonb | All event data | `{"role":"user", "text":"...", "channel":"telegram"}` |
| `ts` | timestamptz | Event timestamp | Auto-set to `now()` |

#### `rag.artifacts` Column Details

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `kind` | text | Artifact category | `'openclaw_web_result'`, `'locked.json'`, `'spec.md'` |
| `title` | text | Human-readable title | `'OpenClaw web fetch'` |
| `content_text` | text | Text content of the artifact | Raw text output |
| `metadata` | jsonb | Structured metadata | `{"mode":"fetch", "model":"openclaw:main"}` |

#### `rag.runs.run_type` Values

| Value | Source | Description |
|-------|--------|-------------|
| `'chat'` | WF_40 | Normal Telegram conversation |
| `'web_fetch'` | WF_41 | OpenClaw web fetch sub-run |
| `'web_search'` | WF_41 | OpenClaw web search sub-run |
| `'web_browser'` | WF_41 | OpenClaw browser sub-run |
| `'spec_build'` | WF_30 | Spec-Kit full build |

### RAG Pipeline Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `rag.sources` | Origin of data | `id`, `project_id`, `type` (url/file/telegram), `uri`, `metadata` |
| `rag.documents` | Parent content units | `id`, `source_id`, `project_id`, `hash` (dedup), `metadata` |
| `rag.chunks` | Embedded text chunks | `id`, `document_id`, `project_id`, `content`, `embedding` (vector 1536), `chunk_index`, `metadata` |

### Indexes

| Name | Table | Columns | Type | Purpose |
|------|-------|---------|------|---------|
| `idx_chunks_embedding_hnsw` | `rag.chunks` | `embedding` | HNSW (`vector_cosine_ops`) | Semantic search |
| `idx_events_conv_type_ts` | `rag.events` | `(conversation_id, event_type, ts DESC)` | B-tree | Load history (WF_40) |
| `idx_events_type_name` | `rag.events` | `(event_type, name)` | B-tree | Action draft lookup (WF_41) |
| `idx_events_run_id` | `rag.events` | `(run_id, ts)` | B-tree | Run timeline |
| `idx_runs_conversation` | `rag.runs` | `(conversation_id, started_at DESC)` | B-tree | Conversation runs |
| `idx_artifacts_run` | `rag.artifacts` | `(run_id, created_at)` | B-tree | Per-run artifacts |

---

## Stored Functions

| Function | Signature | Returns | Used By |
|----------|-----------|---------|---------|
| `rag.start_run_for_thread` | `(client_id, project_id, channel, thread_key, kind, title, run_meta, conv_meta)` | `(conversation_id uuid, run_id uuid, is_new_conversation bool)` | WF_40, WF_41 |
| `rag.log_event` | `(client_id, project_id, conversation_id, run_id, actor_type, actor_name, event_type, name, payload)` | `uuid` (event_id) | WF_40, WF_41 |
| `rag.finish_run` | `(run_id, status, summary, metadata)` | `void` | WF_41 |
| `rag.search_chunks` | `(project_key, embedding, threshold, count)` | `(id, content, similarity, metadata)` | memory_workflows |

### Function Details

**`start_run_for_thread`** — Resolves or creates a conversation by
`(client_id, project_id, channel, thread_key)`, then creates a new run.
Updates `conversations.last_event_at`.

**`log_event`** — Inserts a row into `rag.events` with all context columns.
Updates `conversations.last_event_at`. All event data goes in `payload` jsonb.

**`finish_run`** — Sets `runs.status`, `finished_at`, optionally merges
`summary` and `metadata`. Called with `('success', 'Web action completed', {...})`.

**`search_chunks`** — HNSW-accelerated cosine similarity search over `rag.chunks`.
Resolves project by `project_key`. Returns rows above `threshold`, limited to `count`.

---

## Schema: `analytics.*`

Written by MindsDB batch jobs (read-only from n8n). See [`030_analytics.sql`](../infra/postgres/init/030_analytics.sql).

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `analytics.trends_daily` | Daily topic/keyword aggregation | `(day, client_id)` PK, `top_topics` jsonb, `top_keywords` jsonb |
| `analytics.lead_scores` | ML-scored leads | `lead_id` PK, `client_id`, `score` (0–100), `confidence`, `features` jsonb |

### Indexes

| Name | Table | Columns |
|------|-------|---------|
| `idx_lead_scores_client` | `analytics.lead_scores` | `(client_id, score DESC)` |
| `idx_trends_daily_client` | `analytics.trends_daily` | `(client_id, day DESC)` |

### MindsDB Role

```sql
ROLE mindsdb_ro  -- LOGIN, password in env var MINDSDB_PG_PASSWORD
  GRANT SELECT ON rag.*        -- read-only access to source data
  GRANT ALL ON analytics.*     -- write access for batch results
```

---

## Usage from n8n

All SQL templates: [`ops/n8n/sql/RAG_POSTGRES_NODES.sql`](../n8n/sql/RAG_POSTGRES_NODES.sql)

Common pattern (from WF_40):
```sql
-- Start a run
SELECT * FROM rag.start_run_for_thread(
  client_id, project_id, 'telegram', chat_id,
  'chat', 'Telegram chat ...', '{}', '{}'
);

-- Log a message
SELECT rag.log_event(
  client_id, project_id, conversation_id, run_id,
  'user', from_id, 'message', NULL,
  jsonb_build_object('role','user', 'text', msg, 'channel','telegram')
);

-- Load history
SELECT ... FROM rag.events
WHERE conversation_id = ... AND event_type = 'message'
ORDER BY ts DESC LIMIT 20;

-- Finish
SELECT rag.finish_run(run_id, 'success', 'Chat completed', '{}');
```

---

## Payload JSONB Conventions

All event data is stored in `rag.events.payload`. Common keys:

| Key | Type | Used In | Description |
|-----|------|---------|-------------|
| `role` | text | messages | `'user'` or `'assistant'` |
| `text` | text | messages | The message content |
| `channel` | text | all | `'telegram'` |
| `chat_id` | text | telegram events | Telegram chat ID |
| `decision` | text | approvals | `'approved'` or `'rejected'` |
| `telegram_message_id` | text | action_draft_sent | Links callback to draft |
| `type` | text | tool_call | Action category |
| `mode` | text | tool_call/result | `'fetch'`, `'search'`, `'browser'` |
| `model` | text | tool_call/result | `'openclaw:main'` |
| `status` | text | tool_result | `'success'`, `'sent'` |
| `artifact_id` | text | tool_result | Reference to rag.artifacts.id |
