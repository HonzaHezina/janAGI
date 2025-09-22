## janAGI — Open-source AI Agent Orchestration Framework

Cílem tohoto souboru je uchovávat současnou myšlenku a implementaci systému: jak se používá, jak nastavit LLM a jak rozšiřovat agenty.

Stručný přehled
janAGI se soustředí na záměr → plán → exekuci. Uživatel zadá záměr a systém:
- rozhodne, zda odpovědět přímo (central LLM)
- nebo vygeneruje strukturovaný plán (JSON) s kroky a agenty
- po schválení spustí plán a streamuje výsledky do UI

Hlavní komponenty
- mcp-agent (orchestrátor + planner)
- Agenti (adresáře v mcp-agent/agents/)
- Providers (get_provider: OpenAI, HuggingFace, Gemini, Mistral, Dummy)
- bolt.diy (frontend: chat, code viewer, artifact viewer)

Jak systém funguje (podrobněji)
1) Uživatelský záměr: uživatel zadá záměr ve frontendu.
2) Decision: orchestrátor (central LLM) vytvoří rozhodnutí — buď {"direct_answer":...} nebo {"plan":[...]}.
3) Zobrazení plánu: plan se zobrazí ve frontendu ke schválení (UI používá strukturovaný JSON).
4) Exekuce: po schválení execute_plan spouští kroky; pro každý krok zavolá příslušného agenta.
5) Stream & agregace: výsledky se streamují do UI; orchestrátor může agregovat finální odpověď.

Nastavení LLM
- Hlavní LLM (Planner / Orchestrátor)
  - Konfigurováno v [`mcp-agent/llm_mcp_app/config.py`](mcp-agent/llm_mcp_app/config.py:11) proměnnou LLM_PROVIDER a DEFAULT_MODELS.
  - Orchestrace používá get_provider(DEFAULT_MODELS[LLM_PROVIDER]) pro plánování a rozhodování.
- Per‑agent LLM
  - Každý agent má `agent.yaml` s klíči: model, provider, prompt_template, permissions, timeout.
  - Příklad: [`mcp-agent/agents/codewriter/agent.yaml`](mcp-agent/agents/codewriter/agent.yaml:1)
  - Loader načte agent.yaml a předá agent_config do `get_agent(agent_config=...)`.
  - AgentRunner zpracuje prompt_template a zavolá provider specifikovaný v agent_config.
  - Pokud agent.yaml uvádí provider: mistral a model: codestral, AgentRunner použije `MistralProvider` pro tohoto agenta.

Interní toky a formáty
- Decision výstup: assistant vrací validní JSON ({"direct_answer": "..."} nebo {"plan":[...]}).
- Plan krok: { "step": n, "description": "...", "agent": "codewriter", "arguments": {...} }.
- Show‑agent: orchestrace vrací assistant message s obsahem JSON {"show_agent": {"name": "...", "files": {...}}} pro frontend.

Jak přidat nebo upravit agenta
1) Vytvoř složku `mcp-agent/agents/<agent_name>/`
2) Přidej `agent.yaml` s metadata (model, provider, prompt_template, permissions, timeout).
3) Implementuj `main.py` s funkcí `get_agent(agent_config)` vracející Agent objekt a veřejnou funkci (např. generate_*).
4) Doporučeno: použít stejný pattern jako v [`mcp-agent/agents/codewriter/main.py`](mcp-agent/agents/codewriter/main.py:65) — podporuje agent_config a fallback.

Bezpečnost a validace
- Před načtením nového agenta proveď AST analýzu zdrojů, whitelist/banned modulů a zkontroluj permissions.
- Neprovádějte nerestriktivní importy dynamicky bez validace.
- AgentCreator má mít ochranu proti přepsání souborů a validaci specu.

Testování a vývoj
- Lokální smoke test agenta: (PYTHONPATH include `mcp-agent/src`)
  - Windows: set PYTHONPATH=./mcp-agent/src && python mcp-agent/agents/codewriter/main.py
  - Unix: PYTHONPATH=./mcp-agent/src python mcp-agent/agents/codewriter/main.py
- Pro show_agent: pošli do orchestrace text "zobraz mi kod agenta <name>".

Doporučené další kroky (prioritně)
1. Implementovat bezpečnostní validační pipeline (AST checks, banned modules).
2. Dokončit a zabezpečit MistralProvider pro production (env klíče).
3. Přidat TESTING.md s API příklady, SSE a end‑to‑end scénáři.
4. Přidat automatizované smoke a integrační testy pro orchestrace a per‑agent volání.

Poznámka pro údržbu
Tento `readme.md` slouží jako hlavní dokument a "single source of truth" pro myšlenku a implementaci. Udržujte jej aktuální při změnách architektury nebo chování agentů.

---