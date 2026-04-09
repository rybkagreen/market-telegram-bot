# CHANGES — S-29.6 DB Migration + Constants + Tests (credits → balance_rub)

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Phase 6 (final): Removed all remaining credit-related constants, created DB migration to merge `credits` into `balance_rub` and DROP the column, updated test fixtures and assertions.

## Constants Removed

| File | Removed |
|------|---------|
| `src/constants/payments.py` | `CREDIT_PACKAGES`, `CREDIT_PACKAGE_STANDARD`, `CREDIT_PACKAGE_BUSINESS` |
| `src/constants/tariffs.py` | `TARIFF_CREDIT_COST` |
| `src/constants/__init__.py` | All credit-related re-exports |
| `src/config/settings.py` | `credits_per_rub_for_plan` |

## Database Migration

| File | Description |
|------|-------------|
| `src/db/migrations/versions/s33a001_merge_credits_to_balance_rub.py` | NEW — `UPDATE users SET balance_rub = balance_rub + CAST(credits AS NUMERIC) WHERE credits > 0` then `DROP COLUMN credits` |

**Migration logic:**
1. Merge: `balance_rub += credits` (1:1 conversion)
2. Drop: `ALTER TABLE users DROP COLUMN credits`
3. Rollback: Re-add column (balance_rub NOT reverted — intentional)

## Tests Updated

| File | Change |
|------|--------|
| `tests/conftest.py` | Fixtures: `credits`→`balance_rub` (int→int, no Decimal needed for mock data) |
| `tests/unit/test_start_and_role.py` | `u.credits`→`u.balance_rub` (mock user fixtures) |
| `tests/unit/test_review_service.py` | `credits=N`→`balance_rub=Decimal("N")` (real DB fixtures) |
| `tests/unit/test_escrow_payouts.py` | `credits`→`balance_rub` (dict keys, test names) |
| `tests/mocks/yookassa_mock.py` | Metadata: `"credits"`→`"amount_rub"` |
| `tests/smoke_yookassa.py` | T-04: removed `credits` from required columns; T-05: updated formatter call; T-07: removed `credits` param; T-10: removed `credits` assertion |

## Verification

- ✅ `poetry run ruff check` — 0 new errors (9 pre-existing SIM117/F841 unrelated to credits)
- Migration file syntax verified

## Full Sprint S-29 Summary

| Phase | Files | Status |
|-------|-------|--------|
| S-29.1: Core Services | 5 | ✅ |
| S-29.2: Celery Tasks | 3 | ✅ |
| S-29.3: API Routers + Schemas | 10 | ✅ |
| S-29.4: Bot Handlers | 2 | ✅ |
| S-29.5: Frontend | 14 | ✅ |
| S-29.6: Migration + Constants + Tests | 10 | ✅ |
| **Total** | **44 files** | **✅** |
