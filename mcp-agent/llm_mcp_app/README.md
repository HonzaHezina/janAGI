# Bezpečnostní doporučení pro upload a spuštění kódu agentů

Tento dokument popisuje doporučené postupy pro bezpečné nahrávání, validaci a spouštění kódu agentů v janAGI / mcp-agent.

Základní principy
- Minimalizovat důvěru v uživatelský kód: nikdy nespouštět bez kontroly.
- Přetvořit nasazení na několik vrstev kontroly: statická analýza → CI testy → sandbox runtime.

Validace před uložením (server-side)
- Statická kontrola zdroje (AST): zakázat/nepovolit přímé volání funkcí jako eval, exec, __import__, importlib.
- Zakázané moduly: subprocess, socket, os.system, shutil.rmtree, multiprocessing, ctypes a podobné nízkoúrovňové API.
- Kontrola řetězců: detekovat obfuskované volání (např. getattr(__builtins__...)).
- Lint a bezpečnostní scan: spustit flake8 / bandit / mypy → chybové skóre blokuje upload.
- Testovací spouštění v CI: jednotkové testy a minimální smoke test spouštěné v izolovaném prostředí.

Bezpečný proces uploadu
- Upload přijmout do karantény (temp složka) a nikde nespouštět.
- Uložený kód podepsat/hashovat a uložit auditní záznam (kdo nahrál, kdy).
- Zobrazit diff v Bolt.diy a vyžadovat explicitní potvrzení uživatele a/nebo review před povolením execution.

Sandbox / runtime izolace
- Spouštět kód pouze v omezeném runtime:
  - Docker container s omezenými capabilities nebo gVisor/Firecracker pro silnější izolaci.
  - Omezení CPU / paměti / disk I/O / čas běhu.
  - Síťové restrikce: defaultně žádný egress; povolit jen explicitní whitelist.
  - Filesystem: namountovat readonly FS nebo jen specifické adresáře.
  - Použít Seccomp / AppArmor / SELinux profily kde dostupné.

Proces spouštění
- Spouštějte kód jako neprivilegovaný uživatel.
- Nastavte timeouty na procesu i na vláknu (např. 30s per task).
- Omezte velikost výstupu (stdout/stderr) a logujte všechny výstupy.
- Monitorujte resource usage a zabijte runaway procesy nebo nekonečné smyčky.

Bezpečnostní kontroly v CI
- Před automatickým nasazením spouštějte: bandit, dependency-audit (safety/OWASP), container-scan.
- Automatické testy ověří, že agent nevykonává zakázané akce a že smoke testy projdou.

Governance a audit
- Auditní záznamy: kdo nahrál, co se změnilo, kdo schválil.
- Revize změn: možnost rollbacku a revizního procesu (code owner review).
- Povolit sandboxed "dry-run" pro Planner/LLM testy bez plného spuštění.

Doporučené další kroky
- Implementovat server-side pipeline: AST -> lint -> unit smoke test -> containerized run.
- Přidat UI varování v Bolt.diy při editaci kódu (security risks).
- Definovat `agent.yaml` metadata, která omezí oprávnění (např. allow_network: false).
- Dokumentovat bezpečnostní politiky v projektu a v README modulů agentů.

Poznámka
- Toto jsou doporučení; nasazení do produkce vyžaduje bezpečnostní audit a právní posouzení podle vašeho provozního prostředí.