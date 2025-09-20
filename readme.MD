## janAGI — Open-source AI Agent Orchestration Framework

janAGI přináší nový mentální model práce s umělou inteligencí: neřešíte nástroje ani agenty, ale záměr a výsledky. Uživatel zadá jednoduchý záměr (např. „Vytvoř landing page pro pastelovou čajovnu“) a systém provede zbytek — navrhne plán, přiřadí agenty, požádá o potvrzení a poté bezpečně orchestruje exekuci.

Hlavní principy
1. Hlavní LLM jako centrální mozek
   - Uchovává kontext úlohy: zadání, záměr, mezikroky a uživatelské preference.
   - Pokud dokáže odpovědět přímo, odpoví jako klasický chatbot.
   - Pokud potřebuje vykonat tasky, vytvoří strukturovaný plán (JSON) a navrhne agenty pro každý krok.

2. Agenti vykonávají úlohy, neplánují
   - Každý agent má jasně definované schopnosti (např. run/task rozhraní).
   - Agenti pouze vykonávají přidělené úkoly (AgentCodeWriter, AgentImageGen, AgentScraper, …).
   - Nové agenty lze generovat dynamicky (AgentCodeWriter) a ihned upravit ve frontendovém editoru.

3. Planner LLM se učí nové agenty
   - Každý agent obsahuje metadata a popis schopností (např. `agent.yaml`).
   - Planner LLM se naučí využívat nového agenta přes metadata a krátké runtime testy.
   - Rozšiřování systému je konverzační: nový agent se objeví v Bolt.diy pro úpravy a ladění.

4. Bolt.diy jako frontend
   - UI pro zadávání záměrů, schvalování plánů a sledování průběhu.
   - Vizualizace diffů, náhledů a logů agentů v reálném čase.
   - Komponenta AgentOutputViewer zobrazuje výstupy konkrétních tasků a umožňuje editovat kód agentů.

5. Mcp-agent jako orchestrátor
   - Zpracovává spuštění tasků podle plánu (např. API `/api/run_agent`, `/api/plan`, `/v1/plan/stream`).
   - Obsahuje PlannerAgent (hlavní mozek) a AgentCodeWriter (generování dalších agentů).
   - Snadné rozšíření o testovací a CI/CD agenty.

Průběh workflow (zjednodušeně)
- Uživatel zadá záměr.
- Planner LLM analyzuje a vrátí strukturovaný plán (JSON).
- UI zobrazí plán ke schválení.
- Po schválení OWL orchestruje tasky pomocí dedikovaných agentů.
- Výstupy agentů jsou streamovány do UI; planner agreguje finální odpověď.

MVP (hackathon scope)
- Bolt.diy jako FE s AgentOutputViewer.
- OWL s PlannerAgent a AgentCodeWriter.
- Napojení frontend ↔ backend přes API (plánování, streamování exekuce).
- Jeden funkční agent a základní plánování úlohy.

Proč je to jiné?
- Fokus na záměr → výsledky (not tool-first).
- Chat-first plánování s node-based vizualizací a dynamickou tvorbou agentů.
- Open-source middleware kompatibilní s existujícími MCP nástroji.

Use-casy
- Rychlé prototypování AI nástrojů.
- Interní agentní systémy pro firmy.
- Asistent pro produktové týmy: „Zadej výsledek, AI udělá zbytek.“

Další kroky (doporučené)
- Přidat AgentImageGen a další specializované agenty.
- Definovat `agent.yaml` pro každý agent, aby se usnadnilo auto-učení Planneru.
- Přidat tutorial scénáře (např. „Vytvoř web s generovanými obrázky“).
- Připravit bezpečný sandbox / validační pipeline pro upload kódu agentů.

---
