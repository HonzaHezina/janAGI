# n8n workflows

Import these JSON files in n8n:
- n8n → Workflows → Import from file

## Workflow Index

| File | Purpose |
|------|---------|
| `WF_01_Ingest_Message.json` | Ingest & embed a message into RAG |
| `WF_02_Hunter_Run.json` | Scheduled data collection |
| `WF_03_Analyst_Draft_and_Telegram_Approval.json` | Draft + Telegram approval gate |
| `WF_04_Executor_On_Approve.json` | Execute on Telegram callback approval |
| `WF_10_Turbo_OpenClaw_Run.json` | Direct OpenClaw API call |
| `WF_11_Turbo_OpenClaw_UI_Operator.json` | OpenClaw PLAN/APPLY/VERIFY pattern |
| `WF_12_Turbo_OpenClaw_Run_RawBody.json` | OpenClaw call with raw JSON body |
| `WF_20_Builder_Create_Workflow_via_API.json` | Auto-create n8n workflows via REST API |
| `WF_30_SpecKit_Full_Build_Parallel.json` | Full Spec Kit parallel build |
| `WF_40_Jackie_Telegram_Assistant.json` | Main Jackie AI assistant (Telegram → AI → ACTION_DRAFT / reply) |
| `WF_41_Jackie_Action_Subflow.json` | Approved action executor (callback → OpenClaw → artifact → reply) |

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
