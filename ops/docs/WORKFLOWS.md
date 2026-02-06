# n8n workflow templates

Templates live in [ops/n8n/workflows](ops/n8n/workflows/).

## Included templates

Core domain workflows:
- `WF_01_Ingest_Message.json`
- `WF_02_Hunter_Run.json`
- `WF_03_Analyst_Draft_and_Telegram_Approval.json`
- `WF_04_Executor_On_Approve.json`

Turbo / OpenClaw:
- `WF_10_Turbo_OpenClaw_Run.json` *(simple `/v1/responses` runner)*
- `WF_11_Turbo_OpenClaw_UI_Operator.json` *(PLAN/APPLY/VERIFY pattern skeleton)*
- `WF_12_Turbo_OpenClaw_Run_RawBody.json` *(same as WF_10 but uses `JSON.stringify` — most robust)*

Workflow Builder (API-first):
- `WF_20_Builder_Create_Workflow_via_API.json` *(OpenClaw generates a workflow export JSON → n8n creates it via API)*

## Import
1) n8n → Workflows → Import from file
2) Create credentials (Postgres, Telegram, OpenClaw token, n8n API key, etc.)
3) Replace env placeholders with your real values (Coolify env/secrets)

## Notes

Recommended pattern:
- Main assistant in n8n
- OpenClaw is “Turbo” for browsing/UI/multi-step tasks
- Use **Action Draft** + approval gate for anything risky

For wiring:
- [ops/docs/PERSONAL_ASSISTANT_TURBO.md](ops/docs/PERSONAL_ASSISTANT_TURBO.md)
- [ops/docs/OPENCLAW_TURBO.md](ops/docs/OPENCLAW_TURBO.md)
- [ops/docs/N8N_WORKFLOW_BUILDER.md](ops/docs/N8N_WORKFLOW_BUILDER.md)
- [ops/docs/ACTION_DRAFT_PROTOCOL.md](ops/docs/ACTION_DRAFT_PROTOCOL.md)

Spec Kit automation (OpenClaw gatekeeper + CLI implementers):
- [ops/docs/SPECKIT_OPENCLAW_CLI.md](ops/docs/SPECKIT_OPENCLAW_CLI.md)
