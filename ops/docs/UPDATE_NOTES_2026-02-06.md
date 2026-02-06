# Update notes – 2026-02-06

This update reflects the OpenClaw ↔ n8n integration discussed after finishing OpenClaw onboarding.

## What changed

### Docs
- Added Turbo docs under `ops/docs/`:
  - correct endpoint/body shapes
  - Docker/Coolify-safe base URLs (`http://openclaw:18789`, not localhost)
  - fixes for 405/404/429
  - robust n8n body pattern using `JSON.stringify(...)`
- Added Action Draft protocol with Telegram-safe payload markers and extraction code
- Added Workflow Builder (API-first) pattern

### n8n templates
- Added Turbo runner workflows and builder workflow in `ops/n8n/workflows/`

### Env example
- Added `OPENCLAW_BASE_URL`, `OPENCLAW_GATEWAY_TOKEN`, `N8N_BASE_URL`, `N8N_API_KEY` to `ops/infra/.env.example`
