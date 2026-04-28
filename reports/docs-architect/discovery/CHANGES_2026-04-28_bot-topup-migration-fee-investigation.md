# CHANGES — Bot topup migration + fee model investigation

## What

Two parts shipped together:

### Part A — Bot topup migration (code change)
Bot handler `topup_pay` migrated from dead `YooKassaService.create_payment`
to canonical `YooKassaService.create_topup_payment`. Bot, mini_app, and
web_portal now use identical service entry point for topup creation.

Dead method `YooKassaService.create_payment` removed (deferred from
Промтов 13/15 due to bot handler dependency).

`tests/smoke_yookassa.py` removed (called the dead method).

### Part B — Fee model investigation (read-only diagnostic)
Investigation report inline below. No backend / frontend code changes
related to fee constants in this commit.

## Code changes (Part A)

### `src/bot/handlers/billing/billing.py`
- `topup_pay` handler — now calls
  `YooKassaService().create_topup_payment(session=..., user_id=...,
  desired_balance=...)`. Passes the amount the user typed (the desired
  net credit), not pre-multiplied gross.
- Catches `PaymentProviderError` → graceful Telegram message that
  includes the YooKassa request_id for support tracing.
- Catches `ValueError` → user-facing error message.
- Generic `Exception` fallback preserved (covers RuntimeError from
  unconfigured YooKassa credentials).

### `src/core/services/yookassa_service.py`
- Removed dead `create_payment` method (replaced by
  `create_topup_payment`). Removed two no-longer-used imports:
  `from uuid import uuid4` and
  `from src.db.session import async_session_factory`.

### Tests
- `tests/integration/test_bot_topup_handler.py` (new): 2 integration
  tests covering bot handler happy path (calls
  `create_topup_payment` with caller's session + user.id +
  `desired_balance`) and `PaymentProviderError` handling (user sees
  "недоступен" message + request_id).
- `tests/unit/test_no_dead_methods.py` (extended): `create_payment`
  added to `DEAD_YOOKASSA_METHODS`.
- `tests/smoke_yookassa.py` (deleted): obsolete — exercised the
  removed dead method.

## Public contract delta

None. Bot user-facing UX:
- Before: invisible TypeError on topup attempt (handler called dead
  `create_payment` with `amount_rub=` kwarg, dead method instantiated
  `YookassaPayment` with non-existent fields → TypeError caught by
  bare `except Exception`, user saw the generic error message). On
  live YooKassa creds the dead method's TypeError was masked by an
  earlier 403 from the SDK.
- After: graceful Russian message "⚠️ Платёжный сервис временно
  недоступен..." + provider request_id for support, with a "🔙 Назад"
  button. Successful path renders payment URL keyboard exactly as
  before.

POST `/api/billing/topup` (mini_app + web_portal): unchanged.

## Fee model investigation report (Part B)

### Constants

| Constant | Defined at | Comment in source |
|---|---|---|
| `YOOKASSA_FEE_RATE` | `src/constants/payments.py:13` | `Decimal("0.035")  # Комиссия ЮKassa (3.5%)` |
| `PLATFORM_TAX_RATE` | `src/constants/payments.py:14` | `Decimal("0.06")  # ИП УСН 6%` |
| `PAYOUT_FEE_RATE` | `src/constants/payments.py:15` | `Decimal("0.015")  # Комиссия за вывод (1.5%)` |
| `NPD_RATE_FROM_LEGAL` | `src/constants/legal.py:113` | `Decimal("0.06")  # 6% НПД от юрлиц/ИП` (separate from topup flow) |

### Where each constant is USED

| Constant | File:line | Purpose | Effect |
|---|---|---|---|
| `YOOKASSA_FEE_RATE` (3.5%) | `src/constants/payments.py:114` | Helper `calculate_topup_payment()` | **No production callers** — only unit tests reference it. |
| `YOOKASSA_FEE_RATE` (3.5%) | `src/core/services/billing_service.py:17,536` | `BillingService.calculate_topup_payment` (instance method) | **No production callers** — only unit/integration tests reference it. |
| `PLATFORM_TAX_RATE` (6%) | `src/core/services/yookassa_service.py:85,96` | `YooKassaService.create_topup_payment` — actual fee applied to live payments | **Live**: this is what the user actually pays on top of `desired_balance`. |
| `PAYOUT_FEE_RATE` (1.5%) | `src/api/routers/payouts.py:178`, `src/bot/handlers/payout/payout.py:235`, `src/constants/payments.py:137`, `src/core/services/payout_service.py:544` | Withdrawal flow | Unrelated to topup. |
| Hardcoded `0.035` | `src/bot/handlers/billing/billing.py:55` | Bot UI string `"Комиссия: ..."` shown on confirm screen | Display only — bot now passes `desired_balance` (not pre-multiplied gross) to the canonical service which uses `PLATFORM_TAX_RATE`. |
| Hardcoded `0.035` | `mini_app/src/lib/constants.ts:68` (`YOOKASSA_FEE`) → `mini_app/src/lib/formatters.ts:99` (`calcTopUpFee`) → `mini_app/src/screens/common/TopUpConfirm.tsx:63` ("Комиссия ЮKassa (3,5%)") | Mini App UI string + total preview | Display only. |
| Hardcoded `0.035` | `web_portal/src/screens/shared/TopUpConfirm.tsx:66,193` ("Комиссия ЮKassa (3,5%)") | Web portal UI string + total preview | Display only. |

### Trace: user wants to topup 100 ₽ (after Промт-15.5)

1. User picks "100 ₽" in bot or web frontend.
2. Frontend / bot UI displays:
   - Bot: `"Комиссия: 3.50 ₽ К оплате: 103.50 ₽"` (computed with hardcoded 0.035 in `billing.py:55`).
   - Mini App: `"Комиссия ЮKassa (3,5%): +3 ₽"` (`Math.round(100 * 0.035) = 4`, but `Math.round` of `3.5` is `4` in JS; on this exact case the displayed fee is `4 ₽`).  Note: rounding inconsistency between Python `quantize(0.01)` and JS `Math.round` is a separate observation.
   - Web portal: `"Комиссия ЮKassa (3,5%): +3 ₽"` (same `Math.round(amount * 0.035)`).
3. Frontend / bot sends `desired_balance = 100` to:
   - Web frontends → `POST /api/billing/topup` → router calls `YooKassaService().create_topup_payment(session, user_id, desired_balance=100)`.
   - Bot → `topup_pay` handler now calls the same service method (Промт-15.5).
4. `YooKassaService.create_topup_payment` (yookassa_service.py:80-138):
   - `fee_amount = 100 * PLATFORM_TAX_RATE = 100 * 0.06 = 6.00 ₽` (line 96).
   - `gross_amount = 100 + 6 = 106.00 ₽` (line 97).
5. SDK `Payment.create` is called with `amount.value = "106.00"`.  The user is redirected to YooKassa and pays **106 ₽**.
6. Inside YooKassa, the operator deducts its true commission (~3.5%) from the merchant payout. We do not see that fee directly — we see "succeeded" with `gross_amount = 106 ₽`.
7. Webhook `payment.succeeded` → `BillingService.process_topup_webhook` (billing_service.py:547-649):
   - `User.balance_rub += desired_balance` (= 100 ₽). Difference (6 ₽) is **NOT** credited.
   - `PlatformAccount.total_topups += desired_balance` (= 100 ₽).
   - `Transaction(type=TOPUP, amount=100, meta_json={..., gross_amount: "106"})`.
   - `TaxAggregationService.record_income_for_usn(gross_amount=106)` — ВСЯ сумма gross записана как доход для УСН.
   - `TaxAggregationService.record_expense_for_usn(yk_fee = gross - desired = 6 ₽, category=BANK_COMMISSIONS)` — разница записана как расход.

### What 6% actually goes towards (factually, from code)

The `PLATFORM_TAX_RATE = 6%` comment says "ИП УСН 6%". The
implementation behaviour is:
- The user is charged 6% on top of the desired balance.
- That 6% is recorded as a **bank-commissions expense** in the УСН tax
  aggregation (`category=BANK_COMMISSIONS`, билинг_сервис:629–634).
- The full gross (including the 6%) is recorded as **income for УСН**
  (`record_income_for_usn(gross_amount=106)`, billing_service.py:617–
  621).

So the code treats the 6% as a "fee that covers ЮKassa commission" but
applies a 6% rate, not the 3.5% rate that the YooKassa operator
actually charges. The 2.5% delta (≈ 6% − 3.5%) is **net positive** for
the platform: user pays 6%, YooKassa keeps ~3.5%, ~2.5% remains as
implicit margin (recorded under bank-commissions expense, but not
matching real bank cost).

The displayed UI fee (3.5%) matches the YooKassa SDK's actual fee but
is **smaller** than what the user is actually charged on the YooKassa
checkout page (6%). On mobile-Telegram the user sees `103.50 ₽`, but
the YooKassa redirect URL bills `106.00 ₽`. Same on mini_app /
web_portal.

### UI fee text inventory

| Source | File:line | Text shown to user | Computed value | Backend reality |
|---|---|---|---|---|
| Bot keyboard | `src/bot/handlers/billing/billing.py:55` | `"Комиссия: 3.50 ₽\nК оплате: 103.50 ₽"` (for 100 ₽ topup) | `amount * 0.035` | User actually billed `amount * 1.06 = 106 ₽`. |
| Mini App TopUpConfirm | `mini_app/src/screens/common/TopUpConfirm.tsx:63` | `"Комиссия ЮKassa (3,5%): + N ₽"` (where `N = Math.round(amount * 0.035)`) | hardcoded 0.035 in `mini_app/src/lib/constants.ts:68`, used by `calcTopUpFee` in `mini_app/src/lib/formatters.ts:99` | Same — actually billed 106 ₽. |
| Web portal TopUpConfirm | `web_portal/src/screens/shared/TopUpConfirm.tsx:66,193` | `"Комиссия ЮKassa (3,5%): + N ₽"` | hardcoded `Math.round(amount * 0.035)` inline | Same — actually billed 106 ₽. |

### Decision needed (Marina, separate Промт-15.7)

After reviewing this report — these are the four directions surfaced
by the inconsistency. **This investigation does not recommend a
specific option** — Marina decides per business model.

- **(I) Fix backend down to YooKassa-real rate.** Change
  `YooKassaService.create_topup_payment` to use `YOOKASSA_FEE_RATE`
  (3.5%) — matches what every UI string already displays. User pays
  103.50 ₽ for a 100 ₽ topup. Platform absorbs the 2.5% margin
  difference (or wasn't booking it anyway).
- **(II) Fix UI up to backend-real rate.** Change bot text + mini_app
  + web_portal text to display 6%. User sees the real charge before
  redirect. No backend change.
- **(III) Show two components separately.** "Комиссия ЮKassa: 3,5% +
  Комиссия сервиса: 2,5%" (or "Налог 6%"). Surfaces the platform's
  margin / tax line explicitly.
- **(IV) Defer.** Document the discrepancy, don't change anything,
  revisit later.

(Adjacent observations not in scope for this prompt: `Math.round` vs
Python `quantize(0.01)` produce different rounding for fractional
kopecks; the `BillingService.calculate_topup_payment` and
`src/constants/payments.py::calculate_topup_payment` helpers have no
production callers and silently use the 3.5% rate — they would
produce results that disagree with reality if reused.)

## Gate baseline

Pre → post:
- Forbidden-patterns: 17/17 → 17/17 ✓
- Ruff `src/`: 21 → 21
- Mypy: 10 errors / 5 files → 10 errors / 5 files
- Pytest: 76F + 17E + 638P → 76F + 17E + 640P (2 new bot handler tests)

## Origins

- BL-034 Finding 1: RESOLVED in this session.
- BL-034 Finding 2: INVESTIGATED, decision pending Промт-15.7.
- `BILLING_REWRITE_PLAN_2026-04-28.md` item 6 (consolidation
  continuation).

🔍 Verified against: `<commit_hash_will_be_filled_after_commit>` | 📅 Updated: 2026-04-28T00:00:00Z
