# MindsDB daily jobs (notes)

Doporučený pattern:
- MindsDB běží batch (denně).
- Výsledky zapisuje do `analytics.*`.
- n8n jen čte `analytics.*` a používá to v prioritizaci / reportingu.

## Example: connect Postgres
```sql
CREATE DATABASE janagi_pg
WITH ENGINE = 'postgres',
PARAMETERS = {
  "host": "postgres",        -- docker-compose service name
  "port": "5432",            -- Coolify: use "janagi-db" as host
  "user": "mindsdb_ro",
  "password": "*****",
  "database": "janagi",
  "schema": "rag"
};
```

## Example: daily job skeleton
```sql
-- pseudo
CREATE JOB trends_daily
AS (
  -- compute topics/keywords from rag.events / rag.documents, write into analytics.trends_daily
)
EVERY 1 day;
```

