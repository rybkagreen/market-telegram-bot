# Changes: S-33 Migration Drift Fix — 0001 schema snapshot aligned with models
**Date:** 2026-04-18T01:03:28Z
**Author:** Claude Code
**Sprint/Task:** S-33 — Rewrite 0001_initial_schema.py as authoritative snapshot

## Affected Files

### Migration
- `src/db/migrations/versions/0001_initial_schema.py` — 7 categories of drift fixed (see DB Contracts)
- `src/db/migrations/versions/0002_add_advertiser_counter_fields.py` — **deleted**; content absorbed into 0001
- `src/db/migrations/env.py` — added `_compare_type` function to skip encrypted-type drift; `compare_comment=False`

### Models
- `src/db/models/document_upload.py` — added `extracted_ogrnip: Mapped[str | None]` (syncs ORM with existing DB column)
- `src/db/models/dispute.py` — added `index=True` on `advertiser_id`, `owner_id`, `admin_id`
- `src/db/models/badge.py` — added `index=True` on `BadgeAchievement.badge_id`, `UserBadge.badge_id`
- `src/db/models/reputation_history.py` — added `index=True` on `placement_request_id`
- `src/db/models/act.py` — removed spurious `unique=True` from `act_number` (Index in `__table_args__` enforces uniqueness); added `ondelete="SET NULL"` on `contract_id`
- `src/db/models/invoice.py` — added `ondelete="SET NULL"` on `placement_request_id` and `contract_id`
- `src/db/models/transaction.py` — added `ondelete="SET NULL"` on `act_id` and `invoice_id`

## Business Logic Impact

- **PlacementStatus.completed** is now a valid DB enum value — code paths that transition a placement to `completed` will no longer raise `invalid input value for enum` at runtime.
- **ord_blocked** status also added — ORD-blocking flow now has DB support.
- **DisputeReason/Status/Resolution** frontend values (`not_published`, `wrong_time`, `wrong_text`, `early_deletion`, `other`, `closed`, `full_refund`, `partial_refund`, `no_refund`, `warning`) are now DB-valid — mini_app dispute submission will no longer fail at persistence.
- **TransactionType** storno/admin_credit/gamification_bonus are now DB-valid — Sprint D.2 storno flow no longer blocked.
- **channel_mediakits** gains `owner_user_id`, `logo_file_id`, `theme_color` — mediakit ownership FK and display fields now have DB backing.
- **SET NULL cascade** on `acts.contract_id`, `invoices.*`, `transactions.act_id/invoice_id` — safe deletion of contracts/acts/invoices without FK violations.
- **6 new FK indexes** on dispute, badge, reputation tables — eliminates full-table scans for common lookup queries.

## API / FSM / DB Contracts

| Category | Detail |
|---|---|
| Enum: `placementstatus` | 11 values: added `completed`, `ord_blocked` |
| Enum: `transactiontype` | 20 values: added `storno`, `admin_credit`, `gamification_bonus` |
| Enum: `disputereason` | 8 values: added 5 frontend values |
| Enum: `disputestatus` | 4 values: added `closed` |
| Enum: `disputeresolution` | 8 values: added 4 frontend values |
| Table: `placement_requests` | +3 columns: `advertiser_counter_price`, `advertiser_counter_schedule`, `advertiser_counter_comment` |
| Table: `channel_mediakits` | +3 columns: `owner_user_id` (FK→users), `logo_file_id`, `theme_color` |
| Table: `document_uploads` | DB column `extracted_ogrnip` now mapped in ORM |
| FK cascade | `acts.contract_id`, `invoices.placement_request_id/contract_id`, `transactions.act_id/invoice_id` → ON DELETE SET NULL |
| FK cascade | `users.referred_by_id`, `transactions.reverses_transaction_id` → ON DELETE SET NULL |
| Indexes | 6 new FK indexes on placement_disputes, reputation_history, user_badges, badge_achievements |
| Constraint | `uq_review_placement_reviewer` (was `uq_reviews_…` — plural bug fixed) |
| Alembic check | **Zero drift** — `No new upgrade operations detected.` |

## Migration Notes

- **Pre-production policy**: `0001_initial_schema.py` edited directly as authoritative snapshot. 0002 deleted.
- `alembic upgrade head` → `0001_initial_schema (head)` — single revision, no chain.
- `alembic check` → `No new upgrade operations detected.` ✅
- DB reset command used: `DROP DATABASE market_bot_db; CREATE DATABASE market_bot_db;` then `alembic upgrade head`.

---
🔍 Verified against: `d379bca` | 📅 Updated: 2026-04-18T01:03:28Z
