# CHANGES — Tariff Price Consistency & Credits→RUB Text Migration

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Fixed all tariff price discrepancies across the codebase (old v3.x prices 299/990/2999 → correct 490/1490/4990) and replaced "credits" terminology with "₽" (rubles) in all user-facing text.

## Bugs Fixed

| # | File | Issue | Before | After |
|---|------|-------|--------|-------|
| 1 | `src/tasks/notification_tasks.py:1166` | Old prices in tariff expiry notifications | 299/999/2999 | 490/1490/4990 |
| 2 | `landing/src/lib/constants.ts` | Landing page tariffs all wrong | 299/990/2999 | 490/1490/4990 |
| 3 | `mini_app/src/screens/common/Plans.tsx:79` | Low-balance threshold too low | `< 299` | `< 500` |
| 4 | `web_portal/src/screens/shared/Plans.tsx:90` | Low-balance threshold too low | `< 299` | `< 500` |

## Text Changes (Credits → ₽)

| File | Before | After |
|------|--------|-------|
| `notification_tasks.py` | "Стоимость продления: N кр" | "Стоимость продления: N ₽" |
| `notification_tasks.py` | "Текущий баланс: N кр" | "Текущий баланс: N ₽" |
| `landing/.../Tariffs.tsx` | "1 кредит = 1 ₽ · Комиссия..." | "Комиссия... · Оплата в рублях" |
| `landing/src/lib/constants.ts` | Removed `CREDITS_PER_RUB`, `priceCredits` field | `priceRub` only |
| `mini_app/.../Plans.tsx` | "Кредиты: N 🎟" | "Баланс: N ₽" |
| `mini_app/.../Plans.tsx` | "кр/мес" | "₽/мес" |
| `mini_app/.../Plans.tsx` | "Конвертируйте ₽ → кредиты" | "Пополните баланс" |
| `web_portal/.../Plans.tsx` | "Кредиты: N 🎟" | "Баланс: N ₽" |
| `web_portal/.../Plans.tsx` | "кредитов/мес" | "₽/мес" |
| `web_portal/.../Plans.tsx` | "Конвертируйте ₽ → кредиты" | "Пополните баланс" |

## Code Quality

| File | Change |
|------|--------|
| `src/bot/handlers/billing/billing.py` | `_PLAN_PRICES` changed from hardcoded dict to `settings.tariff_cost_*` references |

## Files Changed

| File | Change |
|------|--------|
| `src/tasks/notification_tasks.py` | `_RENEWAL_COSTS` prices + text |
| `src/bot/handlers/billing/billing.py` | `_PLAN_PRICES` → settings ref |
| `landing/src/lib/constants.ts` | TARIFFS prices, removed `priceCredits`/`CREDITS_PER_RUB` |
| `landing/src/components/Tariffs.tsx` | Note text changed |
| `mini_app/src/screens/common/Plans.tsx` | Threshold, text, currency label |
| `web_portal/src/screens/shared/Plans.tsx` | Threshold, text, currency label |

## Verification

- ✅ `poetry run ruff check` — 0 errors
- ✅ `npm run build` (landing) — 0 errors
- ✅ `npx eslint src/` (landing) — 0 errors
- ✅ `npx tsc --noEmit` (landing) — 0 errors
- ✅ `npx tsc --noEmit` (mini_app) — 0 errors
- ✅ `npx tsc --noEmit` (web_portal) — 0 errors

## Impact

- **User-facing**: All tariff prices now consistent (490/1490/4990 ₽)
- **Notifications**: Tariff expiry messages show correct renewal costs
- **Terminology**: Users see "₽" and "баланс" instead of "кредиты" — no more confusion
- **No DB migration required**: Internal `User.credits` field unchanged; only display text modified
- **No API contract changes**: Backend returns same values, frontend labels updated
