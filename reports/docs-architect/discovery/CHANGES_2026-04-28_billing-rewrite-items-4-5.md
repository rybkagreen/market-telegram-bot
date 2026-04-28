# CHANGES — Billing rewrite items 4-5: dead code removal + endpoint DI migration

## What

Dead code removal in `BillingService` (8 methods) and `YooKassaService`
(2 methods), drop of module-level `billing_service` singleton, plus 2
endpoint DI migrations in `api/routers/billing.py`. Items 4-5 of the
12-item billing rewrite plan
(`reports/docs-architect/discovery/BILLING_REWRITE_PLAN_2026-04-28.md`).

## Code changes

### `src/core/services/billing_service.py`
- Deleted methods (all empirically dead — 0 callers anywhere in `src/`):
  - `add_balance_rub`
  - `deduct_balance_rub`
  - `apply_referral_bonus`
  - `apply_referral_signup_bonus`
  - `apply_referral_first_campaign_bonus`
  - `get_referral_stats`
  - `freeze_campaign_funds`
  - `refund_escrow_credits`
- Removed module-level singleton `billing_service = BillingService()`.
- Class docstring updated to drop `add_balance_rub` and
  `apply_referral_bonus` lines (they referenced now-deleted methods).
- Removed orphan section header `# Реферальная программа (Спринт 4)`
  (all three methods under it were deleted).
- No imports removed at file top — every remaining method still uses
  the existing imports.

### `src/core/services/yookassa_service.py`
- Deleted methods: `handle_webhook`, `_credit_user`.
  Confirmed dead in Шаг 0: `handle_webhook` had 0 external callers in
  `src/`; `_credit_user` was called only from `handle_webhook`. Live
  webhook path is `api/routers/billing.py::yookassa_webhook` →
  `BillingService.process_topup_webhook`.
- Removed now-unused imports: `from datetime import UTC, datetime`,
  `from src.db.models.user import User`.

### `src/api/routers/billing.py`
- Imports: added `Depends` (fastapi), `AsyncSession`
  (sqlalchemy.ext.asyncio), `get_db_session` (src.api.dependencies).
- `get_frozen_balance` (`GET /frozen`): migrated to
  `session: Annotated[AsyncSession, Depends(get_db_session)]`. Removed
  inner `async with async_session_factory() as session:` wrapper.
- `get_history` (`GET /history`): same migration.

### `src/api/routers/disputes.py`
- Replaced `from src.core.services.billing_service import billing_service`
  (singleton) with `from src.core.services.billing_service import BillingService`.
- Instantiate `billing_service = BillingService()` locally inside
  `dispute_resolve` before financial-operation block.

### `src/api/routers/admin.py`
- Removed duplicate `from datetime import UTC` at line 373 inside
  `verify_legal_profile` — module-level `from datetime import UTC, datetime`
  at line 12 already provides it.

### Test files
- `tests/unit/test_escrow_payouts.py`: replaced
  `from src.core.services.billing_service import billing_service`
  with `BillingService` import + local instantiation. Test body
  unchanged — local `billing_service` now refers to a module-local
  instance.
- `tests/unit/test_no_dead_methods.py` (new, 79 LOC): AST-level lint
  preventing revival of:
  - 8 deleted BillingService methods
  - 2 deleted YooKassaService methods
  - module-level `billing_service = BillingService()` singleton

## Public contract delta

None. Endpoint behaviour for `/frozen` and `/history` unchanged;
signature change is internal (FastAPI DI). Deleted service methods had
0 in-tree callers, so no behavioural surface is touched.

## What this does NOT do

- Does not introduce `PlanChangeService` (Промт-15).
- Does not consolidate `YooKassaService` topup creation (Промт-14).
- Does not touch frontend credits cleanup (Промт-17).
- Does not modify `/credits`, `/plan`, `/topup`, `/topup/{id}/status`,
  `/webhooks/yookassa` endpoints.
- Does not delete `tests/smoke_yookassa.py` — empirically it calls
  `YooKassaService.create_payment` which is kept; plan's claim was
  incorrect. Surfaced in BL-032.
- Does not delete `BillingService.activate_plan`, `buy_credits_for_plan`,
  `create_payment`, `check_payment` (out of scope).

## Gate baseline (this branch vs. baseline at start of session)

| Gate | Before | After | Plan target |
|---|---|---|---|
| Forbidden-patterns | 17/17 | 17/17 | 17/17 |
| Ruff `src/` | 21 | 21 | ≤21 |
| Mypy `src/` | 10 errors / 5 files | 10 errors / 5 files | ≤10 |
| Pytest substantive | 76F + 17E + 631P | 76F + 17E + 634P | +3 lint tests |
| New `test_no_dead_methods.py` | — | 3 passed | passing |

Pytest invocation: `poetry run pytest tests/ --ignore=tests/e2e_api
--ignore=tests/unit/test_main_menu.py --no-cov` (per CLAUDE.md
"Verification gate language" guidance).

## Origins

- `BILLING_REWRITE_PLAN_2026-04-28.md` items 4-5.
- BL-032 (this session) in `reports/docs-architect/BACKLOG.md`.

## Notes for Промт-14 author

- Plan claimed `tests/smoke_yookassa.py` should be deleted because it
  "calls a dead method". Empirically it calls
  `YooKassaService.create_payment`, which is **kept**. Re-verify
  before Промт-14 schedules its deletion.
- After Промт-14 consolidates `YookassaService` topup creation,
  `POST /topup` endpoint can finally be DI-migrated cleanly (today
  it would be a half-migration since the called service still opens
  its own session).

🔍 Verified against: HEAD of `fix/billing-rewrite-items-4-5` |
📅 Updated: 2026-04-28T00:00:00Z
