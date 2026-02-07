# Deployment Runbook (Coolify)

## Prerequisites
- Coolify instance on Hostinger VPS
- Docker Stack with PostgreSQL (pgvector image) and n8n

## Deploy Steps

### 1. Create Stack
In Coolify: **New Project → Docker Compose**
Paste `ops/infra/docker-compose.yml` content.

### 2. Environment Variables
Set via Coolify UI (never commit to git):
- `POSTGRES_DB=janagi`
- `POSTGRES_USER=janagi`
- `POSTGRES_PASSWORD=<strong-password>`
- `N8N_ENCRYPTION_KEY=<32+ chars>`
- `OPENAI_API_KEY=<your-key>`

### 3. Persistent Volumes
Ensure these volumes persist across deploys:
- `postgres_data` → `/var/lib/postgresql/data`
- `n8n_data` → `/home/node/.n8n`

### 4. Apply Schema
On first deploy, init scripts run automatically.
For existing databases, run manually:
```bash
docker exec -i <postgres-container> psql -U janagi -d janagi < ops/infra/postgres/init/020_rag_schema.sql
```

### 5. Import Workflows
In n8n UI: Import JSON files from `ops/n8n/`.

### 6. Configure Credentials
In n8n Credentials:
- **Postgres**: host=`postgres` (docker-compose) or `janagi-db` (Coolify), port=5432, db=`janagi`, user=`janagi`
- **Telegram Bot**: your bot token
- **OpenAI**: API key (for embeddings)
- **HTTP Header Auth** (optional): OpenClaw gateway token

## Health Checks
- n8n: `https://your-domain.com/healthz`
- Postgres: `pg_isready -U janagi -d janagi`

## Backup
```bash
# Database
docker exec <postgres-container> pg_dump -U n8n -d n8n > backup_$(date +%F).sql

# n8n workflows (via API)
curl -H "X-N8N-API-KEY: $KEY" https://your-domain.com/api/v1/workflows > workflows_backup.json
```

## Troubleshooting
- **Connection Refused**: Use service DNS name, not localhost. See [COOLIFY_EXISTING_RESOURCES.md](COOLIFY_EXISTING_RESOURCES.md).
- **Extension missing**: Run `CREATE EXTENSION IF NOT EXISTS vector;` in psql.
- **n8n encryption key lost**: All credentials are unrecoverable. Must re-enter.
