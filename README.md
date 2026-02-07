# janAGI — Autonomous Personal AI Agent

**janAGI** is an autonomous AI agent ecosystem powered by **n8n**, **PostgreSQL + pgvector**, and **OpenClaw**.
It runs as a self-hosted stack on **Coolify** (Hostinger VPS) and acts as a personal assistant, project manager,
and knowledge system — all accessible via **Telegram**.

> **[OpenClaw](https://docs.openclaw.ai/)** is the AI "Brain" and "Hands."
> **n8n** is the "Central Nervous System" that routes tasks and manages state.
> **PostgreSQL** is the shared Memory.

---

## What It Does

1.  **🧠 Advanced Chat & Memory:** A voice-enabled assistant that classifies intents (Meeting, Task, Email, Chat) and routes them to specialized agents. (Architecture: `WF_42` Router).
2.  **👁️ Web Intelligence:** An on-demand research agent that browses the web, scrapes data, and summarizes findings. (Capability: `WF_48` + OpenClaw).
3.  **🤲 Software Factory (Spec Kit):** A spec-driven development engine. You define the feature in chat, and janAGI runs a full parallel build using AI coders (Gemini/Copilot) to deliver a Pull Request. (Capability: `WF_49` Interface + `WF_30` Engine).
4.  **⚙️ Self-Evolution:** janAGI can write its own n8n workflows via API to create new automations. (Capability: `WF_20`).

---

## Architecture (V2 Router)

```mermaid
flowchart LR
  subgraph User
    TG[Telegram]
  end

  subgraph Router["🧠 The Brain (Router)"]
    WF42[WF_42 Classifier]
  end

  subgraph Handlers["Specialized Agents"]
    CHAT[WF_46 Chat]
    PROD[WF_43-45 (Cal/Task/Mail)]
    WEB[WF_48 Web Researcher]
    DEV[WF_49 SpecKit Interface]
  end

  subgraph Execution["🤲 The Hands (Execution)"]
    ENG[WF_30 Build Engine]
    ACT[WF_41 Action Executor]
  end

  subgraph AI["OpenClaw Gateway"]
    OC[LLM + Tools]
  end

  TG -->|Text/Voice| WF42
  WF42 -->|General| CHAT
  WF42 -->|Productivity| PROD
  WF42 -->|Research| WEB
  WF42 -->|Code| DEV

  WEB & CHAT & PROD -->|Think/Act| OC
  DEV -->|Trigger| ENG
  ENG -->|Build| OC
  
  WEB -->|Action Draft| ACT
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Integrator** | **n8n** | The "Os" of the agent. Routing, State, Safety Gates. |
| **Memory** | **PostgreSQL + pgvector** | Vector store (`rag` schema), Audit Logs, Analytics. |
| **Brain** | **OpenClaw** | Self-hosted gateway for LLMs, Web Browsing, and CLI Tools. |
| **Analytics** | **MindsDB** | Federated Query Engine for BI and operational insights. |
| **Interface** | **Telegram** | Voice/Text interface for the user. |
| **Infrastructure** | **Coolify** | Docker management on VPS. |

---

## Quick Start (Coolify)

1.  **Create Stack:** Copy `ops/infra/docker-compose.yml` to a new Coolify project.
2.  **Configure Env:** Set secrets (`POSTGRES_PASSWORD`, `OPENCLAW_GATEWAY_TOKEN`, `TELEGRAM_TOKEN`, etc.).
3.  **Deploy:** Let Coolify spin up the services.
4.  **Wiring:**
    *   Import n8n workflows from `ops/n8n/workflows/`.
    *   **CRITICAL:** Update `WF_42_Jackie_Classifier` to point its "Execute Workflow" nodes to your imported sub-workflows (`WF_43`–`WF_49`).
    *   Enable `WF_42`.

---

## Documentation Index

- **[ops/docs/WORKFLOWS.md](ops/docs/WORKFLOWS.md)** — **Start Here.** Complete catalog of capabilities and wiring guide.
- **[ops/docs/ARCHITECTURE.md](ops/docs/ARCHITECTURE.md)** — Deep dive into the V2 Router architecture and data flows.
- **[ops/docs/DB_SCHEMA.md](ops/docs/DB_SCHEMA.md)** — Database layout (`rag.*`).
- **[ops/docs/OPENCLAW_DISPATCHER_CONTRACT.md](ops/docs/OPENCLAW_DISPATCHER_CONTRACT.md)** — How the Software Factory works.
- **[ops/docs/ACTION_DRAFT_PROTOCOL.md](ops/docs/ACTION_DRAFT_PROTOCOL.md)** — Safety protocols for dangerous actions.
