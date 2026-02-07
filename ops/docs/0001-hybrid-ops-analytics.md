# ADR-0001: Hybrid Ops + Analytics Architecture

**Status**: Accepted (updated 2026-02-07)
**Context**: janAGI needs real-time chat+memory operations AND analytics that combine
internal data with external sources (web scraping, social media, purchases, CRM).

## Decision
- **n8n** is the **integrator/curator** — routes all workflows, manages state and safety gates.
- **OpenClaw** is the **brain, hands, and eyes** — reasoning, web browsing, project builds.
- **PostgreSQL + pgvector** is the data layer for real-time operations: chat, RAG, Telegram, Spec-Kit.
- **MindsDB** is the **analytics department** — primarily for external business intelligence
  (multi-source data aggregation, lead scoring, competitor analysis), secondarily for
  internal operational analytics (conversation trends, usage patterns).
- All operational data lives in `rag.*` schema. Analytics results go to `analytics.*` schema.

## Rationale
- Separates low-latency chat/RAG from heavy batch processing.
- n8n integrates — it does NOT think or decide. OpenClaw handles all intelligence.
- MindsDB’s strength is combining data from multiple sources (Postgres, APIs, external DBs)
  into ML models and scheduled reports. This is the primary use case.
- Simplifies deployment: MindsDB can be added or removed without affecting core operations.

## Current State
- MindsDB is deployed in the docker-compose stack (active).
- MindsDB connects to Postgres via `mindsdb_ro` read-only role.
- Results written to `analytics.*` schema. See [MINDSDB_ANALYTICS.md](MINDSDB_ANALYTICS.md).
