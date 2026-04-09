# CHANGES — S-29.2 Celery Tasks (credits → balance_rub)

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Phase 2: Converted all Celery tasks from `credits` to `balance_rub`.

## Files Changed

| File | Change |
|------|--------|
| `src/tasks/billing_tasks.py` | Plan renewal: `_PLAN_COSTS` from settings, `user.balance_rub` check, `update_balance_rub()`, notification text "₽" |
| `src/tasks/notification_tasks.py` | `_notify_low_balance(credits: int)` → `_notify_low_balance(balance_rub: Decimal)`, text "N кр" → "N ₽" |
| `src/tasks/gamification_tasks.py` | `update_credits(user_id, 50)` → `update_balance_rub(user_id, Decimal("50"))` |

## Details

### billing_tasks.py
- Removed import `TARIFF_CREDIT_COST` from constants
- Added `_PLAN_COSTS` dict from `settings.tariff_cost_*` (consistent with billing_service.py)
- Plan check: `user.credits >= plan_cost` → `user.balance_rub >= Decimal(str(plan_cost))`
- Deduction: `update_credits(user.id, -plan_cost)` → `update_balance_rub(user.id, -Decimal(str(plan_cost)))`
- Log: `"had {user.credits} credits"` → `"had {user.balance_rub} ₽"`
- Notification: `"Списано кредитов: {plan_cost}"` → `"Списано: {plan_cost} ₽"`

### notification_tasks.py
- Function signature: `_notify_low_balance(telegram_id: int, credits: int)` → `_notify_low_balance(telegram_id: int, balance_rub: Decimal)`
- Message: `"Ваш баланс: {credits} кр"` → `"Ваш баланс: {balance_rub:.2f} ₽"`

### gamification_tasks.py
- `update_credits(user_id, 50)` → `update_balance_rub(user_id, Decimal("50"))`
- Comment: `# +50 кредитов` → `# +50 ₽ бонус`

## Verification

- ✅ `poetry run ruff check` — 0 errors

## Next

- S-29.3: API Routers + Schemas (~9 files)
- S-29.4: Bot Handlers
- S-29.5: Frontend
- S-29.6: DB Migration + Constants + Tests
