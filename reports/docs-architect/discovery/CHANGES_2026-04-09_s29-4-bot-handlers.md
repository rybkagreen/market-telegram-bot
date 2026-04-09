# CHANGES — S-29.4 Bot Handlers (credits → balance_rub)

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Phase 4: Converted bot handlers from `credits` to `balance_rub`.

## Files Changed

| File | Change |
|------|--------|
| `src/bot/handlers/billing/billing.py` | Removed `credits` param from `yookassa_service.create_payment()` call |
| `src/bot/handlers/shared/notifications.py` | `format_yookassa_payment_success(credits, new_balance)` → `(amount_rub, new_balance)` — text "Зачислено кредитов" → "Баланс: N ₽" |

## Verification

- ✅ `poetry run ruff check` — 0 errors

## Next

- S-29.5: Frontend (mini_app + web_portal)
- S-29.6: DB Migration + Constants + Tests
