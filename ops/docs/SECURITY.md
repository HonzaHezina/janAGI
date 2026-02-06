# Security notes

This stack includes components that can store credentials and execute actions. Treat it like **production infrastructure** from day 1.

## Secrets
- Use Coolify secrets/env var store.
- Never commit `.env`, tokens, or credential files to git.

## n8n API key
- If you use the Workflow Builder pattern, create an API key in n8n and store it as `N8N_API_KEY`.
- Treat it like a password; anyone who has it can create/update workflows via API.

## n8n encryption key
Set `N8N_ENCRYPTION_KEY` from day 1 and never change it unless you intentionally rotate credentials.

## OpenClaw hardening essentials
OpenClaw stores sensitive state under `~/.openclaw/` (config, credentials, sessions, transcripts). If you deploy it:

- **Auth required:** always configure token/password auth.
- **Network exposure:** prefer internal-only networking; do not publish the raw port publicly.
- **Least privilege:** use dedicated agents with strict tool allowlists.
- **Rotate secrets:** if compromised, rotate OpenClaw token/password and provider creds.

## Data retention
Leads/messages can include personal data. Add a retention policy (e.g., delete/anon after 30–90 days) if needed.

## OpenClaw HTTP endpoints
- `/v1/responses` and `/v1/chat/completions` are **disabled by default**; only enable what you need.
- Prefer internal-only networking (`http://openclaw:18789`) and auth tokens.
- Consider a dedicated `ui-operator` agent with strict tool allowlist and a separate session key.
