# OpenClaw Turbo (HTTP) for n8n

OpenClaw Gateway can expose 3 useful HTTP surfaces:

- `POST /v1/responses` (OpenResponses-compatible) – **recommended** for “run an agent to do a task”
- `POST /v1/chat/completions` (OpenAI-compatible) – optional
- `POST /tools/invoke` – invoke **one tool** directly (debug / low-level ops)

This repo is opinionated:

✅ **Use `/v1/responses`** for most automation (web, browsing, UI operator, multi-step tasks).
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
- Use `user` for stable session routing.
- If you omit `x-openclaw-agent-id`, routing still works via `model` (`openclaw:<agentId>`).

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
