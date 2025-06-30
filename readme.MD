# 🧠 janAGI – Open-source AI Agent Orchestration Framework

> ✨ Pracuj se záměrem. Neřeš nástroje.  
> 🛠 Powered by [mcp-agent](https://github.com/lastmile-ai/mcp-agent)  
> 💬 Frontend přes [Bolt.diy](https://github.com/menloresearch/bolt.diy)

---

## 🇨🇿 Popis projektu (Czech)

### ✨ Vize
janAGI přináší nový mentální model práce s umělou inteligencí.  
📌 Nepracuješ s nástroji nebo agenty. Pracuješ se **záměrem**.  
LLM vyhodnotí, zda umí odpovědět sám, nebo musí vytvořit **plán**, který vykonají specializovaní agenti.

---

### 🧩 Architektura

- 🧠 **Planner agent (LLM)** – centrální mozek systému
- 🤖 **Funkční agenti** – např. `AgentCodeWriter`, `AgentImageGen`
- 📦 **mcp-agent** – orchestrace agentů
- 🧑‍💻 **Bolt.diy** – uživatelské rozhraní pro zadání, potvrzení a sledování úloh

---

### 🔁 Jak to funguje

1. Uživatel zadá **záměr** (např. „Vytvoř mi landing page s obrázky“)
2. LLM vyhodnotí, zda odpoví rovnou, nebo:
   - Vytvoří plán (`plan = [task1, task2, ...]`)
   - Vybere agenty a přidělí úkoly
   - Po schválení spustí plán přes `mcp-agent`
3. Výstupy agentů se streamují zpět do Bolt.diy UI

---

### 🧠 Komponenty

- `planner.agent.yaml` – definuje hlavní LLM plánovač
- `*.agent.yaml` – definice jednotlivých agentů (kód, obrázky, texty, scraping...)
- `bolt.diy` – frontend s komponentami `AgentOutputViewer`, `PlanViewer`, `DiffView`
- `mcp-agent` – middleware pro plánování, spouštění a koordinaci agentů

---

### 🧱 MVP

✅ Bolt.diy jako frontend  
✅ Planner LLM jako agent přes MCP  
✅ Jeden funkční agent (`AgentCodeWriter`)  
✅ YAML popis agentů (`agent.yaml`)  
✅ API napojení frontend ↔ backend  

---

## 🇬🇧 Project Overview (English)

### ✨ Vision
janAGI introduces a new mental model for working with AI.  
You don’t operate tools – you **declare intent**.  
The system either answers directly (via LLM) or dynamically creates a **plan** and executes it using agents.

---

### 🧩 Architecture

- 🧠 **Planner Agent (LLM)** – central orchestrator
- 🤖 **Functional Agents** – like `AgentCodeWriter`, `AgentImageGen`
- 📦 **mcp-agent** – lightweight agent orchestrator
- 🧑‍💻 **Bolt.diy** – frontend for intent input, plan confirmation, and result visualization

---

### 🔁 How it works

1. User submits **intent** (e.g., "Create a landing page with images")
2. LLM decides:
   - If it can answer directly → responds like a chatbot
   - If task is complex → creates a plan (series of steps + agents)
3. Plan is shown in UI and confirmed by user
4. After confirmation, tasks are executed via `mcp-agent`
5. Agent outputs are streamed to Bolt.diy in real time

---

### 🧠 Components

- `planner.agent.yaml` – defines main LLM planner
- `*.agent.yaml` – defines agents (code, image, text, scraping...)
- `bolt.diy` – user interface (React + Tailwind)
- `mcp-agent` – FastAPI backend for agent orchestration

---

### 🧱 MVP Scope

✅ Bolt.diy as frontend  
✅ Planner agent running via `mcp-agent`  
✅ One working agent (`AgentCodeWriter`)  
✅ agent.yaml schema for agent definitions  
✅ REST API communication between frontend & backend  

---

## 🌱 Get Involved

We are building janAGI as an open-source framework to support:
- 🛠 Rapid AI prototyping
- 🔌 Agent-based system integration
- 🤖 Internal AI assistants for teams
- 📚 Education in LLM orchestration

> 💡 Pull requests, issues, and ideas are welcome!

---

## 📄 License

MIT License – use freely, modify, and build your own agents.

