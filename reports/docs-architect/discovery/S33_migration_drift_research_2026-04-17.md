# S-33 Migration Drift Research — 0001_initial_schema vs SQLAlchemy Models

**Date:** 2026-04-17  
**Branch:** feature/s-31-legal-compliance-timeline  
**Scope:** Read-only audit; no files were modified.

---

## ⚠️ STOP Conditions Detected

**Migration 0002 exists.** File `src/db/migrations/versions/0002_add_advertiser_counter_fields.py`
(`revision = "0002_adv_counter"`, `down_revision = "0001_initial_schema"`) is an **incremental
migration** following Alembic's standard chaining model. The pre-production "edit 0001 directly"
policy has already been departed from in at least one case. The three columns it adds
(`advertiser_counter_price`, `advertiser_counter_schedule`, `advertiser_counter_comment`) are
present in both the migration and the model — so 0002 is already applied and in sync.

**Action required before any patch work:**
1. Confirm with the team whether 0001 is still editable or whether all future changes must go into
   new incremental migrations (0003+).
2. Run `alembic check` against a live DB to detect any remaining drift not covered by this audit.

---

## Executive Summary

| Category | Count |
|---|---|
| Enum values missing from migration | **20** values across 5 enums |
| Columns in model but missing from migration | **3** (all in `channel_mediakits`) |
| Columns in migration but missing from model | **1** (`extracted_ogrnip` in `document_uploads`) |
| Type mismatches (Numeric/Integer/String) | **0** |
| Field renames / name drift (ReputationScore) | **0** |
| Self-referencing FKs missing ondelete rule | **2** |
| Missing indexes on FK columns | **5** |

---

## Table 1: Enum Values Drift

| enum_name | values_in_model | values_in_migration | missing_from_migration | model_file:line | migration_line |
|---|---|---|---|---|---|
| `placementstatus` | 11 | 10 | `completed` | placement_request.py:37 | 0001:1039 |
| `transactiontype` | 20 | 17 | `storno`, `admin_credit`, `gamification_bonus` | transaction.py:21 | 0001:934 |
| `disputereason` | 8 | 3 | `not_published`, `wrong_time`, `wrong_text`, `early_deletion`, `other` | dispute.py:19 | 0001:1573 |
| `disputestatus` | 4 | 3 | `closed` | dispute.py:38 | 0001:1581 |
| `disputeresolution` | 8 | 4 | `full_refund`, `partial_refund`, `no_refund`, `warning` | dispute.py:47 | 0001:1591 |
| `reputationaction` | 16 | 16 | — MATCH — | reputation_history.py:16 | 0001:1726 |
| `payoutstatus` | 5 | 5 | — MATCH — | payout.py:18 | 0001:742 |
| `publicationformat` | 5 | 5 | — MATCH — | placement_request.py:53 | 0001:1056 |

### Detail: placementstatus (1 missing)

Model (`placement_request.py:37–50`) has `completed` between `published` and `failed`.
Migration (`0001:1039`) list: `pending_owner, counter_offer, pending_payment, escrow, published,
failed, failed_permissions, refunded, cancelled, ord_blocked` — `completed` absent.

This means any code path that sets `status = PlacementStatus.completed` will raise a
PostgreSQL `invalid input value for enum` error at runtime.

### Detail: transactiontype (3 missing)

Model adds `storno` (Sprint D.2), `admin_credit`, and `gamification_bonus` after `ndfl_withholding`.
Migration only lists 17 values ending at `ndfl_withholding`.

### Detail: disputereason (5 missing)

Model has two groups: *legacy* (3 values matching migration) and *frontend* (5 new values:
`not_published`, `wrong_time`, `wrong_text`, `early_deletion`, `other`). All 5 frontend values
are missing from the migration's `disputereason` ENUM.

### Detail: disputestatus (1 missing)

Model: `open, owner_explained, resolved, closed`. Migration: `open, owner_explained, resolved`.
`closed` is absent — any `PlacementDispute` moved to `closed` status will fail at the DB level.

### Detail: disputeresolution (4 missing)

Model adds *frontend display* resolutions: `full_refund`, `partial_refund`, `no_refund`, `warning`
on top of the 4 financial resolutions already in migration. All 4 are absent from migration.

---

## Table 2: Column Drift

### 2a. Columns in model but MISSING from migration

| table | column | model_type | nullable | default | migration_status | model_file:line |
|---|---|---|---|---|---|---|
| `channel_mediakits` | `owner_user_id` | `Integer FK→users.id` | YES | — | **ABSENT** | channel_mediakit.py:23 |
| `channel_mediakits` | `logo_file_id` | `String(256)` | YES | — | **ABSENT** | channel_mediakit.py:28 |
| `channel_mediakits` | `theme_color` | `String(7)` | YES | — | **ABSENT** | channel_mediakit.py:29 |

All three are newly-added columns on the `ChannelMediakit` model. Because they are `nullable=True`,
the immediate runtime impact is limited to INSERT operations that try to write these fields — those
will fail with `column "owner_user_id" of relation "channel_mediakits" does not exist`.

The missing FK `owner_user_id → users.id` also means the `channel_mediakits_channel_id_fkey`
constraint on `telegram_chats` is the only integrity guard in the DB; ownership denormalization
has no DB-level enforcement.

### 2b. Columns in migration but MISSING from model

| table | column | migration_type | nullable | model_status | migration_line |
|---|---|---|---|---|---|
| `document_uploads` | `extracted_ogrnip` | `String(20)` | YES | **ABSENT** | 0001:451 |

`extracted_ogrnip` was created in the DB schema but was never added to the `DocumentUpload` ORM
model. SQLAlchemy will silently ignore this column on reads, but it will never be populated by the
application. Verify with the team whether extraction of ОГРНИП is still planned; if not, the
column can be dropped from the migration.

### 2c. Confirmed in sync (0002 migration)

| table | column | status |
|---|---|---|
| `placement_requests` | `advertiser_counter_price` | ✓ in both model and 0002 |
| `placement_requests` | `advertiser_counter_schedule` | ✓ in both model and 0002 |
| `placement_requests` | `advertiser_counter_comment` | ✓ in both model and 0002 |

---

## Table 3: Type Mismatches (Numeric / Integer / String)

No type-level mismatches found. All checked columns use identical precision/scale:

| column | model_type | migration_type | result |
|---|---|---|---|
| `placement_requests.proposed_price` | `Numeric(10, 2)` | `sa.Numeric(10, 2)` | ✓ MATCH |
| `placement_requests.counter_price` | `Numeric(10, 2)` | `sa.Numeric(10, 2)` | ✓ MATCH |
| `channel_settings.price_per_post` | `Numeric(10, 2)` | `sa.Numeric(10, 2)` | ✓ MATCH |
| `transactions.amount` | `Numeric(12, 2)` | `sa.Numeric(12, 2)` | ✓ MATCH |
| `payout_requests.gross_amount` | `Numeric(12, 2)` | `sa.Numeric(12, 2)` | ✓ MATCH |
| `reputation_scores.advertiser_score` | `Float` | `sa.Float()` | ✓ MATCH |

Server defaults differ in representation (`"5.0"` vs `sa.text("5")`) but are functionally
equivalent in PostgreSQL for `FLOAT` columns.

---

## Table 4: Field Renames — ReputationScore and Others

No field renames detected. All field names in `reputation_scores` are identical between
model (`reputation_score.py`) and migration (0001:686–729):

| field | model_name | migration_name | result |
|---|---|---|---|
| violations counter (advertiser) | `advertiser_violations_count` | `advertiser_violations_count` | ✓ MATCH |
| violations counter (owner) | `owner_violations_count` | `owner_violations_count` | ✓ MATCH |
| block until (advertiser) | `advertiser_blocked_until` | `advertiser_blocked_until` | ✓ MATCH |
| block until (owner) | `owner_blocked_until` | `owner_blocked_until` | ✓ MATCH |

No renames confirmed in any other audited model.

---

## Table 5: Missing Indexes on FK Columns

| table | fk_column | references | index_in_migration | impact |
|---|---|---|---|---|
| `placement_disputes` | `advertiser_id` | `users.id` | **MISSING** | Full table scan for dispute lookups by advertiser |
| `placement_disputes` | `owner_id` | `users.id` | **MISSING** | Full table scan for dispute lookups by owner |
| `placement_disputes` | `admin_id` | `users.id` | **MISSING** | Full table scan for admin dispute queries |
| `reputation_history` | `placement_request_id` | `placement_requests.id` | **MISSING** | Full scan when fetching history per placement |
| `user_badges` | `badge_id` | `badges.id` | **MISSING** | Full scan when querying badges by badge definition |
| `badge_achievements` | `badge_id` | `badges.id` | **MISSING** | Full scan for achievement lookups by badge |

Existing indexes confirmed present for reference:
- `ix_placement_disputes_placement_request_id` ✓
- `ix_placement_disputes_status` ✓
- `ix_reputation_history_user_id` ✓
- `ix_user_badges_user_id` ✓

---

## Table 6: Self-Referencing FKs Missing ondelete Rule

Both self-referencing FKs are created via deferred `op.create_foreign_key()` at the bottom of
`0001_initial_schema.py`. Neither has the `ondelete` parameter that the ORM model specifies.

| table | column | references | model_ondelete | migration_ondelete | migration_line |
|---|---|---|---|---|---|
| `users` | `referred_by_id` | `users.id` | `SET NULL` | **(none)** | 0001:1777 |
| `transactions` | `reverses_transaction_id` | `transactions.id` | `SET NULL` | **(none)** | 0001:1818 |

**Risk:** Without `ON DELETE SET NULL` at the DB level, deleting a referrer `User` row will raise
a FK violation instead of nullifying `referred_by_id`. Similarly, deleting a reversed transaction
will fail instead of clearing the back-reference. The ORM's `ondelete` keyword only affects
`CASCADE` / `SET NULL` behavior when SQLAlchemy controls the DELETE — raw SQL deletes or admin
tool deletes bypass it.

**Patches needed in 0001 (or new migration):**

```python
# users self-ref: add ondelete="SET NULL"
op.create_foreign_key(
    "users_referred_by_id_fkey", "users", "users",
    ["referred_by_id"], ["id"],
    ondelete="SET NULL",          # ← add this
)

# transactions self-ref: add ondelete="SET NULL"
op.create_foreign_key(
    "fk_txn_reverses", "transactions", "transactions",
    ["reverses_transaction_id"], ["id"],
    ondelete="SET NULL",          # ← add this
)
```

---

## Recommended Patch Order for 0001_initial_schema.py

*(If the team decides to keep editing 0001 directly. Otherwise each item becomes a new 0003+ migration.)*

Apply in this exact order to avoid conflicts:

1. **ENUM patches** — `ALTER TYPE ... ADD VALUE` for each missing value, one statement per value.
   Order: `placementstatus` → `transactiontype` → `disputereason` → `disputestatus` →
   `disputeresolution`. Each `ADD VALUE IF NOT EXISTS` is safe to run multiple times.
   > Note: PostgreSQL does not support removing enum values, only adding. If any removed-value
   > cleanup is needed it requires a full `CREATE TYPE ... AS ENUM (...)` / `ALTER COLUMN ...
   > USING ... ::text::new_type` cycle.

2. **Add missing columns to `channel_mediakits`** — three nullable columns; safe to add without
   a default on an empty table:
   ```sql
   ALTER TABLE channel_mediakits ADD COLUMN owner_user_id INTEGER REFERENCES users(id);
   ALTER TABLE channel_mediakits ADD COLUMN logo_file_id VARCHAR(256);
   ALTER TABLE channel_mediakits ADD COLUMN theme_color VARCHAR(7);
   ```

3. **Drop or keep `extracted_ogrnip`** — decision with product team. If dropping:
   ```sql
   ALTER TABLE document_uploads DROP COLUMN extracted_ogrnip;
   ```

4. **Add missing FK indexes** on `placement_disputes`, `reputation_history`, `user_badges`,
   `badge_achievements`:
   ```sql
   CREATE INDEX IF NOT EXISTS ix_placement_disputes_advertiser_id ON placement_disputes (advertiser_id);
   CREATE INDEX IF NOT EXISTS ix_placement_disputes_owner_id ON placement_disputes (owner_id);
   CREATE INDEX IF NOT EXISTS ix_placement_disputes_admin_id ON placement_disputes (admin_id);
   CREATE INDEX IF NOT EXISTS ix_reputation_history_placement_request_id ON reputation_history (placement_request_id);
   CREATE INDEX IF NOT EXISTS ix_user_badges_badge_id ON user_badges (badge_id);
   CREATE INDEX IF NOT EXISTS ix_badge_achievements_badge_id ON badge_achievements (badge_id);
   ```

5. **Fix self-referencing FK ondelete rules** — requires drop-and-recreate the FK constraints:
   ```sql
   ALTER TABLE users DROP CONSTRAINT users_referred_by_id_fkey;
   ALTER TABLE users ADD CONSTRAINT users_referred_by_id_fkey
       FOREIGN KEY (referred_by_id) REFERENCES users(id) ON DELETE SET NULL;

   ALTER TABLE transactions DROP CONSTRAINT fk_txn_reverses;
   ALTER TABLE transactions ADD CONSTRAINT fk_txn_reverses
       FOREIGN KEY (reverses_transaction_id) REFERENCES transactions(id) ON DELETE SET NULL;
   ```

6. **Run `alembic check`** to confirm zero remaining drift after all patches.

---

## Verification Commands Used

```bash
ls -1 src/db/migrations/versions/
# → 0001_initial_schema.py
# → 0002_add_advertiser_counter_fields.py

grep -n 'ForeignKey' src/db/models/*.py | wc -l
# → 73

grep -n 'ondelete' src/db/models/*.py
# → 7 occurrences (click_tracking, feedback, mailing_log×2, publication_log, transaction, user)

grep -n 'ondelete' src/db/migrations/versions/0001_initial_schema.py
# → 10 occurrences (2 deferred FK missing their ondelete params)
```

---

🔍 Verified against: `d195386` (HEAD of feature/s-31-legal-compliance-timeline) | 📅 Updated: 2026-04-17T00:00:00Z
