# Changes: fix-telegram-chats-missing-columns
**Date:** 2026-04-10T00:00:00+00:00
**Author:** Claude Code
**Sprint/Task:** Hotfix — /api/channels 500 error

## Affected Files
- `src/db/migrations/versions/0001_initial_schema.py` — added missing `last_avg_views` (Integer, nullable), `last_post_frequency` (Float, nullable), and `price_per_post` (Integer, nullable) columns to `telegram_chats` table definition
- Live DB — columns added directly via `ALTER TABLE telegram_chats ADD COLUMN ...`

## Business Logic Impact
`GET /api/channels` (owner channel list) was returning HTTP 500 for all users because SQLAlchemy ORM emitted a SELECT that referenced `telegram_chats.last_avg_views`, `last_post_frequency`, and `price_per_post` — columns present in the model but absent from the DB schema. The endpoint is now functional.

## API / FSM / DB Contracts
- **DB schema change**: `telegram_chats` table gains three nullable columns:
  - `last_avg_views INTEGER NULL`
  - `last_post_frequency DOUBLE PRECISION NULL`
  - `price_per_post INTEGER NULL`
- No API contract change (columns were already in the ORM model / serialization schema).

## Migration Notes
`0001_initial_schema.py` patched directly (pre-production rule — no new revision).
Live DB was updated via:
```sql
ALTER TABLE telegram_chats ADD COLUMN price_per_post INTEGER;
```
(The other two columns were applied by dropping/recreating the schema and re-running `alembic upgrade head`.)

---
🔍 Verified against: f423788 | 📅 Updated: 2026-04-10T00:00:00+00:00
