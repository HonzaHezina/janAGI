# Refaktoring: Přesun load_all_agents do llm_mcp_app

## ✅ Změny provedeny:

### 1. **Přesun kódu z utils/ do llm_mcp_app/main.py**
- Funkce `load_all_agents()` je teď přímo v `main.py`
- Eliminovány externí závislosti na `utils` adresář
- Zjednodušená struktura projektu

### 2. **Vyčištění importů**
- Odstraněn import `from utils.load_all_agents import load_all_agents`
- Přidány potřebné importy: `importlib.util`, `ast`, `pathlib.Path`
- Vyčištěn duplicitní import `ast` uvnitř funkcí

### 3. **Odstranění utils/ adresáře**
- Smazán adresář `utils/` včetně `load_all_agents.py`
- Smazán `__pycache__` adresář

### 4. **Aktualizace testovacích skriptů**
- Aktualizován `check_agents.py` pro použití nového importu
- Testovací skripty fungují se zjednodušenou strukturou

## ✅ Struktura po refaktoringu:

```
mcp-agent/
├── llm_mcp_app/
│   ├── main.py          # Obsahuje load_all_agents() + veškerou logiku
│   └── requirements.txt
├── agents/
│   ├── codewriter/
│   ├── finder/
│   ├── html_parser/
│   └── image_generator/
├── check_agents.py      # Aktualizovaný testovací skript
├── test_orchestration.py
└── test_boltdiy.py
```

## ✅ Výhody refaktoringu:

1. **Jednodušší struktura** - méně adresářů a souborů
2. **Méně závislostí** - vše je v jednom hlavním souboru
3. **Snadnější údržba** - agent loading logika je přímo tam, kde se používá
4. **Lepší enkapsulace** - funkčnost je seskupená logicky

## ✅ Testování:

```bash
cd C:\Users\janhe\projekty\janAGI\mcp-agent

# Test načítání agentů
python -c "from llm_mcp_app.main import load_all_agents; print(load_all_agents('agents').keys())"

# Test celého serveru
python check_agents.py

# Spuštění serveru
python -m llm_mcp_app.main
```

Všechny funkce zůstávají nezměněné, pouze byla zjednodušena struktura projektu!
