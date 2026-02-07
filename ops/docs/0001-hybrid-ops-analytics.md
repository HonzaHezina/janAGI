# ADR-0001: Hybrid Ops + Analytics Architecture

**Status**: Accepted (updated 2026-02-06)
**Context**: janAGI needs real-time chat+memory operations AND optional batch analytics.

## Decision
- **n8n + pgvector** handles all real-time operations: chat, RAG, Telegram, Spec-Kit.
- **MindsDB** is an optional add-on for batch analytics (daily scoring, trend detection).
- All data lives in PostgreSQL under the `rag.*` schema.
- Analytics results go to `analytics.*` schema (optional).

## Rationale
- Separates low-latency chat/RAG from heavy batch processing.
- n8n is the single orchestrator — MindsDB is a read-only consumer.
- Simplifies deployment: MindsDB can be added or removed without affecting core operations.

## Current State
- MindsDB is deployed in the docker-compose stack (active, not commented out).
- MindsDB connects to Postgres via `mindsdb_ro` read-only role.
- Results written to `analytics.*` schema. See [MINDSDB_ANALYTICS.md](MINDSDB_ANALYTICS.md).
