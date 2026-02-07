# n8n workflows

Import these JSON files in n8n:
- n8n → Workflows → Import from file

## Workflow Index

### Live Workflows

| File | Purpose |
|------|---------|
| `WF_40_Jackie_Telegram_Assistant.json` | **LIVE** — Main Jackie AI assistant (Telegram → AI → ACTION_DRAFT / reply) |
| `WF_41_Jackie_Action_Subflow.json` | **LIVE** — Approved action executor (callback → OpenClaw → artifact → reply) |

### Router + domain branches (new)

| File | Purpose | Status |
|------|---------|--------|
| `WF_42_Jackie_Classifier.json` | Telegram classifier/dispatcher with ACK; routes MEETING/TASK/EMAIL/CHAT/WEB/DEV/UNKNOWN to subflows | Import + set workflowIds |
| `WF_43_Jackie_Meeting.json` | Meeting/calendar handling | Template |
| `WF_44_Jackie_Task.json` | Task/reminder handling | Template |
| `WF_45_Jackie_Email.json` | Gmail search/read/send | Template |
| `WF_46_Jackie_Chat.json` | Chat/LLM + RAG | Template |
| `WF_47_Jackie_Clarify.json` | Clarifying question when uncertain | Template |
| `WF_48_Jackie_Web.json` | Web browse/search via OpenClaw | Template |
| `WF_49_Jackie_SpecKit.json` | Spec Kit webhook trigger for DEV intents | Template |

### Active Templates

| File | Purpose |
|------|---------|
| `WF_10_Turbo_OpenClaw_Run.json` | Direct OpenClaw API call |
| `WF_11_Turbo_OpenClaw_UI_Operator.json` | OpenClaw PLAN/APPLY/VERIFY pattern |
| `WF_12_Turbo_OpenClaw_Run_RawBody.json` | OpenClaw call with raw JSON body |
| `WF_20_Builder_Create_Workflow_via_API.json` | Auto-create n8n workflows via REST API |
| `WF_30_SpecKit_Full_Build_Parallel.json` | Full Spec Kit parallel build |

### Legacy (Superseded)

| File | Status | Superseded By |
|------|--------|---------------|
| `WF_01_Ingest_Message.json` | ⚠️ Skeleton | `memory_workflows.json` |
| `WF_02_Hunter_Run.json` | ⚠️ Skeleton (old "Hunter" concept) | OpenClaw web browsing via WF_41 |
| `WF_03_Analyst_Draft_and_Telegram_Approval.json` | ⚠️ Skeleton (old "Analyst" concept) | WF_40 AI Jackie agent |
| `WF_04_Executor_On_Approve.json` | ⚠️ Skeleton | WF_41 |

## WF_40 + WF_41: Jackie Assistant Pair

These two workflows work together as the **live Telegram bot**:

1. **WF_40** (main flow): Receives Telegram messages (text or voice), transcribes voice via Gemini, loads conversation history from `rag.events`, formats it, and passes to the AI Jackie agent. Jackie decides:
   - **ACTION needed** → outputs `[ACTION_DRAFT]` + JSON → logged to DB → sent to Telegram with "✅ Schválit" button
   - **No action** → plain Czech response → logged to DB → sent to Telegram

2. **WF_41** (subflow): Triggered by Telegram callback (user clicks "✅ Schválit"). Parses the ACTION_DRAFT JSON, creates a sub-run in DB, calls OpenClaw `/v1/responses`, stores the result as an artifact, logs everything, and replies to Telegram.

### ACTION_DRAFT JSON Format

WF_40's AI agent outputs one of these JSON types:

```json
{"type":"web","target":"openclaw","payload":{"model":"openclaw:main","mode":"fetch|search|browser","input":"<EN prompt>"}}
{"type":"cli","target":"spec-kit","payload":{"repo":"<url>","branch":"<name>","mode":"spec|implement|test|repair|compare","input":"<EN prompt>","tools":[...]}}
```

### Required Credentials

- **Telegram** — Bot token (triggers + replies)
- **Postgres** — `rag.*` schema access
- **OpenAI** — LLM model (via OpenRouter or direct)
- **Bearer Auth** — OpenClaw gateway token
- **Google Gemini** — Voice transcription (optional)

See docs:
- [ops/docs/WORKFLOWS.md](../docs/WORKFLOWS.md)
- [ops/docs/OPENCLAW_TURBO.md](../docs/OPENCLAW_TURBO.md)
- [ops/docs/ACTION_DRAFT_PROTOCOL.md](../docs/ACTION_DRAFT_PROTOCOL.md)
- [ops/docs/OPENCLAW_DISPATCHER_CONTRACT.md](../docs/OPENCLAW_DISPATCHER_CONTRACT.md)

## WF_42 routing quick reference

- Categories: MEETING→WF_43, TASK→WF_44, EMAIL→WF_45, CHAT→WF_46, WEB→WF_48, DEV→WF_49, UNKNOWN→WF_47.
- After import: set each Execute Workflow node in WF_42 to the correct workflowId.
- Inputs passed: `text`, `chat_id`, `conversation_id`, `run_id`. Return `{ output: "..." }` from subflows for reply logging.
