# Database Schema

Canonical schema definition: [`ops/infra/postgres/init/020_rag_schema.sql`](../infra/postgres/init/020_rag_schema.sql)

## Extensions
- `vector` (pgvector) — Vector similarity search
- `pgcrypto` — UUID generation (`gen_random_uuid()`)
- `pg_trgm` — Trigram similarity (fuzzy text search)
- `unaccent` — Diacritics removal

## Schema: `rag.*`

### Entity Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `rag.clients` | Tenants | `client_key` (unique) |
| `rag.projects` | Workspaces per client | `project_key` (unique per client) |
| `rag.conversations` | Chat threads | `channel`, `thread_key` |
| `rag.runs` | Execution sessions | `run_type`, `status`, `started_at` |
| `rag.events` | Append-only audit log | `event_type`, `actor_role`, `content`, `payload` |
| `rag.artifacts` | Generated outputs | `key`, `type`, `content`, `data` |

### RAG Pipeline Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `rag.sources` | Origin of data | `type` (url/file/telegram), `uri` |
| `rag.documents` | Parent content units | `source_id`, `hash` |
| `rag.chunks` | Embedded text chunks | `content`, `embedding` (vector 1536), `chunk_index` |

### Indexes
- `chunks_embedding_hnsw` — HNSW index on `rag.chunks.embedding` using `vector_cosine_ops`

## Stored Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `rag.start_run()` | `(client_key, project_key, conversation_key, run_type, metadata)` → `uuid` | Auto-creates client/project/conversation if missing, starts a new run |
| `rag.log_event()` | `(run_id, event_type, actor_role, content, payload)` → `uuid` | Logs to `rag.events`, updates conversation `last_event_at` |
| `rag.finish_run()` | `(run_id, status)` → `void` | Marks run as completed/failed |
| `rag.search_chunks()` | `(project_key, embedding, threshold, count)` → `table` | Semantic search: returns `id`, `content`, `similarity`, `metadata` |

## Schema: `analytics.*` (Optional)

| Table | Purpose |
|-------|---------|
| `analytics.trends_daily` | Daily topic/keyword aggregation |
| `analytics.lead_scores` | Batch scoring results |

See [`ops/infra/postgres/init/030_analytics.sql`](../infra/postgres/init/030_analytics.sql)

## Usage from n8n

All SQL templates for n8n Postgres nodes are in [`ops/n8n/sql/RAG_POSTGRES_NODES.sql`](../n8n/sql/RAG_POSTGRES_NODES.sql).

Common pattern:
```sql
-- Start a run
SELECT rag.start_run('janagi', 'janagi', $1, 'chat');

-- Log a message
SELECT rag.log_event($1, 'message', 'user', $2, $3::jsonb);

-- Search memory
SELECT * FROM rag.search_chunks('janagi', $1::vector, 0.5, 5);

-- Finish
SELECT rag.finish_run($1, 'completed');
```
