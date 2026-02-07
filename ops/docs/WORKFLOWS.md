# n8n Workflow Templates

All workflow JSON files are in `ops/n8n/`.

## Live Workflows

These are actively running in production.

| File | Trigger | Purpose | DB Functions Used |
|------|---------|---------|-------------------|
| `WF_40_Jackie_Telegram_Assistant.json` | Telegram Trigger | Main Jackie AI assistant: voice/text → history → AI agent → ACTION_DRAFT or reply | `start_run_for_thread`, `log_event` (9-arg) |
| `WF_41_Jackie_Action_Subflow.json` | Telegram callback | Approved action executor: callback → parse → OpenClaw `/v1/responses` → artifact + reply | `start_run_for_thread`, `log_event`, `finish_run`, `INSERT rag.artifacts` |

## Active Templates

Ready to import and use.

| File | Trigger | Purpose | DB Functions Used |
|------|---------|---------|-------------------|
| `memory_workflows.json` | `/webhook/memory-upsert`, `/webhook/memory-search` | Memory API: embed + store/search in `rag.chunks` | `search_chunks`, `INSERT rag.chunks` |
| `spec_kit_workflow.json` | `/webhook/janagi/spec/flow` | Spec-Kit: REFINE requirements → EXECUTE build | – (shell commands) |
| `WF_10_Turbo_OpenClaw_Run.json` | `/webhook/turbo/openclaw/run` | Direct OpenClaw `/v1/responses` call | – |
| `WF_11_Turbo_OpenClaw_UI_Operator.json` | `/webhook/turbo/openclaw/ui-operator` | OpenClaw PLAN/APPLY/VERIFY pattern | – |
| `WF_12_Turbo_OpenClaw_Run_RawBody.json` | `/webhook/turbo/openclaw/run-raw` | OpenClaw call with rawBody pattern | – |
| `WF_20_Builder_Create_Workflow_via_API.json` | `/webhook/builder/workflow/create` | Auto-create n8n workflows via REST API | – |
| `WF_30_SpecKit_Full_Build_Parallel.json` | `/webhook/janagi/spec-build` | Full Spec Kit build: parallel Gemini + Copilot → winner → PR | – (shell commands) |

## Legacy Workflows (Superseded)

These use old function signatures or deprecated APIs. Kept for reference only.

| File | Status | Issue |
|------|--------|-------|
| `main_chat_orchestrator.json` | ⚠️ Legacy | Uses old `rag.start_run()` (4-arg), old `rag.log_event()` (5-arg), references dead `chat.messages` table. **Superseded by WF_40.** |
| `WF_01_Ingest_Message.json` | ⚠️ Legacy | Calls Mistral embeddings API directly. Use `memory_workflows.json` (OpenAI) instead. |
| `WF_02_Hunter_Run.json` | ⚠️ Legacy | Calls `clawd_worker:8090/tasks/hunt` (service commented out in docker-compose). |
| `WF_03_Analyst_Draft_and_Telegram_Approval.json` | ⚠️ Legacy | Uses Mistral model + old n8n-langchain PGVector node. |
| `WF_04_Executor_On_Approve.json` | ⚠️ Legacy | 2-node skeleton. **Superseded by WF_41.** |

## Reusable Snippets

- `snippets/TELEGRAM_NORMALIZATION.js` — Normalize Telegram message/callback_query/channel_post
- `snippets/TELEGRAM_PAYLOAD_EXTRACTOR.js` — Extract hidden JSON from `[ACTION_DRAFT]` markers
- `sql/RAG_POSTGRES_NODES.sql` — Copy-paste SQL for all Postgres nodes (matches live function signatures)

## Import Instructions

1. In n8n: **Workflows → Import from File**
2. Create required credentials:
   - **Postgres** — host: `postgres` (docker-compose) or `janagi-db` (Coolify), port: 5432, db: `janagi`, user: `janagi`
   - **Telegram** — Bot token
   - **OpenAI** — API key (for embeddings + LLM)
   - **HTTP Header Auth** — OpenClaw gateway token (for Turbo workflows)
3. Activate workflows

## Related Docs

- [DB_SCHEMA.md](DB_SCHEMA.md) — Database tables, functions, indexes
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design
- [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) — Memory/RAG details
- [ACTION_DRAFT_PROTOCOL.md](ACTION_DRAFT_PROTOCOL.md) — Approval gate pattern
- [OPENCLAW_TURBO.md](OPENCLAW_TURBO.md) — OpenClaw integration
- [SPECKIT_OPENCLAW_CLI.md](SPECKIT_OPENCLAW_CLI.md) — Spec-Kit spec-driven development flow
- [N8N_WORKFLOW_BUILDER.md](N8N_WORKFLOW_BUILDER.md) — OpenClaw generates n8n workflows via API
- [MINDSDB_ANALYTICS.md](MINDSDB_ANALYTICS.md) — MindsDB batch analytics
