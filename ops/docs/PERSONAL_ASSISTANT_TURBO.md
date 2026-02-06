# Personal Assistant + Turbo (OpenClaw)

Goal: Your **main assistant** lives in n8n (Telegram voice/text → LLM → tools).
OpenClaw is the **Turbo**: it executes tasks that require *eyes + hands* (browser/UI, multi-step ops), and can also **verify** results.

## Design principles

1. **Main assistant stays deterministic**
   - It decides *what* should happen.
   - It records each decision as an event in your domain DB (`rag.events`).

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
- if UI task needed → call **OpenClaw Turbo** (HTTP Request node)

### Strongly recommended: Action Draft + Approval Gate

For anything that triggers OpenClaw (UI actions, browsing, scraping), avoid letting the LLM call the HTTP node directly.

Instead:
1) LLM outputs `[ACTION_DRAFT]` + JSON payload
2) Validate JSON + policy (allowlist of targets/actions)
3) Ask for approval (Telegram buttons)
4) Only then call OpenClaw

See: [ops/docs/ACTION_DRAFT_PROTOCOL.md](ops/docs/ACTION_DRAFT_PROTOCOL.md)

### What to store in DB
- `rag.events`: every action (messages, tool calls/results, approvals, errors)
- `rag.artifacts`: request/response payloads for each Turbo run (OpenClaw)

See also: [ops/docs/OPENCLAW_TURBO.md](ops/docs/OPENCLAW_TURBO.md)

## Practical notes

- If you see JSON parsing issues in n8n HTTP nodes, use the `JSON.stringify(...)` body pattern (template: [ops/n8n/workflows/WF_12_Turbo_OpenClaw_Run_RawBody.json](ops/n8n/workflows/WF_12_Turbo_OpenClaw_Run_RawBody.json)).
- For Telegram approval flows, wrap machine payloads between markers (see Action Draft protocol).
