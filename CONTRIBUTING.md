# Contributing

## Project Context
janAGI is an autonomous personal AI agent (Jackie) built on n8n + PostgreSQL/pgvector + OpenClaw.
All operational code lives in `ops/`.

## Rules
- All data must be **scoped** to `client_id` + `project_id` (multi-tenant ready).
- Every workflow step must be **idempotent** (safe to repeat).
- All actions are logged to `rag.events` with full traceability.
- No hardcoded secrets. Use Coolify env variables or `.env`.
- Database changes go into `ops/infra/postgres/init/` as new numbered files.

## Structure
- Documentation → `ops/docs/`
- Database schema → `ops/infra/postgres/init/` (numbered init scripts)
- n8n workflow exports → `ops/n8n/` (core) or `ops/n8n/workflows/` (templates)
- Reusable code snippets → `ops/n8n/snippets/` (JS) and `ops/n8n/sql/` (SQL)
- Shell scripts → `ops/scripts/`
- Microservices → `ops/services/`

## Commit Style
- `feat: ...` — New feature
- `fix: ...` — Bug fix
- `docs: ...` — Documentation only
- `chore: ...` — Maintenance, dependencies
- `refactor: ...` — Code restructure without behavior change

## Key Docs
- [ARCHITECTURE.md](ops/docs/ARCHITECTURE.md) — System design
- [DB_SCHEMA.md](ops/docs/DB_SCHEMA.md) — Database reference
- [MEMORY_ARCHITECTURE.md](ops/docs/MEMORY_ARCHITECTURE.md) — RAG/memory flows
- [WORKFLOWS.md](ops/docs/WORKFLOWS.md) — n8n workflow index
