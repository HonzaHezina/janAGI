````markdown
# clawd_worker

Minimal FastAPI worker (stub) pro “oči a ruce” (scrape / screenshot / extraction).

## API contract

### POST /tasks/hunt
Input:
```json
{
  "client_id": "uuid",
  "source_type": "reddit|rss|web",
  "query": "string",
  "since": "ISO timestamp",
  "limit": 50
}
```

Output:
```json
{
  "items": [
    {
      "source_type": "reddit",
      "source_ref": "post_id_or_hash",
      "url": "https://...",
      "author": "optional",
      "created_at": "ISO",
      "text_excerpt": "..."
    }
  ]
}
```

### POST /tasks/screenshot
Stub pro budoucí použití (Browserless / Playwright / OpenClaw).

## Poznámka
Tenhle worker je záměrně “dumb” – logika patří do n8n.

````
