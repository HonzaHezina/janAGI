# Coolify: wiring with existing resources

You already run these resources in one Coolify project (same VPS):

- n8n + PostgreSQL
- MindsDB
- OpenClaw Gateway (Turbo / UI operator)

This document explains how to wire them **without public ports**.

---

## Internal hostnames (no public ports)

If resources share the same docker network, call them by **service name**:

- n8n → OpenClaw: `http://openclaw:18789/v1/responses`
- OpenClaw → n8n: `http://n8n:5678/`
- MindsDB → Postgres: `postgres:5432` (or your DB service name)

---

## Quick checks from inside n8n container

```bash
getent hosts openclaw
getent hosts n8n

curl -sS http://openclaw:18789/ | head
curl -sS http://n8n:5678/ | head
```

---

## Common pitfall: 127.0.0.1

Inside a container, `127.0.0.1` points to *that container*.
So from n8n in Docker, `http://127.0.0.1:18789` will **not** reach OpenClaw.
Use `http://openclaw:18789` on the shared network instead.
