# Personal Assistant + Turbo (OpenClaw)

Goal: Your **main assistant** (Jackie) lives in n8n workflows (Telegram voice/text → routing → response).
n8n is the **integrator/curator** — a [fair-code workflow automation platform](https://github.com/n8n-io/n8n)\nwith native AI capabilities (LangChain-based AI agents, 400+ integrations).\nIt manages state, gates, and routing.
[OpenClaw](https://docs.openclaw.ai/) is the **AI agent gateway** — it wraps
LLMs (Anthropic Claude, etc.) and adds agent tools.
**Jackie** is the agent persona configured in OpenClaw.
All systems share the same memory (`rag.*` schema in PostgreSQL).
- **🧠 Brain**: LLM (via OpenClaw) — reasoning, decisions, conversation with memory
- **👁️ Eyes**: browse websites, scrape content, read social media, monitor competitors
- **🤲 Hands**: build software projects using [Spec Kit](https://github.com/github/spec-kit) (spec-driven development — ask user what's needed, lock specs, delegate to CLI tools with correct instructions), write n8n workflows, execute approved actions

## Design principles

1. **n8n integrates, OpenClaw thinks**
   - n8n routes requests to the right sub-workflow.
   - OpenClaw decides *what* should happen and *does* it.
   - Every decision is recorded as an event in your domain DB (`rag.events`).

2. **Turbo is opt-in (tool call)**
   - The LLM can request Turbo, but you keep a policy gate:
     - allowlist of target domains (e.g., `http://n8n:5678/*`)
     - allowlist of actions (create workflow, update node config, export JSON)
     - approval gate for risky actions (delete, rotate credentials, publish)

3. **Two-phase commit for UI changes**
   - **Plan**: Turbo returns a step-by-step plan and expected end state.
   - **Apply**: Turbo performs the steps.
   - **Verify**: Turbo re-opens the UI and confirms end state + exports evidence.

## Recommended flow (n8n)

Telegram Trigger → (voice?) Transcribe → AI Agent
→ Router:
- if LLM can answer directly → reply
- if tool needed → call tool (Gmail, Calendar, DB…)
- if web task needed → call **WF_48** (Web Interface) → OpenClaw
- if project build → call **WF_49** (Spec Kit Interface) → OpenClaw
- if workflow needed → call **WF_20** (Workflow Builder)

Router note (WF_42): when using the classifier/dispatcher path, categories map to MEETING→WF_43, TASK→WF_44, EMAIL→WF_45, CHAT→WF_46, WEB→WF_48, DEV→WF_49, UNKNOWN→WF_47. WF_42 sends an ACK first, waits for the subflow result, logs, then replies.

### Strongly recommended: Action Draft + Approval Gate

For anything that triggers OpenClaw (web browsing, scraping, social media,
project builds, workflow creation), avoid letting the LLM call the HTTP node directly.

Instead:
1) LLM outputs `[ACTION_DRAFT]` + JSON payload
2) Validate JSON + policy (allowlist of targets/actions)
3) Ask for approval (Telegram buttons)
4) Only then call OpenClaw

See: [ops/docs/ACTION_DRAFT_PROTOCOL.md](ops/docs/ACTION_DRAFT_PROTOCOL.md)
If you keep WF_42 in front of Turbo calls, add an approval step in subflows that perform mutating actions (calendar/task/email/web/spec build/UI edits) when Action Draft is not upstream.

### What to store in DB
- `rag.events`: every action (messages, tool calls/results, approvals, errors)
- `rag.artifacts`: request/response payloads for each Turbo run (OpenClaw)

See also: [ops/docs/OPENCLAW_TURBO.md](ops/docs/OPENCLAW_TURBO.md)

## Practical notes

- If you see JSON parsing issues in n8n HTTP nodes, use the `JSON.stringify(...)` body pattern (template: [ops/n8n/workflows/WF_12_Turbo_OpenClaw_Run_RawBody.json](ops/n8n/workflows/WF_12_Turbo_OpenClaw_Run_RawBody.json)).
- For Telegram approval flows, wrap machine payloads between markers (see Action Draft protocol).
