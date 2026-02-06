# janAGI Ops — n8n + pgvector + MindsDB + Moltbot/Clawd (Hostinger + Coolify)

Tahle část ekosystému **janAGI** řeší “operativu” (sběr leadů, RAG odpovědi, schvalování, logování) a k tomu přidává
**MindsDB jako analytické oddělení** (batch scoring, trendy, reporting).

> Cíl: multi‑tenant platforma. Nový klient = nový řádek v DB + nové “zdroje” (sources) + vlastní KB.

---

## Co v repu je

- **Postgres + pgvector**: jednotný zdroj pravdy pro leady, zprávy, události + vektorové dokumenty (kniha / SOP / historie).
- **n8n**: Master orchestrátor (Hunter → Analyst → Telegram approval → Executor).
- **MindsDB**: analytický koprocesor (denní/týdenní batch modely, trendy, reporting).
- **Clawd/Moltbot worker**: “oči a ruce” pro webové zdroje (scrape/screenshot/klikání) — volané z n8n přes HTTP.

---

## Architektura (high-level)

```mermaid
flowchart LR
  subgraph Sources[Zdroje leadů]
    A1[Reddit / RSS / Web]
    A2[Další zdroje]
  end

  subgraph Ops[Operativa]
    N8N[n8n workflows]
    CL[Clawd/Moltbot worker]
    TG[Telegram approvals]
  end

  subgraph Data[Data]
    PG[(Postgres + pgvector)]
    VEC[janagi_documents (vectors)]
    ANA[analytics.*]
  end

  subgraph BI[Analytika]
    MDB[MindsDB]
  end

  A1 -->|Hunter| N8N
  A2 -->|Hunter| N8N
  N8N -->|scrape/screenshot| CL
  N8N -->|write| PG
  PG --- VEC
  N8N -->|notify/approve| TG

  PG -->|read| MDB
  MDB -->|write analytics| ANA
  N8N -->|read analytics| ANA
```

---

## RAG paměť (3 typy v jedné tabulce)

Všechny “dokumenty” (kniha / SOP / historie chatu) jsou v **jedné** tabulce `janagi_documents`:

- `type=expert_knowledge` (statická znalost)
- `type=sop` (procedurální pravidla)
- `type=history` (dynamická paměť — každá zpráva)

Každý záznam má `metadata.client_id` pro multi‑tenant filtraci.

---

## Rychlý start (lokálně)

### 1) Připrav env
Zkopíruj:
```bash
cp ops/infra/.env.example ops/infra/.env
```

Vyplň minimálně:
- `POSTGRES_PASSWORD`
- `N8N_ENCRYPTION_KEY`
- `MISTRAL_API_KEY` (pro embeddingy / chat modely)

### 2) Spusť stack
```bash
cd ops/infra
docker compose up -d
```

- n8n: http://localhost:5678
- MindsDB UI: http://localhost:47334
- MindsDB MySQL API: localhost:47335
- Postgres: localhost:5432

### 3) Import workflow šablon
V `ops/n8n/workflows/` jsou exporty (nebo skeletony). Importuj je do n8n přes UI.

---

## OpenClaw Turbo (n8n ↔ OpenClaw)

OpenClaw je volitelný “Turbo” pro úlohy, které vyžadují *oči a ruce* (web/UI, multi-step ops).

- V Docker/Coolify **nepoužívej** z n8n `http://127.0.0.1:18789`.
- Použij interní DNS na stejné síti: `OPENCLAW_BASE_URL=http://openclaw:18789`.

Dokumentace + šablony:
- `ops/docs/OPENCLAW_TURBO.md`
- `ops/docs/ACTION_DRAFT_PROTOCOL.md`
- `ops/docs/WORKFLOWS.md`
- `ops/docs/SPECKIT_OPENCLAW_CLI.md`

---

## Deploy (Hostinger VPS + Coolify)

1. V Coolify vytvoř nový “Docker Compose” projekt a vlož obsah `infra/docker-compose.yml`.
2. Nastav environment proměnné (podle `infra/.env.example`).
3. Připoj domény (n8n, případně mindsdb UI jen interně / přes auth).
4. Zajisti persistent volumes pro:
   - Postgres data
   - n8n data (`/home/node/.n8n`)
   - MindsDB storage (`/root/mdb_storage`)

---

## Repo struktura

```
.
├── ops/
│   ├── docs/
│   │   ├── OPENCLAW_TURBO.md
│   │   ├── ACTION_DRAFT_PROTOCOL.md
│   │   ├── PERSONAL_ASSISTANT_TURBO.md
│   │   ├── WORKFLOWS.md
│   │   ├── SECURITY.md
│   │   ├── N8N_WORKFLOW_BUILDER.md
│   │   └── N8N_UI_OPERATOR.md
│   ├── infra/
│   │   ├── docker-compose.yml
│   │   ├── .env.example
│   │   ├── openclaw/
│   │   │   └── openclaw.json.patch.internal.example
│   │   └── postgres/
│   │       └── init/
│   │           ├── 001_extensions.sql
│   │           └── 010_tables.sql
│   └── n8n/
│       └── workflows/
│           ├── WF_01_Ingest_Message.json
│           ├── WF_02_Hunter_Run.json
│           ├── WF_03_Analyst_Draft_and_Telegram_Approval.json
│           ├── WF_04_Executor_On_Approve.json
│           ├── WF_10_Turbo_OpenClaw_Run.json
│           ├── WF_11_Turbo_OpenClaw_UI_Operator.json
│           ├── WF_12_Turbo_OpenClaw_Run_RawBody.json
│           └── WF_20_Builder_Create_Workflow_via_API.json
└── services/
  └── clawd_worker/
    ├── Dockerfile
    └── app/
      └── main.py
```

---

## Bezpečnost a ToS

- Pro sociální sítě preferuj **oficiální API** nebo “human-in-the-loop” (copy/paste), jinak hrozí blokace účtů.
- Neposílej do logů osobní údaje navíc. Nastav retention (TTL) pro `history` dle potřeby.

---

## Další kroky (roadmap)

- [ ] Hotové n8n workflow exporty (včetně Telegram callbacků)
- [ ] Skutečný Hunter skill pro 1 zdroj (doporučeně Reddit/RSS)
- [ ] MindsDB: první daily job → `analytics.trends_daily`
- [ ] Dashboard (bolt.diy / UI) pro “lead inbox” + approvals
