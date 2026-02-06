# OpenClaw ↔ n8n “Workflow Builder” (API-first)

Goal: **Tell OpenClaw what workflow you want → it returns an importable n8n workflow JSON → n8n creates it via API**.

This is the most robust approach:
- versionable (JSON)
- testable (you can validate JSON before applying)
- not brittle like UI clicking

---

## Recommended architecture

**n8n remains the orchestrator**, OpenClaw is the “Turbo”:

1) n8n receives a user request (Telegram/Webhook/UI)
2) OpenClaw generates a **workflow spec** (n8n JSON: `name/nodes/connections/settings`)
3) n8n validates + applies it through the **n8n REST API**
4) n8n responds with the result (workflow id, name, activation status)

UI automation (“clicking in n8n”) stays as a fallback only.

---

## Preconditions (Coolify / self-hosted)

### 1) Internal DNS
Your services are on the same Coolify/docker network:

- n8n: `http://n8n:5678`
- OpenClaw gateway: `http://openclaw:18789`

### 2) n8n API key
Create an API key in n8n: **Settings → API → Create key**.

Store as a secret:
- `N8N_API_KEY`

Also set:
- `N8N_BASE_URL=http://n8n:5678`

### 3) OpenClaw `/v1/responses` enabled
If you see **405 Method Not Allowed**, enable endpoints (see [ops/docs/OPENCLAW_TURBO.md](ops/docs/OPENCLAW_TURBO.md)).

---

## Pattern A — n8n calls OpenClaw, then n8n calls its own API (recommended)

1) HTTP Request → OpenClaw `/v1/responses`
2) Code node → extract the JSON workflow
3) HTTP Request → `POST ${N8N_BASE_URL}/api/v1/workflows`

Template:
- [ops/n8n/workflows/WF_20_Builder_Create_Workflow_via_API.json](ops/n8n/workflows/WF_20_Builder_Create_Workflow_via_API.json)

---

## Pattern B — OpenClaw creates workflows directly (not recommended by default)

OpenClaw can call `http://n8n:5678/api/v1/...` too, but:
- you must store `N8N_API_KEY` in OpenClaw runtime
- you lose safety gates (validation/allowlist) that are easy in n8n

Use only with strict policy + approval gating.

---

## Security checklist

- Keep `N8N_API_KEY` in Coolify secrets (never in prompts).
- Keep OpenClaw gateway internal-only; do not publish its port.
- Keep an approval gate (Action Draft) for:
  - workflow activation
  - credential edits
  - deletions

See:
- [ops/docs/ACTION_DRAFT_PROTOCOL.md](ops/docs/ACTION_DRAFT_PROTOCOL.md)
- [ops/docs/SECURITY.md](ops/docs/SECURITY.md)
