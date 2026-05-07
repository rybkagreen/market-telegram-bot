# T1.2.5e — Payout cleanup + dead-code purge + pre-test gates

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07
**Pre-state HEAD:** b7d4589
**Pre-state baseline:** 12F / 997P / 5S / 0E + 21 lint / 14 format / 10 mypy
**Status:** in-progress (commit 8 finalizes)

## Marina decisions

- **Q1-frame=(c)+(d):** full backend dead-code purge (PayoutService methods + PayoutComplianceService skeleton + free function `calculate_payout`) + topup normalize deferred к T1.2.5f.
- **Q2-frame=(a):** delete bot admin payout `approve_payout` / `reject_payout` callbacks; "Выплаты" admin menu button preserved (live `show_pending_payouts` target).
- **Q4-frame=(a):** pre-test gates fix included в this sub-block.
- **Q1-Phase-C=(a):** conftest 7 lint errors accepted as known residual (BL-024 prohibits touching `tests/unit/conftest.py`).
- **Q2-Phase-C=(c):** mediakit_service.py 4 typecheck errors deferred к BACKLOG (orthogonal architectural cleanup).
- **Q3-Phase-C=(b):** commit 7 split в 7a (lint), 7b (format), 7c (typecheck) для cleaner history.

## Commits

### Commit 1 — `refactor(bot): delete empty admin payout approve/reject callbacks`
- **Hash:** c9d3175
- **Files:** `src/bot/handlers/admin/users.py` (-12 lines)
- **Verify:** 12F / 997P / 5S / 0E (+ unchanged 21 lint / 14 format / 10 mypy)
- **Note:** First gate run showed 13F due к flake `tests/unit/test_content_filter.py::test_check_case_insensitive` (Mistral non-determinism, `0.25 == 1.0`). Re-run confirmed 12F restoration. Flake unrelated к commit diff.

### Commit 2 — `refactor(mini_app): remove payout screens, hooks, types, redirect routes`
- **Hash:** 79de007
- **Files (delete, 5):** `OwnPayouts.tsx`, `OwnPayouts.module.css`, `OwnPayoutRequest.tsx`, `api/payouts.ts`, `hooks/queries/usePayoutQueries.ts`
- **Files (modify, 7):** `App.tsx` (imports + routes + stale comment), `OwnMenu.tsx` (Выплаты MenuButton + dead `useMe`/`formatCurrency` imports), `hooks/queries/index.ts` (barrel export), `lib/types.ts` (`PayoutStatus`+`Payout` interface), `lib/constants.ts` (`WITHDRAWAL_FEE`), `lib/formatters.ts` (`calcWithdrawalFee` + `WITHDRAWAL_FEE` import), `screens/common/Help.tsx` (FAQ rewrite to portal-redirect text)
- **Diff:** 13 files, +8 / -318 lines (incl. CHANGES placeholder add line)
- **Verify:** 12F/997P/5S/0E (match) + 21 lint / 14 format / 10 mypy unchanged

### Commit 3 — `docs(bot): update stale 16.3 payout-flow comments`
- **Hash:** TBD (post-commit)
- **Files:** `src/bot/handlers/__init__.py` (router-include comment lines 29-31), `tests/unit/test_fsm_middlewares.py` (TestNoBotPayoutFlow class docstring lines 100-105)
- **Reason:** Both comments described the bot opening mini_app at `/own/payouts/request` for OpenInWebPortal redirect — the mini_app screen was deleted in commit 2 (79de007), and the actual mechanism was always `build_portal_deeplink` direct minting (BL-055). Comments now describe the actual flow.
- **Verify:** TBD (expected 12F/997P/5S/0E preserved — comment-only edits)

### Commit 4 — `refactor(payout): delete dead PayoutService methods`
- **Hash:** 516415d
- **Files (modify, 2):** `src/core/services/payout_service.py` (-684 lines net: 11 dead methods + 3 unused exception classes + 8 orphan imports), `tests/integration/test_api_endpoints.py` (-45 lines: TestPayoutService class with 2 active + 2 SKIPPED tests)
- **Methods deleted (11):** `calculate_payout` (instance), `get_owner_balance`, `get_owner_payouts`, `create_pending_payout`, `process_payout`, `mark_payout_paid`, `cancel_payout`, `request_payout_for_placement`, `check_velocity`, `create_payout` (instance — also drops S-48 `async with session.begin()` violation), `calculate_payout_with_tax`
- **Methods retained (4 + __init__):** `complete_payout`, `reject_payout`, `approve_request`, `reject_request` — all live via admin router (`approve_request`/`reject_request` chain into internal complete/reject_payout)
- **Exceptions removed (3):** `InsufficientFundsError`, `PayoutAPIError`, `UserNotFoundError` — all unused after deletion
- **Imports cleaned:** ROUND_HALF_UP, COOLDOWN_HOURS, MIN_PAYOUT, PAYOUT_FEE_RATE, VELOCITY_MAX_RATIO, VELOCITY_WINDOW_DAYS, VelocityCheckError, User, PayoutRepository
- **Verify:** 12F/995P/3S/0E (match) + 21 lint / 14 format / 10 mypy unchanged

### Commit 5 — `refactor(payout): delete PayoutComplianceService skeleton + clean stale comments`
- **Hash:** 17d8f1f
- **Files (delete, 2):** `src/core/services/payout_compliance_service.py` (5b.7b SKELETON, ~190 LOC), `tests/unit/test_payout_compliance_service.py` (145 LOC, 7 tests)
- **Files (modify, 2):** `src/core/services/legal_compliance_service.py` (line 79 comment — remove "(handed off to PayoutComplianceService)" reference), `src/core/services/gates/payout_gates.py` (lines 12-14 docstring — remove "future PayoutComplianceService" reference)
- **Reason:** Skeleton had empty registries `_PAYOUT_TRANSITION_GATES = {}` / `_PAYOUT_CREATE_GATES = {}` and ZERO production callers (verified via grep — only the test file imports it). Phase 5 / 5b.7 will recreate (see Deferred section).
- **Verify:** 12F/988P/3S/0E (match) + 21 lint / 14 format / 10 mypy unchanged

### Commit 6 — `refactor(payments): delete unused free function calculate_payout`
- **Hash:** 1dd496c
- **Files (modify, 3):** `src/constants/payments.py` (-21 lines: function deleted), `tests/unit/test_billing.py` (-30 lines: TestPayoutCalculation class — 4 tests; PAYOUT_FEE_RATE import dropped — no longer used after class delete), `tests/unit/test_payments_constants.py` (-20 lines: TestCalculatePayout class — 3 tests; PAYOUT_FEE_RATE import dropped — no longer used)
- **Reason:** Free function в `src/constants/payments.py:135` had zero callers in `src/` (verified via grep). Only test consumers (TestPayoutCalculation in test_billing.py, TestCalculatePayout in test_payments_constants.py — 7 tests total) referenced it. Removing function + dependent test classes.
- **Surviving in payments.py:** `calculate_topup_payment`, `get_format_price`, `is_format_allowed_for_plan`, all constants (PAYOUT_FEE_RATE, MIN_PAYOUT, MAX_TOPUP, MIN_TOPUP, COOLDOWN_HOURS, VELOCITY_MAX_RATIO, VELOCITY_WINDOW_DAYS, FORMAT_MULTIPLIERS, PLAN_LIMITS) — kept (still used by router/service code).
- **Surviving test classes:** TestBillingServiceInit, TestCalculateTopupPreview, TestFreezeEscrowConstants, TestEscrowReleaseLocation, TestPlatformCommission, TestVelocityCheckConstants (test_billing.py); TestCalculateTopupPayment, TestGetFormatPrice, TestIsFormatAllowedForPlan, TestPlanLimits (test_payments_constants.py).
- **Verify:** 12F/981P/3S/0E (match) + 21 lint / 14 format / 10 mypy unchanged

### Commit 7a — `chore(lint): clear residual ruff lint after dead-code purge (excl. conftest)`
- **Hash:** d84780b
- **Files (modify, 7):** `src/api/routers/document_validation.py` (SIM102 line 107 — combine if; E712 line 263 — replace `== True` с `.is_(True)`), `src/bot/handlers/owner/channel_owner.py` (SIM108 line 82 — collapse к ternary), `src/tasks/placement_tasks.py` (F841 line 380 — drop unused `repo`), `tests/mocks/yookassa_mock.py` (B903 lines 8, 15 — convert MockConfirmation/MockAmount к dataclass), `tests/tasks/test_placement_escrow.py` (4× N806 — rename `mock_scalars_AB`/`mock_result_AB`/`mock_scalars_C`/`mock_result_C` → lowercase; 2× N817 — replace `as PS` с full `PlacementStatus` name), `tests/unit/test_fsm_middlewares.py` (E302 line 39 — add blank line), `tests/unit/test_payments_constants.py` (B007 line 151 — rename `plan` → `_plan`)
- **NOT touched:** `tests/unit/conftest.py` (7 errors stay per Marina Q1=(a) Phase C — intentional asyncio policy ordering, BL-024 prohibition).
- **Verify:** lint 21 → **7** (conftest residual); format 14 → **13** (one file incidentally cleaned by edit); pytest 12F/981P/3S/0E (unaffected by lint-only edits — verified post-7b)

### Commit 7b — `chore(format): apply ruff format to 13 drifted files`
- **Hash:** TBD (post-commit)
- **Method:** `make format` (`poetry run ruff format src/ tests/`)
- **Files reformatted (13):** `src/api/routers/channels.py`, `src/bot/handlers/owner/channel_owner.py`, `src/core/services/legal_compliance_service.py`, `src/db/models/legal_profile.py`, `tests/integration/api/test_admin_payouts.py`, `tests/integration/test_audit_log_repo.py`, `tests/test_api_channel_settings.py`, `tests/test_streak_bonus.py`, `tests/unit/api/test_channels_create.py`, `tests/unit/test_advertiser_gates.py`, `tests/unit/test_bot_channel_owner.py`, `tests/unit/test_legal_compliance_service.py`, `tests/unit/test_owner_gates.py` (commit 7a's `test_fsm_middlewares.py` E302 edit incidentally cleaned that file).
- **Verify:** TBD (expected pytest 12F/981P/3S/0E unchanged; lint 7 (conftest); format 13 → **0**; mypy 10 → 10)

### Commit 7c — `chore(typecheck): clear 6 of 10 mypy errors (mediakit deferred)`
- **Hash:** TBD (post-commit)
- **Files (modify, 4 src + 1 helper):** `src/bot/handlers/owner/channel_owner.py:457` (added explicit `if ch is None: return` guard before `.username`/`.title` access — closes 2 union-attr errors), `src/tasks/ord_tasks.py:59` (dropped commented-out `channel_id`/`post_url` kwargs from `report_publication` call to match service signature — closes 2 call-arg errors), `src/core/services/analytics_service.py:392-411` (typed `messages` list with full `SystemMessageTypedDict | UserMessageTypedDict | AssistantMessageTypedDict | ToolMessageTypedDict` union to satisfy SDK list-invariance constraint — closes 1 arg-type error), `src/bot/handlers/advertiser/campaigns.py:172` (no-op — issue resolved by adding `parse_mode` to helper), `src/bot/utils/safe_callback.py:10-32` (extended `safe_callback_edit` signature to accept optional `parse_mode: str | None = None`, threaded into both `edit_text` and `answer` fallback — closes 1 call-arg error).
- **NOT touched:** `src/core/services/mediakit_service.py` (4 errors deferred per Marina Q2=(c) — `TelegramChat` model attrs `last_avg_views`/`last_post_frequency`/`price_per_post` don't exist; orthogonal cleanup target, see Deferred section).
- **Verify:** TBD (expected pytest 12F/981P/3S/0E unchanged; lint 7 (conftest); format 0; mypy 10 → **4** — only mediakit residual)

### Commit 8 — TBD (closure docs + tmp cleanup)

## Deferred to production launch

(filled by commit 8 finalizer)

## Verification footer

(filled by commit 8 finalizer)
