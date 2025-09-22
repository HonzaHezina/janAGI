## janAGI — Open-source AI Agent Orchestration Framework

Cílem tohoto souboru je uchovávat současnou myšlenku a implementaci systému: jak se používá, jak nastavit LLM a jak rozšiřovat agenty.

mcp-agent — stručný popis fungování

Architektura: centrální orchestrace + sada per‑agent modulů. Orchestrace rozhoduje, zda odpovědět přímo nebo vytvořit a spustit plán agentů. Viz [`mcp-agent/llm_mcp_app/orchestration.py:104`](mcp-agent/llm_mcp_app/orchestration.py:104).

Agenti: každý agent má adresář s `agent.yaml` (meta: model, provider, prompt_template, permissions) a `main.py` implementující `get_agent(agent_config)` + veřejné funkce. Příklad CodeWriter: [`mcp-agent/agents/codewriter/agent.yaml:1`](mcp-agent/agents/codewriter/agent.yaml:1) a [`mcp-agent/agents/codewriter/main.py:65`](mcp-agent/agents/codewriter/main.py:65).

AgentRunner: složí prompt z `prompt_template` + runtime task, vybere provider a zavolá ho; vrací normalizovaný výsledek. Viz [`mcp-agent/llm_mcp_app/agent_runner.py:11`](mcp-agent/llm_mcp_app/agent_runner.py:11).

Providers: factory `get_provider(model, provider_override)` mapuje model na implementaci (OpenAI, HuggingFace, Gemini, Mistral). Implementace Mistral pro "codestral" byla přidána. Viz [`mcp-agent/llm_mcp_app/providers.py:405`](mcp-agent/llm_mcp_app/providers.py:405).

Orchestrace → plán: assistant má vrátit strojově čitelný JSON (`{"direct_answer":...}` nebo `{"plan":[...]}`); plán se zobrazí uživateli pro potvrzení a následné spuštění kroků (`execute_plan` / `execute_plan_stream`). Viz [`mcp-agent/llm_mcp_app/orchestration.py:139`](mcp-agent/llm_mcp_app/orchestration.py:139) a [`mcp-agent/llm_mcp_app/orchestration.py:351`](mcp-agent/llm_mcp_app/orchestration.py:351).

Různé utility: `show_agent` handler vrací strukturovaný payload s klíčem `show_agent` (jádro pro front‑end zobrazení kódu). Viz [`mcp-agent/llm_mcp_app/orchestration.py:502`](mcp-agent/llm_mcp_app/orchestration.py:502).

bolt.diy — co dělá front‑end

Chat UI: zobrazuje zprávy, markdown a artefakty (kód, obrázky, diffy) přes komponenty které umí vykreslit strukturovaný obsah LLM‑odpovědí. Hlavní render v Markdown/Artifact komponentách: [`bolt.diy/app/components/chat/Markdown.tsx:109`](bolt.diy/app/components/chat/Markdown.tsx:109) a [`bolt.diy/app/components/chat/Artifact.tsx:164`](bolt.diy/app/components/chat/Artifact.tsx:164).

Code viewer: speciální CodeBlock komponenta pro zobrazení zdrojového kódu s kopírováním a zvýrazněním: [`bolt.diy/app/components/chat/CodeBlock.tsx:18`](bolt.diy/app/components/chat/CodeBlock.tsx:18).

Integrace se serverem: když orchestrace pošle assistant content obsahující např. `{"show_agent": {...}}`, front‑end rozpozná payload a otevře zabudovaný code viewer / file panel bez dalších úprav UI. Viz orchestrace → payload: [`mcp-agent/llm_mcp_app/orchestration.py:502`](mcp-agent/llm_mcp_app/orchestration.py:502) a front‑end renderer: [`bolt.diy/app/components/chat/Markdown.tsx:109`](bolt.diy/app/components/chat/Markdown.tsx:109).

Streaming: SSE / OpenAI‑like streamy z backendu jsou spotřebovány v UI jako inkrementální zprávy; front‑end komponenty podporují postupné vykreslování chunků.

Stručný přehled

janAGI se soustředí na záměr → plán → exekuci. Uživatel zadá záměr a systém:
- rozhodne, zda odpovědět přímo (central LLM)
- nebo vygeneruje strukturovaný plán (JSON) s kroky a agenty
- po schválení spustí plán a streamuje výsledky do UI

Hlavní komponenty
- mcp-agent (orchestrátor + planner)
- Agenti (adresáře v `mcp-agent/agents/`)
- Providers (get_provider: OpenAI, HuggingFace, Gemini, Mistral, Dummy)
- bolt.diy (frontend: chat, code viewer, artifact viewer)

Jak systém funguje (podrobněji)
1) Uživatelský záměr: uživatel zadá záměr ve frontendu.
2) Decision: orchestrátor (central LLM) vytvoří rozhodnutí — buď `{"direct_answer":...}` nebo `{"plan":[...]}`.
3) Zobrazení plánu: plan se zobrazí ve frontendu ke schválení (UI používá strukturovaný JSON).
4) Exekuce: po schválení `execute_plan` spouští kroky; pro každý krok zavolá příslušného agenta.
5) Stream & agregace: výsledky se streamují do UI; orchestrátor může agregovat finální odpověď.

Nastavení LLM
- Hlavní LLM (Planner / Orchestrátor)
  - Konfigurováno v [`mcp-agent/llm_mcp_app/config.py:11`](mcp-agent/llm_mcp_app/config.py:11) proměnnou LLM_PROVIDER a DEFAULT_MODELS.
  - Orchestrace používá `get_provider(DEFAULT_MODELS[LLM_PROVIDER])` pro plánování a rozhodování.
- Per‑agent LLM
  - Každý agent má `agent.yaml` s klíči: model, provider, prompt_template, permissions, timeout.
  - Příklad: [`mcp-agent/agents/codewriter/agent.yaml:1`](mcp-agent/agents/codewriter/agent.yaml:1)
  - Loader načte `agent.yaml` a předá `agent_config` do `get_agent(agent_config=...)`.
  - `AgentRunner` zpracuje `prompt_template` a zavolá provider specifikovaný v `agent_config`.
  - Pokud `agent.yaml` uvádí `provider: mistral` a `model: codestral`, `AgentRunner` použije `MistralProvider` pro tohoto agenta.

Interní toky a formáty
- Decision výstup: assistant vrací validní JSON (`{"direct_answer": "..."} nebo {"plan":[...]}`).
- Plan krok: `{ "step": n, "description": "...", "agent": "codewriter", "arguments": {...} }`.
- Show‑agent: orchestrace vrací assistant message s obsahem JSON `{"show_agent": {"name": "...", "files": {...}}}` pro frontend.

Jak přidat nebo upravit agenta
1) Vytvoř složku `mcp-agent/agents/<agent_name>/`
2) Přidej `agent.yaml` s metadata (model, provider, prompt_template, permissions, timeout).
3) Implementuj `main.py` s funkcí `get_agent(agent_config)` vracející Agent objekt a veřejnou funkci (např. generate_*).
4) Doporučeno: použít stejný pattern jako v [`mcp-agent/agents/codewriter/main.py:65`](mcp-agent/agents/codewriter/main.py:65) — podporuje `agent_config` a fallback.

Bezpečnost a validace
- Před načtením nového agenta proveď AST analýzu zdrojů, whitelist/banned modulů a zkontroluj permissions.
- Neprovádějte nerestriktivní importy dynamicky bez validace.
- AgentCreator má mít ochranu proti přepsání souborů a validaci specu.

Testování a vývoj
- Lokální smoke test agenta: (PYTHONPATH include `mcp-agent/src`)
  - Windows: `set PYTHONPATH=./mcp-agent/src && python mcp-agent/agents/codewriter/main.py`
  - Unix: `PYTHONPATH=./mcp-agent/src python mcp-agent/agents/codewriter/main.py`
- Pro `show_agent`: pošli do orchestrace text "zobraz mi kod agenta <name>".

Doporučené další kroky (prioritně)
1. Implementovat bezpečnostní validační pipeline (AST checks, banned modules).
2. Dokončit a zabezpečit `MistralProvider` pro production (env klíče).
3. Přidat `TESTING.md` s API příklady, SSE a end‑to‑end scénáři.
4. Přidat automatizované smoke a integrační testy pro orchestrace a per‑agent volání.

Poznámka pro údržbu
Tento `readme.md` slouží jako hlavní dokument a "single source of truth" pro myšlenku a implementaci. Udržujte jej aktuální při změnách architektury nebo chování agentů.

---