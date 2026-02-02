# Contributing

Díky za zájem přispět.

## Pravidla
- Všechno musí být **multi-tenant** (vždy filtrovat `client_id`).
- Každý krok workflow musí být **idempotentní** (repeat-safe).
- Vše logovat do `events` s `trace_id`.
- Žádné hardcoded secrets. Používej `.env`/Coolify secrets.

## Struktura změn
- Dokumentace do `docs/`
- DB změny jako nové soubory do `infra/postgres/init/` (nepřepisovat staré)
- n8n workflow exporty do `n8n/workflows/`

## Styl commitů
- `feat: ...`
- `fix: ...`
- `docs: ...`
- `chore: ...`
