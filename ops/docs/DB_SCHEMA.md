# DB_SCHEMA

Current canonical schema: `rag.*` (see [ops/infra/postgres/init/020_rag_schema.sql](ops/infra/postgres/init/020_rag_schema.sql)).

## Extensions
- `pgcrypto` (UUID)
- `vector` (pgvector)
- optional: `pg_trgm`, `unaccent`

## rag.* (single source of truth)

### rag.clients / rag.projects
- stable keys you can reference from n8n (e.g. `client_key='janagi'`, `project_key='main'`)

### rag.conversations
- one row per thread (Telegram chat / channel thread / external thread)
- dedupe: UNIQUE `(client_id, project_id, channel, thread_key)`

### rag.runs
- one row per orchestrated run (chat turn, tool execution, web subworkflow)

### rag.events
- append-only event log (messages, tool calls/results, errors, approvals)
- ordering per conversation via `(conversation_id, event_no)`

### rag.artifacts
- store big payloads (OpenClaw request/response bodies, diffs, logs)

### rag.documents / rag.chunks
- retrieval index; can point back to sources and carry metadata

## Compatibility: janagi_documents

We keep `janagi_documents` for easy integration with existing n8n/PGVector patterns.
Treat it as a convenience vector store; the audit log is still `rag.events`.

