# n8n Workflow Templates

All workflow JSON files are in `ops/n8n/`.

## Core Workflows

| File | Webhook/Trigger | Purpose |
|------|----------------|---------|
| `main_chat_orchestrator.json` | Telegram Trigger | Main chat loop: Log → RAG Search → AI Agent → Parse Actions → Reply |
| `memory_workflows.json` | `/webhook/memory-upsert`, `/webhook/memory-search` | Memory API: embed + store/search in `rag.chunks` |
| `spec_kit_workflow.json` | `/webhook/janagi/spec/flow` | Spec-Kit: REFINE requirements → EXECUTE build |

## Supporting Templates (in `workflows/`)

| File | Purpose |
|------|---------|
| `WF_01_Ingest_Message.json` | Webhook → embed → store to `rag.chunks` |
| `WF_02_Hunter_Run.json` | Scheduled data collection via `clawd_worker` |
| `WF_03_Analyst_Draft_and_Telegram_Approval.json` | RAG retrieval → LLM draft → Telegram approval |
| `WF_04_Executor_On_Approve.json` | Execute on Telegram callback approval |
| `WF_10_Turbo_OpenClaw_Run.json` | Direct OpenClaw `/v1/responses` call |
| `WF_11_Turbo_OpenClaw_UI_Operator.json` | OpenClaw PLAN/APPLY/VERIFY pattern |
| `WF_12_Turbo_OpenClaw_Run_RawBody.json` | OpenClaw call with `JSON.stringify` body |
| `WF_20_Builder_Create_Workflow_via_API.json` | Auto-create n8n workflows via REST API (OpenClaw generates JSON → n8n applies) |
| `WF_30_SpecKit_Full_Build_Parallel.json` | Full Spec Kit build with parallel Gemini + Copilot implementers, winner selection, PR |
| `WF_40_Jackie_Telegram_Assistant.json` | Main Jackie AI assistant: Telegram → voice/text → history → AI agent → ACTION_DRAFT or reply |
| `WF_41_Jackie_Action_Subflow.json` | Approved action executor: Telegram callback → parse ACTION_DRAFT → OpenClaw `/v1/responses` → artifact + reply |

## Reusable Snippets

- `snippets/TELEGRAM_NORMALIZATION.js` — Normalize Telegram message/callback/channel_post
- `snippets/TELEGRAM_PAYLOAD_EXTRACTOR.js` — Extract hidden JSON from messages
- `sql/RAG_POSTGRES_NODES.sql` — Copy-paste SQL for all Postgres nodes

## Import Instructions

1. In n8n: **Workflows → Import from File**
2. Create required credentials:
   - **Postgres** — pointing to `postgresql:5432` (internal Docker DNS)
   - **Telegram** — Bot token
   - **OpenAI** — API key for embeddings
   - **HTTP Header Auth** — OpenClaw gateway token (if using Turbo)
3. Activate workflows

## Related Docs
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design
- [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) — Memory/RAG details
- [ACTION_DRAFT_PROTOCOL.md](ACTION_DRAFT_PROTOCOL.md) — Approval gate pattern
- [OPENCLAW_TURBO.md](OPENCLAW_TURBO.md) — OpenClaw integration
- [SPECKIT_OPENCLAW_CLI.md](SPECKIT_OPENCLAW_CLI.md) — Spec-Kit autopilot
- [N8N_WORKFLOW_BUILDER.md](N8N_WORKFLOW_BUILDER.md) — OpenClaw generates n8n workflows via API
- [MINDSDB_ANALYTICS.md](MINDSDB_ANALYTICS.md) — MindsDB batch analytics, lead scoring, trends
