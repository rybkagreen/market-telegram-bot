# CHANGES — Centralized fee config + new fee model (15.7 / 5)

## What

First of 5-prompt rewrite to fix fee inconsistency between code and
legal templates. This prompt: **backend only**.

New fee model (locked):
- Topup: 3.5% YooKassa pass-through, platform earns 0.
- Placement success: Owner = 78.8%, Platform = 21.2% (20% commission +
  1.5% service fee from owner gross share).
- Cancel `after_confirmation`: 50% advertiser / 40% owner / 10% platform.

## Code changes

### `src/constants/fees.py` (new)
Single source of truth for all fee/tax rates. Documented as legal
contract constants — changes require version bump and re-acceptance
flow (15.9 territory).

Constants:
- `YOOKASSA_FEE_RATE = 0.035`
- `PLATFORM_COMMISSION_RATE = 0.20`, `OWNER_SHARE_RATE = 0.80`
- `SERVICE_FEE_RATE = 0.015` (withheld from owner gross share)
- `CANCEL_REFUND_ADVERTISER_RATE = 0.50`,
  `CANCEL_REFUND_OWNER_RATE = 0.40`,
  `CANCEL_REFUND_PLATFORM_RATE = 0.10`
- `NPD_RATE_FROM_INDIVIDUAL = 0.04`, `NPD_RATE_FROM_LEGAL = 0.06`
- `PLATFORM_USN_RATE = 0.06`

### `src/constants/payments.py`
- Removed `PLATFORM_COMMISSION` (0.15), `OWNER_SHARE` (0.85),
  `PLATFORM_TAX_RATE` (0.06), top-level `YOOKASSA_FEE_RATE` (last
  moved into `fees.py`; `calculate_topup_payment` re-imports it locally).
- Kept `PAYOUT_FEE_RATE = 0.015` (withdrawal fee — separate from
  placement service fee semantically).

### `src/constants/legal.py`
- Removed `NPD_RATE_FROM_LEGAL`/`NPD_RATE_FROM_INDIVIDUAL` (moved to
  `fees.py`).
- `VAT_RATE`/`NDFL_RATE` retained — out of scope for this prompt.

### `src/constants/__init__.py`
- Re-exported `OWNER_SHARE_RATE` and `PLATFORM_COMMISSION_RATE` from
  `fees.py` (replacing old names).

### `src/core/services/billing_service.py`
- `release_escrow`: applies new split — owner net 78.8%, platform total
  21.2%. Service fee tracked separately in `meta_json` for audit
  (final_price / owner_gross / service_fee / owner_net /
  platform_commission / platform_total).
- `refund_escrow` `after_confirmation` scenario: changed
  `Decimal("0.50")`/`Decimal("0.425")` to imported
  `CANCEL_REFUND_ADVERTISER_RATE`/`CANCEL_REFUND_OWNER_RATE`. Effective
  split now 50/40/10 (was 50/42.5/7.5).
- `refund_escrow` `before_escrow` and `after_escrow_before_confirmation`:
  unchanged (no Decimal literals to swap; behavior preserved 100/0/0).

### `src/core/services/yookassa_service.py`
- `create_topup_payment`: imports `YOOKASSA_FEE_RATE` from `fees.py`
  (was `PLATFORM_TAX_RATE` 6%).

### `src/core/services/payout_service.py`
- `payout_percentage`/`platform_percentage` now use `OWNER_SHARE_RATE`
  (0.80) and `PLATFORM_COMMISSION_RATE` (0.20). Was 0.85/0.15.

### `src/api/routers/billing.py`
- New endpoint `GET /api/billing/fee-config` — public, returns nested
  JSON `{topup, placement, cancel}` with all rates.

### `src/api/routers/channel_settings.py`,
### `src/bot/handlers/admin/disputes.py`,
### `src/bot/handlers/billing/billing.py`,
### `src/bot/handlers/placement/placement.py`,
### `src/core/services/analytics_service.py`,
### `src/core/services/placement_request_service.py`
- All call-sites updated: `OWNER_SHARE` → `OWNER_SHARE_RATE`,
  `PLATFORM_COMMISSION` → `PLATFORM_COMMISSION_RATE`. Imports moved
  from `src.constants.payments` → `src.constants.fees`.
- `placement.py:592` cancel display calc uses
  `CANCEL_REFUND_ADVERTISER_RATE` (was `Decimal("0.50")`).
- `billing/billing.py:55` topup keyboard text uses `YOOKASSA_FEE_RATE`
  (was inline `Decimal("0.035")`/`Decimal("1.035")`).

### Tests
- `tests/unit/test_no_hardcoded_fees.py` (new) — AST lint forbidding
  hardcoded fee Decimal literals in `src/` outside the constants
  area / tax / scoring / config modules. Float lint kept narrow
  (3.5%/78.8%/21.2% only) to avoid PDF/AI/threshold false positives.
- `tests/unit/test_fee_constants.py` (new) — mathematical consistency
  invariants (sums == 1.00, computed owner net 78.8%, computed platform
  total 21.2%, concrete 1000-₽ trace 788/212, concrete cancel 500/400/100).
- Updated assertions in existing tests:
  - `tests/test_constants.py`: 0.85/0.15/0.06 → 0.80/0.20 + new
    `PLATFORM_USN_RATE` test.
  - `tests/unit/test_billing.py::TestPlatformCommission`: split
    assertions migrate to net/total model (78.8%/21.2%).
  - `tests/unit/test_placement.py::TestSelfDealingPrevention`: gross
    split 0.80/0.20 → 8000/2000 on 10000 ₽.
  - `tests/unit/test_payments_constants.py`: drop unused old imports.
  - `tests/test_billing_service.py`: net split formula in `test_owner_plus_platform_equals_final_price`.
  - `tests/unit/test_escrow_payouts.py`: `earned_rub == 425` → `394.00`
    (78.8% of 500).
  - `tests/integration/test_yookassa_create_topup_payment.py`: 106.00 →
    103.50, 6.00 → 3.50.
  - `tests/integration/test_api_endpoints.py::TestPayoutService`:
    150/850 → 200/800; 849.15/149.85 → 799.20/199.80.

## Public contract delta

`POST /api/billing/topup`:
- User now pays `desired_balance × 1.035`. Was `× 1.06`.
- Response shape unchanged.

`Escrow release` (internal flow, no direct API):
- Owner credited with 78.8% of `final_price`. Was 85%.
- Platform earns 21.2%. Was 15%.

`Cancel post-confirmation`:
- Owner compensation: 40% of `final_price`. Was 42.5%.
- Platform: 10% (remainder). Was 7.5%.
- Advertiser refund: 50% (unchanged).

`GET /api/billing/fee-config` (new endpoint):
- Returns nested JSON with `topup`/`placement`/`cancel` rates, all as
  Decimal-formatted strings. No authentication required.

## Critical operational notes

- Legal templates **still говорят 20%/80%** (target model — already
  matches code now). Templates **do NOT yet upomянают 1.5% service fee**
  — addressed in 15.8.
- Frontend **still hardcodes 3.5% / 6%** at multiple places — addressed
  in 15.10.
- Acceptance flow ignores `CONTRACT_TEMPLATE_VERSION` — addressed in
  15.9.
- Until 15.8-15.10 complete, system is in **consistent backend** /
  **inconsistent frontend+templates** state. Real prod launch should
  wait for completion of all 5 prompts.

## Surfaced findings (deferred)

1. `refund_escrow` scenario `after_escrow_before_confirmation` still
   gives 100/0/0 (matches `before_escrow`). Marina's "post-escrow
   pre-publish = 50/40/10" rule is not wired here yet. Pre-existing
   UI/backend drift: bot in `placement.py:632` shows "Возврат 50%"
   but service credits 100%.
2. `refund_escrow` `after_confirmation` semantically is post-publish.
   Marina's rule says post-publish = 0%. Currently returns 50/40/10 —
   defer for follow-up prompt.
3. VAT rate `Decimal("0.22")` hardcoded at `billing_service.py:790`
   (`vat_amount = platform_fee * 0.22`) — separate concept (НДС);
   `0.22` not in forbidden lint set.
4. `tax_repo.py` / `tax_aggregation_service.py` use `Decimal("0.15")`
   for income tax — allowlisted in AST lint (different concept).
5. Reputation scoring weights and PDF coords keep raw float literals;
   AST float lint narrowed to {0.035, 0.788, 0.212} only.
6. `analytics_service.py` aggregates historical
   `final_price * OWNER_SHARE_RATE` — switching the constant value
   retroactively re-displays old earnings at 80% instead of 85%.
   Acceptable pre-prod (CLAUDE.md "Migration Strategy" — no real users
   yet).

## Gate baseline

| Gate | Pre | Post |
|------|------|------|
| Forbidden-patterns | 17/17 | 17/17 |
| Ruff `src/` errors | 21 | 21 |
| Mypy errors / files | 10 / 5 | 10 / 5 |
| Pytest (excl e2e_api, test_main_menu) | 76F + 17E + 640P | 76F + 17E + 650P (+10 new fee tests) |

`make ci-local` invocation:
`poetry run pytest tests/ --ignore=tests/e2e_api --ignore=tests/unit/test_main_menu.py --no-cov`.

## BACKLOG / CHANGELOG

- BL-035 added (this session, RESOLVED).
- CHANGELOG entry added under `[Unreleased]`.

## Origins

- BILLING_REWRITE_PLAN_2026-04-28.md.
- PLAN_centralized_fee_model_consistency.md.
- BL-034 Finding 2 (fee display inconsistency — partial resolution
  here, full resolution in 15.10 frontend).

## Next prompt — 15.8

Legal templates Jinja2 injection + version bump 1.0 → 1.1. Templates
will read fee values from `src/constants/fees.py` via
`ContractService.render_*` methods. Adds "Редакция от X, версия Y.Z" +
115-ФЗ + юрисдикция.

🔍 Verified against: HEAD on `fix/centralized-fee-model` | 📅 Updated: 2026-04-28
