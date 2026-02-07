# OpenClaw as n8n UI Operator (robust, not fragile)

You want: "Tell Jackie what to build → OpenClaw builds it → you only review the result".
n8n routes the request (integrator), OpenClaw does the work (brain+hands).

UI automation is inherently brittle if done with fixed CSS selectors or coordinates.
This kit uses a safer pattern:

- **PLAN:** OpenClaw explains what it will do (steps + acceptance criteria)
- **APPLY:** OpenClaw performs the UI actions
- **VERIFY:** OpenClaw re-opens the result and returns evidence (screenshots + exported JSON)

---

## 1) Prepare an operator user in n8n

Create a dedicated user in n8n with minimal permissions needed to create/edit workflows:

- `N8N_OPERATOR_EMAIL`
- `N8N_OPERATOR_PASSWORD`

Store these as Coolify secrets.

---

## 2) Ensure internal routing works (no public ports)

OpenClaw must be able to reach n8n:

- internal URL: `http://n8n:5678`

Set:
- `N8N_INTERNAL_URL=http://n8n:5678`

---

## 3) Recommended Operator prompt contract

When n8n calls OpenClaw, include:

- target URL: `N8N_INTERNAL_URL`
- operator login credentials (injected via env/secrets, not hard-coded)
- strict JSON output schema

Output JSON should include:
- `status` (`ok|fail`)
- `changes` (list)
- `evidence` (screenshots paths or textual evidence)
- `workflow_export` (JSON string if possible)
- `notes`

---

## 4) Review gate (human-in-the-loop)

Even in autopilot, keep one human review point:

- OpenClaw returns PLAN and you approve
- OpenClaw applies + verifies
- You approve activation

See:
- [ops/docs/ACTION_DRAFT_PROTOCOL.md](ops/docs/ACTION_DRAFT_PROTOCOL.md)

---

## 5) Templates

See [ops/n8n/workflows](ops/n8n/workflows/):

- `WF_10_Turbo_OpenClaw_Run.json`
- `WF_11_Turbo_OpenClaw_UI_Operator.json`
- `WF_12_Turbo_OpenClaw_Run_RawBody.json`
