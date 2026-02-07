# OpenClaw Turbo (HTTP) for n8n

[OpenClaw](https://docs.openclaw.ai/) is a **self-hosted AI agent gateway**.
It wraps LLM providers (Anthropic Claude, etc.) and adds agent capabilities:
tools (web browsing, scraping, code execution), sessions, skills, and
multi-agent routing. **Jackie** is the agent persona configured in OpenClaw.
n8n (integrator) calls OpenClaw via HTTP. All systems share the same memory
(`rag.*` schema in PostgreSQL).

OpenClaw Gateway exposes 3 HTTP surfaces:

- `POST /v1/responses` (OpenResponses-compatible) – **recommended** for "run an agent to do a task"
- `POST /v1/chat/completions` (OpenAI-compatible) – optional
- `POST /tools/invoke` – invoke **one tool** directly (debug / low-level ops)

This repo is opinionated:

✅ **Use `/v1/responses`** for most automation (web browsing, scraping, social media, UI operator, project builds, multi-step tasks).
🧰 Use `/tools/invoke` only when you *really* want a single tool call (and you know the tool name is allowed).

---

## 0) Docker/Coolify note (important)

If n8n runs in Docker (Coolify), **do not** call OpenClaw via `http://127.0.0.1:18789` from inside n8n.
That points to the *n8n container itself*.

Use internal DNS on the shared network instead:

- `OPENCLAW_BASE_URL=http://openclaw:18789` (recommended)

---

## 1) Enable HTTP endpoints (fixes 405 Method Not Allowed)

OpenClaw disables `/v1/responses` and `/v1/chat/completions` by default.

Enable only what you need (safer):
- [ops/infra/openclaw/openclaw.json.patch.internal.example](ops/infra/openclaw/openclaw.json.patch.internal.example)

Then restart the OpenClaw service.

---

## 2) Internal-only wiring (Coolify network)

Recommended env vars (Coolify secrets):

- `OPENCLAW_BASE_URL` *(internal only; default `http://openclaw:18789`)*
- `OPENCLAW_GATEWAY_TOKEN`
- `N8N_BASE_URL` *(default `http://n8n:5678`)*
- `N8N_API_KEY` *(optional; only if you use the Workflow Builder pattern)*

---

## 3) n8n → OpenClaw (`/v1/responses`) call shape

### Endpoint
`POST ${OPENCLAW_BASE_URL}/v1/responses`

### Headers
- `Authorization: Bearer ${OPENCLAW_GATEWAY_TOKEN}`
- `Content-Type: application/json`
- Optional: `x-openclaw-agent-id: main`

### Body (minimal)
```json
{
  "model": "openclaw:main",
  "user": "n8n:<stable_session_key>",
  "input": "Your task here…"
}
```

Notes:
- Use `user` for stable session routing. This is a **killer feature**: OpenClaw derives a stable session key from `user`, so multi-step tasks maintain continuity. Use a predictable format like `telegram:<chat_id>` or `n8n:<workflow_id>`.
- If you omit `x-openclaw-agent-id`, routing still works via `model` (`openclaw:<agentId>`).
- You can target specific agents per task: `"model": "openclaw:ui-operator"` for UI tasks, `"model": "openclaw:main"` for general reasoning.

---

## 4) Recommended n8n HTTP Request body pattern

In n8n, the most reliable way (avoids “literal moustaches” / editor quirks) is:

- Content-Type: JSON
- JSON parameters: **true**
- Body (Expression): `={{JSON.stringify({...})}}`

Example (matches template [ops/n8n/workflows/WF_12_Turbo_OpenClaw_Run_RawBody.json](ops/n8n/workflows/WF_12_Turbo_OpenClaw_Run_RawBody.json)):

```js
={{JSON.stringify({
  model: "openclaw:main",
  user: $json.user_key,
  input: $json.prompt
})}}
```

---

## 5) `/tools/invoke` (when you really need a tool)

### Endpoint
`POST ${OPENCLAW_BASE_URL}/tools/invoke`

### Body (example)
```json
{
  "tool": "sessions_list",
  "action": "json",
  "args": {},
  "sessionKey": "main",
  "dryRun": false
}
```

Important: **Do not send a `/tools/invoke` body to `/v1/responses`** (or vice versa).
They are different protocols.

---

## 6) Common errors & fixes

### A) 405 “Method Not Allowed”
You hit an endpoint that is disabled.

✅ Fix: enable `/v1/responses` (section 1) and restart OpenClaw.

### B) 404 “Tool not available: <name>”
The tool exists conceptually, but is not allowed by current OpenClaw policy.

✅ Fix:
- verify tool list via `/tools/invoke` (if your policy allows listing)
- allowlist the tool for the agent/session you use

### C) 429 “status code (no body)”
Upstream provider rate limiting.

✅ Fix:
- retry/backoff in n8n
- reduce concurrency
- use smaller model for routing, big model only for execution

---

## 7) UI Operator Protocol (PLAN → APPLY → VERIFY)

When using OpenClaw to operate on UIs (n8n editor, MindsDB, dashboards, admin panels),
follow this three-phase protocol to avoid fragile automation:

### Phase 1: PLAN

OpenClaw analyzes the task and returns:
- Step-by-step actions it will perform
- How it will verify success
- What artifacts it will export as proof (workflow JSON, screenshot, etc.)

```json
{
  "model": "openclaw:main",
  "user": "n8n:ui-operator",
  "input": "Open n8n UI at http://n8n:5678. I need a new workflow that triggers on Telegram message, calls OpenClaw, and replies. First, tell me your PLAN: what steps you'll take, how you'll verify, and what you'll export. Do NOT make changes yet."
}
```

### Phase 2: APPLY

After reviewing the plan, trigger execution:

```json
{
  "model": "openclaw:main",
  "user": "n8n:ui-operator",
  "input": "Approved. Execute the plan now. Create the workflow in n8n. Report each step as you complete it."
}
```

### Phase 3: VERIFY

OpenClaw re-opens the UI and confirms the end-state:

```json
{
  "model": "openclaw:main",
  "user": "n8n:ui-operator",
  "input": "Verify the workflow was created correctly. Open n8n, check the workflow exists, nodes are connected, credentials are set. Export the workflow JSON as proof."
}
```

### n8n Integration Pattern

In n8n, wire it as a sub-workflow with a Telegram approval gate:

1. **PLAN call** → Parse response → Send plan summary to Telegram
2. User clicks "✅ Schválit" → Trigger APPLY
3. **APPLY call** → Parse response → Log result
4. **VERIFY call** → Parse response → Send verification + exported artifact to Telegram
5. User clicks "✅ Aktivovat" → Activate the workflow / deploy the change

See workflow templates:
- `WF_11_Turbo_OpenClaw_UI_Operator.json` — PLAN/APPLY/VERIFY pattern
- `WF_40_Jackie_Telegram_Assistant.json` — Main assistant with ACTION_DRAFT
- `WF_41_Jackie_Action_Subflow.json` — Approved action executor

---

## 8) OpenClaw as a Skill/Tool in the Main Assistant

OpenClaw can be attached to the main Jackie assistant in two ways:

### A) Direct HTTP Tool (in the AI Agent node)
Add an HTTP Request tool in n8n's AI Agent node that calls `/v1/responses`.
The agent decides autonomously when to invoke OpenClaw.

**Pro:** Simple, no extra workflow.
**Con:** No human approval gate for dangerous actions.

### B) Separate Sub-workflow via ACTION_DRAFT (recommended)
The main agent outputs `[ACTION_DRAFT]` + JSON when it needs OpenClaw.
n8n routes it to Telegram for approval, then executes via `WF_41`.

**Pro:** Human-in-the-loop, full audit trail.
**Con:** Extra latency (waiting for approval).

Choose **B** for production, **A** for development/testing.
