# Spec Kit autopilot: OpenClaw (gatekeeper) + CLI implementers (end-to-end)

Tenhle dokument popisuje přesně to flow, které chceš:

- **OpenClaw** s tebou vede krátkou debatu a uzamkne zadání (Definition of Done).
- OpenClaw udělá **repo bootstrap** a **Spec Kit bootstrap**.
- **CLI implementer(ři)** pak udělají **veškerou tvorbu artefaktů Spec Kitu + kód + testy + fix-loop**.

Cíl: držet se filozofie Spec Kitu (proces + artefakty), ale být autonomní a auditovatelný.

---

## Mentální model (definitivně)

- **Spec Kit = autorita procesu** (pořadí a očekávané artefakty)
- **CLI nástroje = jediné bytosti, které generují** constitution/spec/plan/tasks/kód
- **OpenClaw = gatekeeper/orchestrátor/porotce** (ne developer)

---

## Rozdělení rolí

### OpenClaw dělá jen 4 věci

1) **Refine & Lock**: položí max 2–5 krátkých otázek, nabídne defaulty, uzamkne DoD.
2) **Bootstrap repa**: založí repo/branche a připraví workspace.
3) **Bootstrap Spec Kitu**: spustí `specify init` (mechanika scaffoldingu) a udělá první commit.
4) **Orchestrace + převzetí**: spustí CLI implementera(y), vyhodnotí testy/CI, vybere vítěze, otevře PR, spustí fix-loop.

### CLI implementer dělá všechno ostatní

- generuje Spec Kit artefakty: **constitution → specify → plan → tasks**
- implementuje kód + testy
- commit po krocích
- spouští lint/test/build/smoke
- opravuje do zelené (max N iterací)

---

## Spec Kit sekvence (nesmí se měnit pořadí)

CLI implementer běží v pořadí:

- `constitution`
- `specify`
- `plan`
- `tasks`
- `implement`

OpenClaw jen hlídá, že se nic nepřeskočilo.

---

## Doporučený Git flow pro autonomii

- `base/spec-kit` – výsledek `specify init` + první commit se skeletonem
- `impl/gemini` / `impl/copilot` – implementace od implementerů
- PR `impl/*` → `main`

---

## Dvoufázový protokol: REFINE → EXECUTE

### Fáze 1: REFINE (jen dialog)

OpenClaw se ptá jen na to, co je potřeba, aby později šlo korektně vytvořit constitution/spec/plan/tasks a dotáhnout implement.

**Výstup**: `locked.json` (mimo repo) se stabilními vstupy.

### Fáze 2: EXECUTE (autopilot)

OpenClaw udělá repo + Spec Kit bootstrap + zavolá CLI implementery. Sám nic „nevymýšlí do kódu“.

**Výstup**: PR URL + winner branch + shrnutí.

---

## Co se OpenClaw ptá v REFINE (Spec-Kit-aware checklist)

Minimum (typicky 6–10 otázek):

- Repo: `app_name`, `visibility`, (implicitní) `owner`
- Template/stack: `fastapi | nextjs | fullstack`
- Product scope: 1–3 věty co to dělá + kdo je uživatel
- Acceptance criteria: 3–7 bodů „hotovo když…“
- Non-goals: co teď určitě nedělat
- Constitution constraints: testy povinné? lint? minimal deps? bezpečnost (žádné secrety v git)?
- DoD validační příkazy: konkrétní `lint/test/build/smoke` (OpenClaw navrhne defaulty dle template)

---

## Formát `locked.json` (doporučený)

```json
{
  "repo": {"owner":"<GITHUB_OWNER>","name":"<app_name>","visibility":"private"},
  "primary": "both",
  "template": "fastapi",
  "project_intent": "...",
  "definition_of_done": ["..."],
  "acceptance_criteria": ["..."],
  "non_goals": ["..."],
  "validation_commands": ["ruff check .","pytest -q"]
}
```

---

## Kontrakt: OpenClaw Dispatcher (paste-ready)

Použij jako systémové instrukce pro OpenClaw (v EXECUTE módu).

```text
ROLE
Jsi OpenClaw Dispatcher. Jsi gatekeeper + orchestrátor Spec Kit flow. Neimplementuješ kód ani Spec Kit artefakty.

DEFAULTY
primary=both, visibility=private, template=fastapi.
Polož max 2–5 krátkých otázek. Pak pokračuj s defaulty.

KROKY (musí být dodrženy)
1) REFINE & LOCK
- Vytvoř locked.json: Project Intent, DoD, Non-goals, Validation Commands, repo params.

2) Repo & workspace
- Založ GitHub repo, naklonuj do workspace.

3) Bootstrap Spec Kit (jen mechanika)
- Spusť: specify init --here --ai <bootstrap_ai>
- Commitni do base/spec-kit a pushni.

4) Branches
- Vytvoř impl/gemini a/nebo impl/copilot z base/spec-kit, push.

5) Spusť CLI implementery
- Implementer musí provést: constitution → specify → plan → tasks → implement.
- Ty mu jen předáš locked.json (DoD + intent) a požadavky na small commits + test/fix loop (max 5 iterací).

6) Vyhodnocení a vítěz
- Ověř validation_commands na obou branchech.
- Vyber vítěze; pokud nic neprojde, spusť fix-loop.

7) PR
- Zajisti main (pokud chybí, vytvoř z base/spec-kit).
- Otevři PR winner → main.

OUTPUT
Na konci vrať 1-line JSON: {repo_url, winner_branch, pr_url, status, run_id}.
```

---

## Kontrakt: CLI Implementer (paste-ready)

```text
ROLE
Jsi CLI Implementer. Děláš end-to-end Spec Kit flow a implementaci. Generuješ Spec Kit artefakty i kód.

NEJPRVE
Přečti locked.json (Definition of Done). Pokud je něco nejasné, polož 1 otázku, jinak pokračuj.

POVINNÁ SEKQUENCE
constitution → specify → plan → tasks → implement (pořadí neměnit).

PRAVIDLA
- Small commits, smysluplné commit messages.
- Po každé vlně změn spusť validation commands.

TEST/FIX LOOP
- Když něco failne: diagnostic summary (What failed / Most likely cause / Fix plan), oprav, retest.
- Max N=5 iterací, pak eskaluj s logy a návrhem rozhodnutí.

VÝSTUP
- Repo „green“ podle DoD.
- README: jak spustit a jak otestovat.
- Spec Kit artefakty tracked v gitu.
```

---

## Jak to napojit v n8n (minimálně)

Doporučené jsou 2 workflowy:

- `REFINE`: Webhook → OpenClaw `/v1/responses` → uložit otázky/locked.json → odpovědět uživateli
- `EXECUTE`: Webhook → OpenClaw `/v1/responses` → uložit logy → odpovědět výsledkem

Pro OpenClaw HTTP integraci viz [ops/docs/OPENCLAW_TURBO.md](OPENCLAW_TURBO.md).
