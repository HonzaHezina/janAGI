# ARCHITECTURE

## Cíl
Postavit multi-tenant “ops platformu” pro sběr leadů a asistovanou komunikaci (RAG), s batch analytikou v MindsDB.

## Komponenty

### Postgres + pgvector
- `rag.*` = operativní data + audit log + RAG index
- `analytics.*` = výsledky MindsDB (batch scoring, trendy)

### n8n (Master orchestrator)
3 hlavní workflow:
1) **Hunter**: sběr kandidátů → `rag.documents` (+ embed do `rag.chunks`)
2) **Analyst**: retrieval (knowledge+sop+history) → draft → Telegram approval
3) **Executor**: schválení → odeslání (manual/API) + log do `rag.events`

### Clawd/Moltbot worker (oči a ruce)
HTTP worker, který:
- čte weby, dělá screenshoty, vrací strukturovaná data
- NENÍ to “autoposter” do sítí by default — to je vždy přepínatelná capability

### MindsDB (analytické oddělení)
- připojí se k Postgresu read-only
- počítá:
  - trend topics
  - batch lead scoring
  - reporting
- ukládá do `analytics.*`, které čte n8n

## Datové toky

### Lead pipeline
1) Hunter najde kandidáta → UPSERT do `rag.sources`/`rag.documents` (dedupe pomocí unique indexů)
2) Analyst:
  - načte thread/conversation + poslední zprávy (`rag.events`)
  - retrieval nad `rag.chunks` (knowledge/sop/history přes metadata)
   - vytvoří draft odpovědi + vysvětlení
   - pošle do Telegramu (Approve/Edit/Ignore)
3) Executor:
  - uloží finální text + status jako event
  - log `rag.events`

### RAG retrieval pravidla
- knowledge: `metadata.type=expert_knowledge AND client/project`
- sop: `metadata.type=sop AND client/project`
- history: `metadata.type=history AND conversation_id`

## Observability
-- každá akce zapisuje do `rag.events`:
  - `type` (hunter.found, analyst.draft, telegram.approved, executor.sent, ...)
  - `payload` (json)
  - `run_id` + `conversation_id`

## Multi-tenant
- Vždy mít `client_id`
- Vektorové chunk-y musí mít `client_id` a `project_id`
- Všechny query musí filtrovat na `client_id`

