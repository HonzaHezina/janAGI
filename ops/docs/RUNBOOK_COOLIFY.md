# RUNBOOK (Coolify / Hostinger)

Kanonická infra v tomto repu je `ops/infra/docker-compose.yml` a init DB skripty jsou v `ops/infra/postgres/init/`.

## Doporučení
- n8n a Postgres vždy s persistent volumes
- n8n: nastav `N8N_ENCRYPTION_KEY` hned od začátku (jinak se v DB uloží data pod jiným klíčem)
- mindsdb UI nezveřejňovat bez auth / VPN

## Ports
- n8n: 5678
- postgres: 5432 (interně)
- mindsdb: 47334 (UI+HTTP), 47335 (MySQL API)

## Zálohy
- Postgres: pravidelné pg_dump
- n8n: volume `/home/node/.n8n` + DB

## Deploy checklist (minimum)
- V Coolify použij compose z `ops/infra/docker-compose.yml`
- V secrets nastav minimálně:
	- `POSTGRES_PASSWORD`
	- `N8N_ENCRYPTION_KEY`
	- `MISTRAL_API_KEY` (pokud embeduješ)
- Ověř, že Postgres volume je persistent a že init skripty se provedly (viz tabulky ve schématu `rag` a `analytics`).

