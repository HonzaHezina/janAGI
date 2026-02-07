# RAG (Retrieval-Augmented Generation)

> This is a brief overview. Full details:
> - **DB tables & functions**: [DB_SCHEMA.md](DB_SCHEMA.md)
> - **Memory architecture**: [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md)
> - **SQL templates**: [`ops/n8n/sql/RAG_POSTGRES_NODES.sql`](../n8n/sql/RAG_POSTGRES_NODES.sql)

## Memory Types

1. **Short-term** (`rag.events`): Every message in every conversation — append-only log.
2. **Long-term** (`rag.chunks`): Curated facts, extracted knowledge, ingested documents — vector-indexed.
3. **Artifacts** (`rag.artifacts`): Generated outputs (OpenClaw results, specs, code).

## RAG Pipeline
```
Source (URL, file, chat) → rag.sources
  → Document (deduplicated by hash) → rag.documents
    → Chunks (split + embedded) → rag.chunks
```

Embeddings: OpenAI `text-embedding-3-small` → 1536 dimensions.
Index: HNSW (`vector_cosine_ops`) for fast approximate nearest neighbor search.
Search function: `rag.search_chunks(project_key, embedding, threshold, limit)`.

## Optimization (Future)
- TTL: auto-expire old events (e.g. 180 days)
- Session summaries: condense every N messages into a summary chunk
- Pinning: mark important facts as permanent (move to `rag.chunks` with `metadata.pinned=true`)
- Deduplication: hash-based document dedup prevents storing the same content twice
