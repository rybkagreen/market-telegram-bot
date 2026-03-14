# Changelog

All notable changes to RekHarborBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### v4.3 - 2026-03-14

#### P01 - Constants, Settings, Repositories
- **Added** helper functions to `constants/payments.py`:
  - `calculate_topup_payment(desired)` - YooKassa fee calculation (3.5%)
  - `calculate_payout(gross)` - Payout fee calculation (1.5%)
  - `get_format_price(base_price, fmt)` - Format multiplier pricing
  - `is_format_allowed_for_plan(plan, fmt)` - Plan format validation
- **Added** v4.3 settings: `DISPUTE_CHECK_INTERVAL_MINUTES`, `POST_MONITORING_MIN_LIFE_RATIO`
- **Removed** deprecated `CRYPTOBOT_TOKEN`, `STARS_ENABLED` (YooKassa only)
- **Fixed** `currency_rates` property to use `rub_per_*` rates
- **Tests**: 22 unit tests for payment constants

#### P02 - BillingService + PayoutService
- **Fixed** SIM102 ruff error in `payout_service.py` (combined nested if statements)
- **Verified** ESCROW-001: `release_escrow()` ONLY called in `delete_published_post()`
- **Verified** financial constants:
  - OWNER_SHARE = 0.85 (85%)
  - PLATFORM_COMMISSION = 0.15 (15%)
  - PAYOUT_FEE_RATE = 0.015 (1.5%)
  - YOOKASSA_FEE_RATE = 0.035 (3.5%)
- **Tests**: 17 unit tests for billing calculations
- **Total P02 tests**: 39 passed, 0 failed

#### P03 - PlacementRequestService + PublicationService + ReputationService
- **Fixed** 8 ruff errors (SIM102, SIM103, SIM108, SIM110) in services:
  - `placement_request_service.py`: 2 fixes (nested if, for loop)
  - `reputation_service.py`: 6 fixes (nested if, ternary operator)
- **Verified** ESCROW-001: `release_escrow()` ONLY in `delete_published_post()`
- **Verified** self-dealing prevention in `create_request()`
- **Verified** format multipliers: post_24h=1.0, post_48h=1.4, post_7d=2.0, pin_24h=3.0, pin_48h=4.0
- **Verified** reputation system:
  - Score range: [0.0, 10.0], SCORE_AFTER_BAN = 2.0
  - Ban duration: 7 days, PERMANENT_BAN_VIOLATIONS = 5
  - Deltas: publication=+1, review_5star=+2, cancel_after=-20, reject_invalid_3=-20
- **Tests**: 22 unit tests for placement services
- **Total P03 tests**: 22 passed, 0 failed

---

## [v4.2] - 2026-03-13

### Financial Model v4.2
- Platform commission: 15% (OWNER_SHARE = 85%)
- YooKassa fee: 3.5% (paid by user)
- Payout fee: 1.5%
- Tax: УСН 6% (not NPD 4%)
- MIN_TOPUP: 500 ₽, MIN_PAYOUT: 1000 ₽, MIN_CAMPAIGN_BUDGET: 2000 ₽
