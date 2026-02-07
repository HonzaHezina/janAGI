# MindsDB daily jobs (notes)

MindsDB is a Federated Query Engine for AI (Connect → Unify → Respond).
In janAGI, it runs scheduled jobs that write results to `analytics.*`.
n8n reads `analytics.*` and uses it for prioritization/reporting.

## Example: connect Postgres
```sql
CREATE DATABASE janagi_pg
WITH ENGINE = 'postgres',
PARAMETERS = {
  "host": "janagi-db",       -- Coolify resource name (docker-compose: "postgres")
  "port": "5432",
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

