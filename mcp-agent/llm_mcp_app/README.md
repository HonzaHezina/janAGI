# Správa agentů — stručný návod a kontrakty

Tento soubor popisuje, jak `mcp-agent/llm_mcp_app` načítá a používá agenty, a dává doporučení pro formát metadat (`agent.yaml`) tak, aby loader a orchestrace fungovaly konzistentně.

Krátké shrnutí role modulů
- [`agents.py`](mcp-agent/llm_mcp_app/agents.py:1) — dynamické načítání agentů z adresáře `mcp-agent/agents`.
- [`agent_runner.py`](mcp-agent/llm_mcp_app/agent_runner.py:1) — per-agent runner, skládá prompt z `agent_config` a volá provider.
- [`planner.py`](mcp-agent/llm_mcp_app/planner.py:1) — utilitky pro rozhodování (extrakce JSON, validace plánu, převod do textu, tvorba promptu a preview).
- [`orchestration.py`](mcp-agent/llm_mcp_app/orchestration.py:1) — vykonávací logika a streaming executor.
- [`providers.py`](mcp-agent/llm_mcp_app/providers.py:1) — implementace LLM providerů a fallback `DummyProvider`.
- [`main.py`](mcp-agent/llm_mcp_app/main.py:1) — FastAPI aplikace a veřejné endpointy.
- [`models.py`](mcp-agent/llm_mcp_app/models.py:1) — pydantic modely (Message, ChatCompletionRequest).

Kontrakty, které loader a orchestrace očekávají
- Každý agent se nachází v `mcp-agent/agents/{agent_name}` a musí mít `main.py`.
- V `main.py` musí být funkce `get_agent(agent_config: Optional[dict] = None) -> Agent`.
- Vrácený `Agent` musí mít alespoň atribut `functions` (seznam volatelných callables). Orchestrace volá `agent.functions[0]`.
- Loader předá do `get_agent` slovník `agent_config`, pokud existuje `agent.yaml`. Loader provádí jednoduchou normalizaci polí (např. `prompt` → `prompt_template`, doplní `model` defaultem).

Doporučené schéma `agent.yaml`
- `agent.yaml` je volitelný, ale pokud je přítomen, měl by obsahovat tato pole. Níže ukázka a stručný význam:

```yaml
# language: yaml
name: finder                 # slug agenta (adresářový název)
description: "Najde soubory dle dotazu"
model: gpt-4                 # volitelné; loader doplní DEFAULT_MODEL pokud chybí
provider: openai             # volitelně: 'openai', 'huggingface', 'gemini', 'mistral', ...
prompt_template: |           # template použitý AgentRunnerem; must contain placeholder např. {{task}}
  Najdi soubory odpovídající: {{task}}
timeout: 30                  # sekund, fallback 30
permissions: []              # metadata pro budoucí bezpečnostní politiku
entrypoint: main.py          # volitelně; default 'main.py'
```

Poznámky ke kompatibilitě
- Loader v [`mcp-agent/llm_mcp_app/agents.py`](mcp-agent/llm_mcp_app/agents.py:1) načítá `agent.yaml` pokud je dostupné a předává `agent_config` do `get_agent(...)`. Pokud `agent_config` obsahuje staré aliasy (např. `prompt`), loader je automaticky normalizuje na `prompt_template`.
- Pokud `agent.yaml` neobsahuje `model`, loader doplní `DEFAULT_MODEL` z konfigurace (`mcp-agent/llm_mcp_app/config.py`).
- Orchestrace očekává, že agent implementuje jednoduché volání `agent.functions[0](**arguments)` nebo `await` pokud jde o coroutine. Agenti v [`mcp-agent/agents`](mcp-agent/agents/codewriter/main.py:1) dodržují tento vzor.

Bezpečnost a provoz
- Tento FastAPI modul je zamýšlený jako administrátorské rozhraní. V produkci je doporučeno:
  - Omezit přístup k endpointům upravujícím agenty pouze pro adminy.
  - Spouštění uživatelského kódu provádět v sandboxu (pokud chcete povolit uživatelské nahrávání).
  - V README v rootu projektu jsou další bezpečnostní doporučení (viz `mcp-agent/llm_mcp_app/README.md` ve vyšší úrovni projektu).

Doporučené kroky a testy
- Přidat unit testy pro [`planner.py`](mcp-agent/llm_mcp_app/planner.py:1) a pro loader (`agents.py`) kontrolující, že `agent_config` se předává a normalizuje.
- Přidat příklad `agent.yaml` do `_examples` nebo do jednotlivých agent adresářů pro rychlou referenci.

Konec.