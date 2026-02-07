# Update Notes — 2026-02-06

## Major Changes

### Repository Overhaul
- **README.md**: Complete rewrite. Now accurately describes janAGI as an autonomous personal AI agent (Jackie) with Telegram interface, RAG memory, and Spec-Kit dispatcher.
- **ARCHITECTURE.md**: Rewritten for Chat + Memory + Spec-Kit focus (removed old "lead scraping" framing).
- **CONTRIBUTING.md**: Updated with correct project context and structure.

### Database Schema (`020_rag_schema.sql`)
- Replaced old `janagi_documents` table with proper RAG pipeline: `rag.sources` → `rag.documents` → `rag.chunks`.
- Added `rag.artifacts` table for generated files/specs.
- Added PL/pgSQL stored functions: `start_run()`, `log_event()`, `finish_run()`, `search_chunks()`.
- Embedding dimension: 1536 (OpenAI text-embedding-3-small).
- Index: HNSW (`vector_cosine_ops`) instead of IVFFlat.

### n8n Workflows
- **New**: `main_chat_orchestrator.json` — Full Telegram chat loop with memory.
- **New**: `memory_workflows.json` — Webhook API for memory upsert/search.
- **Updated**: All workflows now use `rag.start_run()` / `rag.log_event()` instead of raw INSERT.
- **Updated**: Memory search uses `rag.search_chunks()` function.

### Documentation
- **DB_SCHEMA.md**: Rewritten to document all tables, functions, and usage patterns.
- **MEMORY_ARCHITECTURE.md**: Rewritten — unified `rag.*` schema, no separate `chat.*`.
- **RAG.md**: Updated with actual implementation (chunks, HNSW, 1536d).
- **WORKFLOWS.md**: Now indexes all workflow files including new core workflows.
- **COOLIFY_EXISTING_RESOURCES.md**: Updated with correct DB name (`n8n`), hostname (`postgresql`).
- **RUNBOOK_COOLIFY.md**: Practical deployment instructions with correct credentials.

### Infrastructure
- **.env.example**: DB name changed from `janagi` to `n8n` (matching actual Coolify setup). OpenAI replaces Mistral as primary embedding provider.
- Removed `021_chat_schema.sql` migration (not needed — building from scratch).

## Breaking Changes
- Table `rag.janagi_documents` no longer exists. Use `rag.chunks` instead.
- ~~DB name is `n8n`, not `janagi`.~~ **Corrected 2026-02-07:** DB name is `janagi` (business data). n8n can use the same DB (local dev) or a separate `n8n` DB (Coolify prod).
- ~~Postgres hostname in Docker is `postgresql`, not `postgres`.~~ **Corrected 2026-02-07:** docker-compose service = `postgres`. Coolify resource = `janagi-db`.

---

# Update Notes — 2026-02-07

## Database Schema Rewrite (`020_rag_schema.sql`)

Aligned the SQL schema with the **live n8n workflows** (WF_40, WF_41):

### Table Changes
- **`rag.events`**: `actor_role` → `actor_type`, `created_at` → `ts`, added `actor_name`, `name`, `conversation_id` columns. Removed `content` text column (all data in `payload` jsonb).
- **`rag.artifacts`**: `key` → `kind`, `type` removed, `content` → `content_text`, `data` → `metadata`, added `client_id`, `conversation_id`, `title` columns.
- **`rag.runs`**: added `summary` column.

### Function Changes
- **Added `rag.start_run_for_thread()`** — 8-arg version that resolves/creates conversations. This is what WF_40/WF_41 actually call.
- **`rag.log_event()`** — rewritten as 9-arg version (client_id, project_id, conversation_id, run_id, actor_type, actor_name, event_type, name, payload).
- **`rag.finish_run()`** — now accepts 4 args (run_id, status, summary, metadata).
- **`rag.search_chunks()`** — unchanged.

### Indexes Added
- `idx_events_conv_type_ts` — history loading (WF_40)
- `idx_events_type_name` — action draft lookup (WF_41)
- `idx_events_run_id` — run timeline
- `idx_runs_conversation` — conversation runs
- `idx_artifacts_run` — per-run artifacts

### Legacy Workflows Marked
- `main_chat_orchestrator.json` → superseded by WF_40 (used old function signatures)
- `WF_01` through `WF_04` → superseded by WF_40/WF_41 or use deprecated APIs

### Config Fixes
- `.env`: `N8N_HOST=0.0.0.0`, `MINDSDB_STORAGE_DIR`, added `OPENAI_API_KEY`
- `.env.example`: `POSTGRES_DB=janagi` (was incorrectly `n8n`)
- `docker-compose.yml`: default DB = `janagi`, not `n8n`

### Doc Deduplication
- `RAG.md` thinned to pointer → `DB_SCHEMA.md` + `MEMORY_ARCHITECTURE.md`
- `WORKFLOWS.md` rewritten with legacy marks
- Hostname references unified (`postgres` for compose, `janagi-db` for Coolify)
