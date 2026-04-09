# CHANGES — S-29.5 Frontend (mini_app + web_portal) credits → balance_rub

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Phase 5: Updated all frontend code to use `balance_rub` instead of `credits`. Removed credit converter UI, updated types, API calls, and screen text.

## mini_app (7 files)

| File | Change |
|------|--------|
| `src/api/billing.ts` | Removed `TopupPackage`, `packages` field from `BillingBalance`; `credits_remaining`→`balance_rub_remaining`; `TransactionType.credits_buy` removed; `BuyCreditsResponse` simplified to `{amount_rub}` |
| `src/api/analytics.ts` | `AnalyticsSummary.credits`→`balance_rub` |
| `src/hooks/queries/useBillingQueries.ts` | Toast "Зачислено N кредитов"→"Оплачено N ₽"; error text updated |
| `src/screens/common/Cabinet.tsx` | Removed credits converter form, credits stat card; 3-col→2-col grid |
| `src/screens/common/Plans.tsx` | `user.credits`→`user.balance_rub` |
| `src/screens/common/Referral.tsx` | `total_earned_credits`→`total_earned_rub` |
| `src/screens/common/TransactionHistory.tsx` | Removed `credits_buy` entry |
| `src/screens/admin/AdminUserDetail.tsx` | "Кредиты"→"Баланс ₽" |

## web_portal (7 files)

| File | Change |
|------|--------|
| `src/api/billing.ts` | `getBalance()` removed `credits` field |
| `src/stores/authStore.ts` | `User` type removed `credits` field |
| `src/screens/common/Cabinet.tsx` | Removed credits converter form and stat card; 3-col→2-col grid |
| `src/screens/shared/Plans.tsx` | `user.credits`→`user.balance_rub` |
| `src/screens/common/Referral.tsx` | `total_earned_credits`→`total_earned_rub` |
| `src/screens/common/TransactionHistory.tsx` | Removed `credits_buy` entry |
| `src/screens/admin/AdminUserDetail.tsx` | "Кредиты"→"Баланс ₽" |

## Verification

- ✅ `npx tsc --noEmit` (mini_app) — 0 errors
- ✅ `npx tsc --noEmit` (web_portal) — 0 errors

## Next

- S-29.6: DB Migration + Constants + Tests
