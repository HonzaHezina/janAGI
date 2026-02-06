# RAG (Memory design)

Kanonická DB implementace je v `rag.*` (viz [ops/infra/postgres/init/020_rag_schema.sql](ops/infra/postgres/init/020_rag_schema.sql)).

## 3 paměti
1) **Statická**: expert_knowledge (kniha, články, certifikace, FAQ)
2) **Dynamická**: history (každá zpráva)
3) **Procedurální**: sop (pravidla komunikace, tone, zakázaná slova, CTA)

## Proč ukládat každou zprávu
- kontinuita (AI navazuje)
- personalizace (rozpočet, preference)
- robustní retrieval (najde přesně ten detail)

## Optimalizace později
- TTL (např. 180 dní)
- session summaries (každých N zpráv)
- “pin” důležitých faktů do SOP/notes

