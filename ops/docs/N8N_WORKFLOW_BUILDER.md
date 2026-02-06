# OpenClaw ↔ n8n “Workflow Builder” (API-first)

Goal: **Tell OpenClaw what workflow you want → it returns an importable n8n workflow JSON → n8n creates it via API**.

This is the most robust approach:
- versionable (JSON)
- testable (you can validate JSON before applying)
- not brittle like UI clicking
OpenClaw takes over everything you would otherwise do manually in n8n UI.
You just describe what you want — OpenClaw generates the workflow JSON,
n8n applies it through its REST API.
---

## Recommended architecture

**n8n remains the orchestrator**, OpenClaw is the “Turbo”:

1) n8n receives a user request (Telegram/Webhook/UI)
2) OpenClaw generates a **workflow spec** (n8n JSON: `name/nodes/connections/settings`)
3) n8n validates + applies it through the **n8n REST API**
4) n8n responds with the result (workflow id, name, activation status)

UI automation (“clicking in n8n”) stays as a fallback only.
---

## n8n API Endpoints

| Method | Endpoint                         | Purpose                    |
|--------|----------------------------------|----------------------------|
| POST   | `/api/v1/workflows`              | Create new workflow        |
| PATCH  | `/api/v1/workflows/:id`          | Update existing workflow   |
| PATCH  | `/api/v1/workflows/:id/activate` | Activate workflow          |
| GET    | `/api/v1/workflows`              | List all workflows         |
| DELETE | `/api/v1/workflows/:id`          | Delete workflow            |

All calls require `X-N8N-API-KEY` header.
---

## Preconditions (Coolify / self-hosted)

### 1) Internal DNS
Your services are on the same Coolify/docker network:

- n8n: `http://n8n:5678`
- OpenClaw gateway: `http://openclaw:18789`

If not on the same network, create a shared network in Coolify and attach both stacks.

### 2) n8n API key
Create an API key in n8n: **Settings → API → Create key**.

Store as a Coolify secret:
- `N8N_API_KEY`

Also set:
- `N8N_BASE_URL=http://n8n:5678`

### 3) OpenClaw `/v1/responses` enabled
If you see **405 Method Not Allowed**, enable endpoints (see [OPENCLAW_TURBO.md](OPENCLAW_TURBO.md)).

---

## Pattern A — n8n calls OpenClaw, then n8n calls its own API (recommended)

1) HTTP Request → OpenClaw `/v1/responses`
2) Code node → extract + validate the JSON workflow
3) HTTP Request → `POST ${N8N_BASE_URL}/api/v1/workflows`
4) (Optional) `PATCH /api/v1/workflows/:id/activate`

### OpenClaw Call Shape

```json
{
  "model": "openclaw:main",
  "user": "n8n-workflow-builder",
  "input": "Create an n8n workflow JSON. Return ONLY a valid JSON object with structure {\"name\":\"...\",\"nodes\":[...],\"connections\":{...},\"settings\":{...}}. No text around it.\n\nUser request:\n<user_prompt_here>"
}
```

### n8n API Call Shape

```
POST http://n8n:5678/api/v1/workflows
Headers:
  Content-Type: application/json
  X-N8N-API-KEY: <your_api_key>
Body:
  <workflow JSON from OpenClaw>
```

Template:
- [ops/n8n/workflows/WF_20_Builder_Create_Workflow_via_API.json](../n8n/workflows/WF_20_Builder_Create_Workflow_via_API.json)

---

## Pattern B — OpenClaw creates workflows directly (not recommended by default)

OpenClaw can call `http://n8n:5678/api/v1/...` too, but:
- you must store `N8N_API_KEY` in OpenClaw runtime
- you lose safety gates (validation/allowlist) that are easy in n8n

Use only with strict policy + approval gating.
---

## Workflow Skeleton (what OpenClaw generates)

n8n workflow JSON has this minimum structure:

```json
{
  "name": "My Workflow",
  "nodes": [
    {
      "parameters": { ... },
      "id": "unique-id",
      "name": "Node Name",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [200, 260]
    }
  ],
  "connections": {
    "Node Name": {
      "main": [[{ "node": "Next Node", "type": "main", "index": 0 }]]
    }
  },
  "active": false,
  "versionId": "1"
}
```

OpenClaw must generate this exact structure. The Code node in n8n validates
that `name`, `nodes`, and `connections` exist before sending to the API.
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
