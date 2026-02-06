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
- DB name is `n8n`, not `janagi`.
- Postgres hostname in Docker is `postgresql`, not `postgres`.
