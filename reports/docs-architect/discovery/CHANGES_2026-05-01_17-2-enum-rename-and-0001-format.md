# CHANGES — 17.2 Commit 2: enum rename + 0001 format + redundant meta literal drop

**Date:** 2026-05-01
**Branch:** feat/17-2-clean-sweep-persisted-credits
**Series:** 17.x (BL-053 umbrella)
**Closes:** Category B + E of 17.2 (per `PHASE_17_2_RESEARCH_2026-05-01.md`).

## Summary

Rename two `transactiontype` Postgres ENUM values to single-currency-RUB-aligned names; drop a fully-redundant `meta_json["type"]` string literal alongside the typed enum column; clear the `0001` formatting drift deferred from 17.1. Pre-prod policy applied: direct edit of inline `sa.Enum(...)` in `0001_initial_schema.py`, DB drop+recreate executed locally.

## Changes

| Old | New | Sites |
|---|---|---|
| Enum value `credits_buy` | `plan_purchase` | `transaction.py:34`, `0001:891`, `billing.py:488` (`_VISIBLE_TX_TYPES`), `bot/handlers/billing/billing.py:275` (`TransactionType.credits_buy` ref) |
| Enum value `admin_credit` | `admin_grant` | `transaction.py:45`, `0001:899`, `analytics.py:251` (`_INCOME_TX_TYPES`), `billing_service.py:985` (`TransactionType.admin_credit` ref) |
| `meta_json["type"] = "admin_credit"` redundant literal | **deleted** | `billing_service.py:991` (line removed; typed `Transaction.type` enum column carries the same info) |
| `0001_initial_schema.py` format drift | clean | bundled `ruff format` pass on the same file |

## Rationale

- `credits_buy` → `plan_purchase`: the value tags Transactions created when a user purchases a tariff/subscription plan via balance debit (`bot/handlers/billing/billing.py:275`). The legacy name lied — it never represented "credits as currency" post-migration. `plan_purchase` matches the existing internal `meta_json["type"] = "plan_purchase"` discriminator at `billing_service.py:269` (already present pre-17.2 in `activate_plan`).
- `admin_credit` → `admin_grant`: the value tags Transactions created when admin transfers from `PlatformAccount.profit_accumulated` → `user.balance_rub` (`billing_service.py admin_credit_from_platform`). `grant` better captures "platform-funded admin transfer" without "credit" ambiguity.
- Redundant `meta_json["type"]` drop: typed `Transaction.type: TransactionType` already carries this info — meta dict copy was a zero-consumer artifact (verified: `grep "meta_json\\[.type.\\]"` in `src/` returned 0 read sites).

## Files touched

- `src/db/models/transaction.py` — 2 enum decls.
- `src/db/migrations/versions/0001_initial_schema.py` — 2 enum literals inside inline `sa.Enum(...)` + format pass (78 insertions, 15 deletions per `git diff --stat` — content edits + reformat).
- `src/api/routers/billing.py` — 1 string literal in `_VISIBLE_TX_TYPES`.
- `src/api/routers/analytics.py` — 1 string literal in `_INCOME_TX_TYPES`.
- `src/bot/handlers/billing/billing.py` — 1 `TransactionType.*` ref.
- `src/core/services/billing_service.py` — 1 `TransactionType.*` ref + 1 redundant meta_json literal removed.

## DB verification (executed locally)

```
docker compose exec postgres psql -U market_bot -d postgres -c "DROP DATABASE IF EXISTS market_bot_db WITH (FORCE)" -c "CREATE DATABASE market_bot_db OWNER market_bot"
docker compose exec api poetry run alembic -c alembic.ini upgrade head
docker compose exec postgres psql -U market_bot -d market_bot_db -c "SELECT enumlabel FROM pg_enum WHERE enumtypid = 'transactiontype'::regtype ORDER BY enumsortorder;"
```

Final enum DB state: 20 values; `plan_purchase` at order 11 (replaces `credits_buy`), `admin_grant` at order 19 (replaces `admin_credit`); old values absent.

## Verification

- `grep '"credits_buy"\|"admin_credit"\|TransactionType\.credits_buy\|TransactionType\.admin_credit'` against `src/` → 0 matches.
- `grep '"plan_purchase"\|"admin_grant"\|TransactionType\.plan_purchase\|TransactionType\.admin_grant'` against `src/` → 6 matches (decls + 4 references + 2 pre-existing internal `meta_json` discriminator strings).
- `poetry run ruff format --check src/db/migrations/versions/0001_initial_schema.py` → clean.
- DB `pg_enum` sweep confirms only new values present.

## Pre-existing drift surfaced (NOT introduced by 17.2)

`alembic check` reports drift on `placement_status_history.ix_psh_placement_changed` index:
- Migration `e6a88faa9fa0:71`: `["placement_id", sa.text("changed_at DESC")]`.
- Model `placement_status_history.py:69`: plain `"changed_at"` (no DESC).

Drift is between migration (descending) and model (default ASC) on an artifact entirely unrelated to 17.2. Not introduced by this commit. No `transactiontype` enum drift detected — enum changes are in sync between model and DB.

## Out of scope (deferred)

- Pydantic schema `PlatformCreditRequest` + handler `create_platform_credit` rename → Commit 3.
- URL paths `/credits/...` → 17.3.
- Local var `tx_type` in `billing.py`/`analytics.py` → cosmetic, skipped per Marina decision.
- `placement_status_history` index drift (above) → unrelated, surface for separate cleanup.

## Baseline impact

Internal enum/identifier rename only; no public API contract change (URLs unchanged, OpenAPI operation_ids unchanged). CHANGELOG.md not updated.

🔍 Verified against: HEAD prior to commit (post-Commit-1 = `7715ef6`) | 📅 Updated: 2026-05-01T00:00:00Z
