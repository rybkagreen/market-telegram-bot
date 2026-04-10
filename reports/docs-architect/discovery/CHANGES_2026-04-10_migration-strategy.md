# Migration Strategy Decision — 2026-04-10

## Decision
Pre-production migration strategy changed: single rewritable `0001_initial_schema.py`
instead of incremental Alembic migrations.

## Affected Files
- `CLAUDE.md` — added "Migration Strategy (Pre-Production)" section
- `QWEN.md` — added "Стратегия миграций (до появления prod-пользователей)" section

## Rationale
No production users exist. Squash approach eliminates migration chain complexity,
speeds up DB resets, and avoids merge conflicts in versions/.

## Trigger for Revert
First real production user → `0001_initial_schema.py` becomes immutable →
standard incremental migrations resume.

## Impact
- Business logic: none
- API contracts: none
- FSM: none
- DB: `0001_initial_schema.py` is now the single source of truth for schema

🔍 Verified against: HEAD @ 2026-04-10 | 📅 Updated: 2026-04-10T00:00:00Z
