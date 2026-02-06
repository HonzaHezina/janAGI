# ADR-0001: Hybrid Ops + Analytics (n8n + pgvector + MindsDB)

## Status
Accepted

## Context
Potřebujeme:
- rychlou operativu (low latency, vizuální debug, human approval)
- analytiku nad historií (batch scoring, trendy, reporting)

## Decision
- Operativa zůstává v n8n + pgvector (RAG)
- MindsDB je oddělená analytická vrstva (batch), která zapisuje do `analytics.*`

## Consequences
+ Menší latence pro chat
+ Lepší observabilita v n8n
+ MindsDB přidává BI hodnotu bez rizika, že “spadne” operativa
- Další servis v stacku (RAM/ops)
