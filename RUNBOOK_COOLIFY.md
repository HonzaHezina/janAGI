# RUNBOOK (Coolify / Hostinger)

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
