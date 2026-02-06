# Coolify Networking & Existing Resources

## Current Setup
janAGI runs as a Docker Stack on Coolify (Hostinger VPS).

### Services in the Stack
| Service | Internal Hostname | Port | Image |
|---------|-------------------|------|-------|
| PostgreSQL | `postgresql` | 5432 | pgvector/pgvector:0.8.x-pg16 |
| n8n | `n8n` | 5678 | n8nio/n8n:latest |
| OpenClaw (opt) | `openclaw` | 18789 | — |

### Database Connection (from n8n)
- **Host**: `postgresql` (Coolify-managed internal DNS — NOT `localhost`)
- **Port**: `5432`
- **Database**: `n8n`
- **User**: `n8n`
- **Password**: (set via Coolify environment variable)

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
