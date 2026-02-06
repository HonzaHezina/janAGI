# JanAGI Memory Architecture

This document describes the shared memory architecture for JanAGI, enabling collaboration between **n8n** (Orchestrator) and **OpenClaw** (Agent) using a centralized PostgreSQL `pgvector` store.

## Overview

The system uses a **Single Source of Truth** for long-term memory (RAG) and audit logs.
- **Database**: PostgreSQL (with `pgvector` and `pgcrypto` extensions).
- **Location**: Running in the same Docker Stack / Coolify Project as n8n.
- **Access**:
    - **n8n**: Direct SQL access (via Postgres Nodes) for `UPSERT` and `SELECT`.
    - **OpenClaw**: Indirect access via n8n Webhooks (API Layer) for safety and audit.

## Database Schema

The database is split into logical schemas to separate "Semantic Memory" from "Audit Logs".

### 1. RAG Memory (`rag.janagi_documents`)
Stores semantic knowledge, specifications, and long-term facts.
*   **Use Case**: RAG (Retrieval-Augmented Generation).
*   **Key Columns**:
    *   `content` (Text): The chunk of information.
    *   `embedding` (Vector): 1024 (Mistral/Gemini) or 1536 (OpenAI).
    *   `namespace` (Text): Scope (e.g., `janagi`, `project-x`).
    *   `metadata` (JSONB): Source trace, tags, original URL.

### 2. Chat Audit (`chat.messages`)
Stores the raw conversation history for debugging and short-term context.
*   **Use Case**: Chat history display, debugging, short-term context window.
*   **Key Columns**:
    *   `chat_id`, `platform`, `role`, `content`.

## Workflow Protocols

### A. Memory Upsert (Writing to Memory)
**Trigger**: Webhook `POST /webhook/memory-upsert`
**Payload**:
```json
{
  "namespace": "janagi",
  "content": "Deploying on Coolify requires the pgvector image.",
  "metadata": { "source": "openclaw", "trace_id": "..." }
}
```
**Process**:
1.  **Embed**: Generate vector from `content` using the standard Embedding Model.
2.  **Format**: Convert vector array to string format `[...]`.
3.  **Insert**: Execute SQL `INSERT INTO rag.janagi_documents ...`.

### B. Memory Search (Reading from Memory)
**Trigger**: Webhook `POST /webhook/memory-search`
**Payload**:
```json
{
  "namespace": "janagi",
  "query": "How do I deploy on Coolify?",
  "top_k": 5
}
```
**Process**:
1.  **Embed**: Generate vector from `query`.
2.  **Search**: Execute SQL `SELECT ... ORDER BY embedding <=> $1 LIMIT $2`.
3.  **Return**: JSON list of matches.

### C. Chat Interaction Flow (Telegram/Chat)
1.  **Ingest**: Telegram Trigger receives message.
2.  **Log User**: Insert into `chat.messages` (Role: `user`).
3.  **Retrieve Context**: Call `Memory Search` with user query.
4.  **AI Process**: Agent (Jackie/OpenClaw) processes query + retrieved context.
    *   *Decision*: Should this new info be stored?
5.  **Log Assistant**: Insert into `chat.messages` (Role: `assistant`).
6.  **Store (Optional)**: If Agent decided to store data, call `Memory Upsert`.
7.  **Reply**: Send message back to Telegram.

## Integration Configuration

### n8n
- **Credentials**: Use `Postgres` credentials pointing to the `postgresql` service in the stack.
- **Nodes**: Use `Embeddings` node + `Postgres` node.

### OpenClaw
- **Env**: `N8N_BASE_URL=http://n8n:5678` (Internal Docker Network URL).
- **Operation**: Calls n8n Webhooks to read/write memory.
