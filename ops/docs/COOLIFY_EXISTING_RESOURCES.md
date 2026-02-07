# Coolify Networking & Existing Resources

## Current Setup
janAGI runs as a Docker Stack on Coolify (Hostinger VPS).

## Stable Hostname Convention

**Rename all Coolify resources to short, predictable names.**
Coolify uses the resource name as the Docker hostname. Random suffixes
(e.g., `mindsdb-wc88ks`) work but are painful to maintain.

| Resource Name | Purpose | Internal Hostname |
|---------------|---------|-------------------|
| `janagi-db` | PostgreSQL + pgvector | `janagi-db:5432` |
| `n8n` | Workflow orchestrator | `n8n:5678` |
| `openclaw` | AI agent (internal-only) | `openclaw:18789` |
| `mindsdb` | Batch analytics | `mindsdb:47335` |

### How to Rename in Coolify
1. Go to **Projects → your project → resource card**
2. Click **Settings** (gear icon)
3. Change the **Name** field to the short name
4. Redeploy the resource

### Verify DNS from Inside a Container

Open Terminal for any container in Coolify and run:

```bash
# Check if hostnames resolve
getent hosts openclaw
getent hosts mindsdb
getent hosts janagi-db

# Or ping:
ping -c 1 openclaw
```

If DNS doesn't resolve:
- Services are not in the same Docker network
- Resource name doesn't match the expected hostname
- Fix in Coolify → Settings → Networks

### Services in the Stack
| Service | Internal Hostname | Port | Image | Exposed? |
|---------|-------------------|------|-------|----------|
| PostgreSQL | `janagi-db` | 5432 | pgvector/pgvector:0.8.x-pg16 | ❌ No |
| n8n | `n8n` | 5678 | n8nio/n8n:latest | ✅ Webhooks (HTTPS) |
| OpenClaw | `openclaw` | 18789 | — | ❌ No (internal-only) |
| MindsDB | `mindsdb` | 47334–47336 | mindsdb/mindsdb:latest | ❌ No |

### Database Separation

**Two logical databases on one Postgres instance:**

| Database | Purpose | Who connects |
|----------|---------|-------------|
| `n8n` | n8n internal state (workflows, credentials, executions) | n8n only |
| `janagi` | Domain data (`rag.*`, `analytics.*`) | n8n Postgres nodes, MindsDB, OpenClaw |

> ⚠️ **Never store janAGI business data in the `n8n` database.**
> n8n upgrades can run schema migrations on its own DB. If your business data
> is in the same DB, a bad migration could lock or corrupt it.

In n8n, you will have **two Postgres credentials**:
1. **n8n internal** (auto-configured by n8n) — `n8n` DB
2. **janAGI data** (manual credential) — `janagi` DB, host=`janagi-db`

### Database Connection (from n8n Postgres nodes)
- **Host**: `janagi-db` (Coolify resource name → Docker hostname)
- **Port**: `5432`
- **Database**: `janagi`
- **User**: `janagi`
- **Password**: (set via Coolify environment variable `JANAGI_DB_PASSWORD`)

### Critical Rule
**Never use `localhost` or `127.0.0.1`** to connect between containers.
Each container has its own network namespace. Use the Docker service name instead.

Common mistake:
```
# WRONG (will fail with "Connection Refused")
postgresql://localhost:5432/n8n

# CORRECT
postgresql://n8n:password@postgresql:5432/n8n
```

### pgvector
The `vector` extension (v0.8.1+) is already installed in the database.
Verify with: `SELECT * FROM pg_extension WHERE extname = 'vector';`

### Adding Init Scripts
SQL files in `ops/infra/postgres/init/` are mounted to `/docker-entrypoint-initdb.d/` (read-only).
They run **only on first database creation** (when the data volume is empty).

To apply schema changes to an existing database:
```bash
# Connect to Postgres from the n8n container or via psql
psql -h postgresql -U n8n -d n8n -f /path/to/script.sql
```

### Volumes
| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `postgres_data` | `/var/lib/postgresql/data` | Database files |
| `n8n_data` | `/home/node/.n8n` | n8n config, credentials, encryption |
