# DB_SCHEMA

## Extensions
- `pgcrypto` (UUID)
- `vector` (pgvector)

## Tabulky

### leads
- jeden řádek = jeden lead (post, komentář, DM thread)
- dedupe: UNIQUE (client_id, source_type, source_ref)

### messages
- všechny zprávy (user/seller/system)
- po INSERT se message embeduje a uloží do `janagi_documents` s `type=history`

### events
- audit log + observability + billing

### janagi_documents (vector store)
Sloupce:
- `id` UUID
- `content` TEXT
- `embedding` VECTOR(1024) (pro mistral-embed)
- `metadata` JSONB (client_id, type, lead_id, message_id, role, ts, source...)

Metadata standard:
```json
{
  "client_id": "uuid",
  "type": "history|expert_knowledge|sop",
  "lead_id": "uuid",
  "message_id": "uuid",
  "role": "user|seller|system",
  "source": "telegram|book|sop",
  "ts": "2026-02-02T12:34:56Z"
}
```

### analytics.*
Výsledky MindsDB batch jobů:
- `analytics.trends_daily`
- `analytics.lead_scores`
- další dle potřeby
