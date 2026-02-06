# n8n SQL Snippets & Helper Code

This directory contains code snippets that you can copy/paste into n8n nodes.

## SQL (Postgres Node)
The file `RAG_POSTGRES_NODES.sql` contains the **exact SQL queries** needed for the `rag.*` schema.
- **Why?** n8n Postgres nodes do not support named parameters (`:param`). You must use `$1, $2...`.
- **How to use:** Copy the query block into the node's "Query" field, and add parameters in the "Query Parameters" list in exactly the order specified in the snippet comments.

## JavaScript (Code Node)
### 1. Unified Chat ID (`TELEGRAM_NORMALIZATION.js`)
Use this to normalize `message` vs `callback_query` into a single `chat_id` / `text` object.
- **Why?** Simplifies downstream logic (logging, RAG).
- **How to use:** Paste into a Code node after the Telegram Trigger.

### 2. Payload Extractor (`TELEGRAM_PAYLOAD_EXTRACTOR.js`)
Use this to extract hidden JSON payloads from human-readable approval messages (e.g. `[ACTION_DRAFT]` or `---PAYLOAD_JSON---`).
- **Why?** For "Approve -> Execute" flows where you need the original machine instruction without the chat text.
- **How to use:** Paste into a Code node after an "Approval" callback trigger.
