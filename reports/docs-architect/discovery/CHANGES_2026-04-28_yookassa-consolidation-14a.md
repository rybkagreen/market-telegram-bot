# CHANGES — YookassaService consolidation 14a (create_payment move + /topup migration)

## What

Topup creation logic relocated from `BillingService` to `YooKassaService`,
following caller-controlled session pattern (S-48). POST `/api/billing/topup`
endpoint migrated to canonical `Depends(get_db_session)`. Item 6 14a of the
12-item billing rewrite plan (`BILLING_REWRITE_PLAN_2026-04-28.md`).

## Code changes

### `src/core/services/yookassa_service.py`
- Added new method
  `create_topup_payment(session, *, user_id, desired_balance) -> dict`:
  caller-controlled async session (S-48), YooKassa SDK call OUTSIDE any DB
  transaction, raises `PaymentProviderError` on SDK errors, persists
  `YookassaPayment` + pending `Transaction` row via `session.flush`.
  Returns dict with `payment_id`, `payment_url`, `amount` (gross),
  `credits` (= `int(desired_balance)`), `status="pending"`.
- Imports added: `AsyncSession`, full set of YooKassa exceptions
  (`BadRequestError`, `ForbiddenError`, `NotFoundError`,
  `ResponseProcessingError`, `TooManyRequestsError`, `UnauthorizedError`),
  `PaymentProviderError`, `TransactionRepository`, `TransactionType`,
  `UserRepository`.
- Existing dead `YooKassaService.create_payment` method NOT removed in
  this prompt (per BL-034 finding 1: live-wired bot handler still
  references it; deferred to a separate decision).

### `src/core/services/billing_service.py`
- Removed `create_payment` method entirely (logic moved).
- Removed unused imports after the deletion: `asyncio`, `uuid`,
  `Configuration`, `Payment`, all yookassa exception classes,
  `from src.config.settings import settings` (top-level — inner imports
  in remaining methods retained).

### `src/api/routers/billing.py`
- `create_unified_topup` (POST `/topup`) now:
  - Accepts `session: Annotated[AsyncSession, Depends(get_db_session)]`.
  - Calls `YooKassaService().create_topup_payment(session=session, ...)`.
  - Preserves `PaymentProviderError → HTTP 503` translation (Промт-12D).
  - Adds explicit `ValueError → HTTP 400` translation (e.g. user not
    found).

### Tests
- `tests/integration/test_yookassa_create_topup_payment.py` (new):
  4 integration tests:
  1. Happy path — SDK succeeds → `YookassaPayment` + `Transaction`
     persisted via caller's session, returned dict matches contract.
  2. SDK `ForbiddenError` → `PaymentProviderError`, no DB rows.
  3. User not found → `ValueError`, SDK never called, no DB rows.
  4. POST `/topup` endpoint forwards to `create_topup_payment` with
     correct kwargs and the caller's session.
- `tests/integration/test_billing_hotfix_bundle.py` — two Промт-12D
  regression tests rewired:
  - `test_create_payment_translates_forbidden_to_payment_provider_error`:
    now patches `yookassa_service.Payment.create` and calls
    `YooKassaService().create_topup_payment(session=db_session, ...)`.
  - `test_topup_endpoint_returns_503_on_payment_provider_error`: now
    patches `YooKassaService.create_topup_payment` and passes
    `session=db_session` to the endpoint call.
- `tests/unit/test_no_dead_methods.py`:
  - Added `"create_payment"` to `DEAD_BILLING_METHODS`.
  - Updated assertion message to reference items 4 AND 6 of the rewrite
    plan and the new `YooKassaService.create_topup_payment` location.
  - **Not** added to `DEAD_YOOKASSA_METHODS` — see Finding 1 below.

## Public contract delta

POST `/api/billing/topup`:
- Request shape: unchanged (`{desired_amount, method}`).
- 200 response shape: unchanged (`{payment_id, payment_url, status}`).
- 503 error shape: unchanged from Промт-12D
  (`{message, provider_error_code, provider_request_id}`).
- 400 errors now also include `ValueError → 400` (e.g. user not found),
  which previously surfaced as 500. Frontend already shows generic error
  notification for non-503 statuses; no UI change needed.

No frontend changes required (Промт-14 modal still works on same
response shape).

## Critical operational invariant

In `create_topup_payment`, the YooKassa SDK call (`Payment.create`) runs
**before** any DB write. Ordering matters:
- SDK call fails → no DB writes happen, clean state.
- SDK succeeds → record persisted, caller commits transaction.
- Reviewers and future modifiers must NOT move the SDK call into
  `async with session.begin()` block or after `session.flush()` — that
  would create a "real charge, no local record" state if rollback
  happens after SDK success.

A multi-line code comment in `create_topup_payment` documents this
invariant inline.

## Open findings surfaced (deferred)

### Finding 1 — bot handler `topup_pay` is broken-but-reachable

`src/bot/handlers/billing/billing.py:60` registers a live
`@router.callback_query(F.data == "topup:pay", ...)` handler that
calls `yookassa_service.create_payment(amount_rub=..., user_id=...)`.
That dead method instantiates `YookassaPayment` with kwargs the model
no longer has (`amount_rub`, `credits`, `description`,
`confirmation_url`, `idempotency_key`), so any actual click hits a
`TypeError` caught by the handler's `except Exception`.

The plan §0.5 STOP gate triggered on "registered handler". Marina chose
**Option A** — defer the dead-method removal entirely. Consequently:
- `YooKassaService.create_payment` (dead, broken at runtime) is **kept**.
- `tests/smoke_yookassa.py` — likewise kept.
- AST lint test does NOT mark `create_payment` as dead in
  `DEAD_YOOKASSA_METHODS`; that comes when the bot-handler decision is
  resolved.

A separate prompt should decide: migrate `topup_pay` to the new method,
delete the bot topup flow entirely, or accept the latent bug.

### Finding 2 — bot UI displays 3.5% but billing applies 6%

Pre-existing inconsistency. `src/bot/handlers/billing/billing.py:55`
shows `Комиссия: {amount * 0.035:.2f} ₽` to the Telegram user, but
`src/constants/payments.py` defines:
- `YOOKASSA_FEE_RATE = Decimal("0.035")` — actual YK SDK commission.
- `PLATFORM_TAX_RATE = Decimal("0.06")` — ИП УСН 6%.

Both removed `BillingService.create_payment` and new
`YooKassaService.create_topup_payment` apply `PLATFORM_TAX_RATE` (6%) on
top of `desired_balance`. Display ≠ what is charged. Out of scope for
14a; flagged for product/UX decision. Test expectations in
`test_yookassa_create_topup_payment.py` reflect the actual 6% rate
applied by code (assertions `fee_amount == Decimal("6.00")`,
`gross_amount == Decimal("106.00")`), preserving parity with the removed
method.

## Gate baseline (pre → post on feature branch)

- Forbidden-patterns: 17/17 → 17/17 ✓
- Ruff `src/`: 21 errors → 21 errors (no new errors).
- Mypy `src/`: 10 errors / 5 files → 10 errors / 5 files (unchanged).
- Pytest substantive (
  `pytest tests/ --ignore=tests/e2e_api --ignore=tests/unit/test_main_menu.py`
  ):
  - Before: 76F + 17E + 634P + 7S.
  - After: 76F + 17E + 638P + 7S (+4 new integration tests).

## Origins

- `BILLING_REWRITE_PLAN_2026-04-28.md` item 6 (split into 14a/14b).
- `reports/docs-architect/BACKLOG.md` BL-034 entry above.

## Next prompt — 14b (Промт-16)

Webhook consolidation: move `BillingService.process_topup_webhook` into
`YooKassaService.process_webhook`, remove `BillingService.check_payment`,
migrate GET `/topup/{id}/status` to a direct repo read, rewire POST
`/webhooks/yookassa`.

🔍 Verified against: feature branch `fix/billing-rewrite-item-6a-yookassa-consolidation`
📅 Updated: 2026-04-28T00:00:00Z
