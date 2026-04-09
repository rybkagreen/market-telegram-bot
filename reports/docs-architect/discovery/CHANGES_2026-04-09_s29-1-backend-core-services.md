# CHANGES — S-29.1 Backend Core Services (credits → balance_rub)

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Phase 1 of credits removal: converted all core backend services from `credits` (Integer) to `balance_rub` (Numeric) as the single internal currency. This eliminates the 1:1 credit↔ruble conversion layer.

## Files Changed

| File | Change |
|------|--------|
| `src/db/repositories/user_repo.py` | `update_credits(user_id, delta: int)` → `update_balance_rub(user_id, delta: Decimal)` |
| `src/core/services/billing_service.py` | 6 methods converted (see details below) |
| `src/core/services/yookassa_service.py` | `create_payment()` removed `credits` param; `_credit_user()` uses `balance_rub` |
| `src/core/services/badge_service.py` | Badge rewards: `credits` → `balance_rub` (Decimal) |
| `src/core/services/xp_service.py` | Streak bonuses: `credits` → `balance_rub` (Decimal) |

## billing_service.py — Methods Converted

| Method | Before | After |
|--------|--------|-------|
| `buy_credits_for_plan()` | Converts RUB→credits, creates 2 transactions | Direct `balance_rub` deduction, 1 transaction |
| `activate_plan()` | Checks `user.credits < plan_price`, `user.credits -= plan_price` | Checks `user.balance_rub < plan_price`, `user.balance_rub -= plan_price` |
| `freeze_campaign_funds()` | Checks `user.credits < cost`, `user.credits -= int(cost)` | Checks `user.balance_rub < cost`, `user.balance_rub -= cost` |
| `refund_escrow_credits()` | `user.credits += int(amount)`, direct write | `user_repo.update_balance_rub(advertiser_id, amount)` via repo ✅ |
| `deduct_credits()` | Renamed to `deduct_balance_rub()`, uses `update_balance_rub` | Via repo ✅ |
| `_credit_user()` (in yookassa) | `user.credits += credits` | `user.balance_rub += amount_rub` |
| Referral bonus (first campaign) | `update_credits(referrer_id, 100)` | `update_balance_rub(referrer_id, Decimal("100"))` |
| Payment crediting (webhook) | `update_credits(user_id, credits_amount)` | `update_balance_rub(user_id, amount_rub)` |

## Key Design Decisions

1. **All direct writes eliminated**: Previously 6 locations did `user.credits +=/-=` directly. Now ALL go through `user_repo.update_balance_rub()` (axiom: repos = only DB access layer).

2. **balance_rub type**: Numeric(12,2) — same precision as payments. No more Integer truncation.

3. **Transaction metadata**: Removed `credits_spent`, `credits_frozen` keys. Now uses plain `amount` in rubles.

4. **YooKassa `credits` column**: Still written as `int(amount_rub)` for backward compat with existing migration. Will be dropped in S-29.6 migration.

## Verification

- ✅ `poetry run ruff check` — 0 errors (1 auto-fixed import sort)
- All 5 modified files pass linting

## Next Steps (S-29.2+)

- S-29.2: Celery tasks (`billing_tasks.py`, `notification_tasks.py`, `gamification_tasks.py`)
- S-29.3: API routers (`billing.py`, `auth.py`, `users.py`, `admin.py`, etc.)
- S-29.4: Bot handlers (`billing/billing.py`)
- S-29.5: Frontend (mini_app, web_portal)
- S-29.6: DB migration + constants cleanup + tests
