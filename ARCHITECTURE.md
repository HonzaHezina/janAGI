# ARCHITECTURE

## Cíl
Postavit multi-tenant “ops platformu” pro sběr leadů a asistovanou komunikaci (RAG), s batch analytikou v MindsDB.

## Komponenty

### Postgres + pgvector
- `leads`, `messages`, `events` = operativní data
- `janagi_documents` = vektory (kniha/SOP/historie)
- `analytics.*` = výsledky MindsDB

### n8n (Master orchestrator)
3 hlavní workflow:
1) **Hunter**: sběr leadů → `leads (NEW)`
2) **Analyst**: retrieval (book+sop+history) → draft → Telegram approval
3) **Executor**: schválení → odeslání (manual/API) + log do `events`

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
1) Hunter najde kandidáta → INSERT do `leads` (dedupe pomocí UNIQUE)
2) Analyst:
   - načte lead + poslední zprávy
   - retrieval nad `janagi_documents` (3 filtry)
   - vytvoří draft odpovědi + vysvětlení
   - pošle do Telegramu (Approve/Edit/Ignore)
3) Executor:
   - uloží finální text + status
   - log `events`

### RAG retrieval pravidla
- book: `type=expert_knowledge AND client_id`
- sop:  `type=sop AND client_id`
- history: `type=history AND client_id AND lead_id`

## Observability
- každá akce zapisuje do `events`:
  - `type` (hunter.found, analyst.draft, telegram.approved, executor.sent, ...)
  - `payload` (json)
  - `trace_id`

## Multi-tenant
- Vždy mít `client_id`
- Vektorové dokumenty musí mít `metadata.client_id`
- Všechny query musí filtrovat na `client_id`
