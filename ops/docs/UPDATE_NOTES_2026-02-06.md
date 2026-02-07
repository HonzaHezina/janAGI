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

---

## Architecture Vision Alignment (2026-02-07, batch 2)

Aligned all documentation to the correct system paradigm:

### Core Paradigm
- **n8n** = Integrator / Curator — routes workflows, manages state, enforces safety gates. Does NOT think or decide.
- **OpenClaw / Jackie** = Brain + Hands + Eyes — LLM reasoning, web browsing/scraping/social media, Spec Kit project builds, n8n workflow creation.
- **MindsDB** = Analytics Department — PRIMARY: external business intelligence (multi-source data aggregation, lead scoring, competitor analysis). SECONDARY: internal operational analytics.
- **PostgreSQL** = Memory — all data in `rag.*`, analytics results in `analytics.*`.

### Files Updated
- `ARCHITECTURE.md` — Vision, components, data flow diagrams, agent architecture pattern all rewritten for integrator/brain paradigm
- `README.md` — Opening tagline, "What It Does" section (added web intelligence + MindsDB external analytics), architecture mermaid diagram (added MindsDB + web flows), tech stack table, roadmap
- `PERSONAL_ASSISTANT_TURBO.md` — Reframed from "Turbo" to "brain+hands+eyes"
- `OPENCLAW_TURBO.md` — Opening section updated
- `SPECKIT_OPENCLAW_CLI.md` — n8n role renamed from "Orchestrator" to "Integrator"
- `N8N_WORKFLOW_BUILDER.md` — Architecture description updated
- `N8N_UI_OPERATOR.md` — Opening section updated
- `MINDSDB_ANALYTICS.md` — Added external BI as primary purpose, external data sources table, updated architecture diagram with OpenClaw data pipeline
- `0001-hybrid-ops-analytics.md` (ADR) — Updated to reflect integrator paradigm + MindsDB external BI focus
- `MEMORY_ARCHITECTURE.md` — Access patterns labeled with roles (Integrator/Brain)
- `OPENCLAW_DISPATCHER_CONTRACT.md` — Fixed `rag.start_run()` → `rag.start_run_for_thread()`

---

## Spec Kit Description Fix (2026-02-07, batch 3)

Corrected Spec Kit descriptions across all docs. Previously described as
"scaffolding/bootstrap," now correctly framed as GitHub's open-source
**spec-driven development toolkit** that:
- Helps OpenClaw ask the user the right questions (mapped to Spec Kit concepts)
- Ensures CLI tools receive complete, structured specifications from the start
- Prevents vibe coding through structured refinement (constitution → spec → plan → tasks → implement)

### Files Updated

- `ARCHITECTURE.md` — Vision, dispatcher, hands section, agent architecture ASCII all updated
- `README.md` — "Spec-Driven Project Builder" (was "Spec-Kit Dispatcher"), tech stack, roadmap
- `SPECKIT_OPENCLAW_CLI.md` — Complete opening rewrite with proper Spec Kit explanation + GitHub link
- `OPENCLAW_DISPATCHER_CONTRACT.md` — Opening, "Why" section, REFINE objective rewritten
- `CLI_IMPLEMENTER_CONTRACT.md` — Title, key principle, "Why CLI Tools" section rewritten
- `PERSONAL_ASSISTANT_TURBO.md` — Hands description and router updated
- `WORKFLOWS.md` — Related docs link text updated

---

## OpenClaw/Jackie Relationship Fix (2026-02-07, batch 4)

Fixed the relationship between OpenClaw and Jackie across all docs:
- **OpenClaw** = LLM model powering AI agents in n8n (brain + tools for web/scraping/execution)
- **Jackie** = AI agent persona that lives in n8n workflows, uses OpenClaw as its LLM
- **Shared memory**: all systems (n8n, OpenClaw, MindsDB) share the same `rag.*` schema

### Files Updated

- `README.md` — Intro, blockquote, mermaid diagram, tech stack table
- `ARCHITECTURE.md` — Vision, OpenClaw section, agent pattern ASCII art, closing
- `OPENCLAW_TURBO.md` — Opening paragraph
- `PERSONAL_ASSISTANT_TURBO.md` — Goal section description
- `N8N_UI_OPERATOR.md` — Opening line
- `MEMORY_ARCHITECTURE.md` — Overview (shared memory), access patterns, mermaid participant

---

## OpenClaw = AI Agent Gateway (2026-02-07, batch 5)

Based on [OpenClaw docs](https://docs.openclaw.ai/), corrected what OpenClaw
actually is:

- **OpenClaw** = self-hosted AI agent gateway (wraps LLM providers like
  Anthropic Claude and adds agent capabilities: tools, sessions, skills,
  multi-agent routing)
- **Jackie** = agent persona configured in OpenClaw (own workspace, identity,
  session store)
- n8n calls OpenClaw via `/v1/responses` HTTP API as the brain for its
  AI Agent workflows
- NOT "the LLM model" — it's a gateway layer on top of LLMs

### Files Updated

- `README.md` — Intro blockquote, mermaid, tech stack table
- `ARCHITECTURE.md` — Vision, OpenClaw section, agent pattern ASCII, closing
- `OPENCLAW_TURBO.md` — Opening paragraph
- `PERSONAL_ASSISTANT_TURBO.md` — Goal section
- `N8N_UI_OPERATOR.md` — Opening line
- `MEMORY_ARCHITECTURE.md` — Access patterns, mermaid participant

---

## Batch 6 — n8n & MindsDB Identity Fix (per GitHub repos)

### Problem
- **n8n** was described generically as "workflow orchestration, routing".
  Actually: fair-code workflow automation platform with native AI capabilities
  (LangChain-based AI agents, 400+ integrations, JS/Python code support).
- **MindsDB** was described as "Analytics Dept." / "ML Models / Batch Jobs".
  Actually: Federated Query Engine for AI — connects hundreds of data sources,
  unifies them via knowledge bases and views (no-ETL), responds via built-in
  agents and MCP server. Tagline: "The only MCP Server you'll ever need."

### Key Corrections
- **n8n**: Added fair-code license, native AI capabilities (LangChain), 400+
  integrations, JS/Python code support to all descriptions. Role as
  "integrator/curator" in janAGI preserved (that's our usage).
- **MindsDB**: "Analytics Dept." → "Federated Query Engine for AI".
  Core philosophy: Connect → Unify → Respond. Built-in MCP server + agents.
  In janAGI: data federation + analytics (not just batch ML jobs).

### Files Updated
- `README.md` — Tech stack, mermaid diagram, roadmap
- `ARCHITECTURE.md` — Vision, n8n section, MindsDB section, ASCII art, sequence diagram
- `MINDSDB_ANALYTICS.md` — Title, opening, core capabilities, data pipeline
- `OPENCLAW_TURBO.md` — n8n reference
- `PERSONAL_ASSISTANT_TURBO.md` — n8n description
- `MEMORY_ARCHITECTURE.md` — MindsDB access pattern
- `DB_SCHEMA.md` — MindsDB role description
- `WORKFLOWS.md` — MindsDB doc link