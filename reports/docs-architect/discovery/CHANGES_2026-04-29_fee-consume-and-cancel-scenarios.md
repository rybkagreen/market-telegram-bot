# CHANGES — Frontend fee-config consume + bot scenario fix + middleware fail-closed (combined 15.10 + 15.11.5)

🔍 Verified against: `c95908e` | 📅 Updated: 2026-04-29

## What

Combined deployable checkpoint closing three related findings as a
single PR. Marina chose option (A) for Часть B after inventory
surfaced the prompt-as-written would have broken 4 callers; the
real cancel-scenarios bug was a single-character mis-routing in the
bot handler.

## Affected files

### Часть A — Frontend /fee-config consume (15.10)

- **`web_portal/src/api/billing.ts`** — added `getFeeConfig()` +
  `FeeConfigResponse` type (mirrors `/api/billing/fee-config`
  nested response: `{topup, placement, cancel}`).
- **`mini_app/src/api/billing.ts`** — same.
- **`web_portal/src/hooks/useBillingQueries.ts`** — added
  `useFeeConfig()` (5 min `staleTime`, 30 min `gcTime`).
- **`mini_app/src/hooks/queries/useBillingQueries.ts`** — same.
- **`web_portal/src/screens/shared/TopUpConfirm.tsx`** — `0.035`
  literal (line 66) → `YOOKASSA_FEE`. Label
  `'Комиссия ЮKassa (3,5%)'` → `formatRatePct(YOOKASSA_FEE)`.
- **`web_portal/src/screens/shared/TopUp.tsx`** — `const FEE_RATE
  = 0.035` → `YOOKASSA_FEE`. Three method-detail strings
  `'комиссия 3,5%'` → `${FEE_LABEL}`. Summary row label updated.
- **`web_portal/src/screens/owner/OwnPayoutRequest.tsx`** — `const
  PAYOUT_FEE_RATE = 0.015` → `PAYOUT_FEE`. Two `'Комиссия 1,5%'`
  strings → `formatRatePct(PAYOUT_FEE)`.
- **`web_portal/src/screens/owner/OwnPayouts.tsx`** —
  `'комиссия 1,5%'` → `formatRatePct(PAYOUT_FEE)`.
- **`web_portal/src/screens/common/Help.tsx`** — FAQ entry
  hardcoded `'1,5%'` → template literal with
  `formatRatePct(PAYOUT_FEE)`.
- **`web_portal/src/screens/advertiser/AdvertiserFrameworkContract.tsx`**
  — paragraph hardcoding `20%`, `1,5%`, `21,2%`, `78,8%` → all
  derived from `PLATFORM_COMMISSION_GROSS`, `SERVICE_FEE`,
  `PLATFORM_TOTAL_RATE`, `OWNER_NET_RATE` constants.
- **`mini_app/src/screens/common/TopUpConfirm.tsx`** — label
  `'Комиссия ЮKassa (3,5%)'` → `formatRatePct(YOOKASSA_FEE)`.
- **`mini_app/src/screens/owner/OwnPayouts.tsx`** —
  `'Комиссия 1,5%'` → `formatRatePct(WITHDRAWAL_FEE)`.
- **`mini_app/src/screens/common/Help.tsx`** — FAQ entry
  hardcoded `1,5%` → `formatRatePct(WITHDRAWAL_FEE)`.
- **`landing/src/lib/constants.ts`** — added
  `CANCEL_REFUND_ADVERTISER = 0.50`.
- **`landing/src/components/Compliance.tsx`** — hardcoded `50%`
  / `1.5%` in legal copy → `formatRatePct(...)` calls.
- **`web_portal/src/screens/owner/OwnRequests.tsx`** — removed
  stale "Промт 15.7" explanatory comment containing hardcoded
  `1.5%` (conflicted with new lint rule, redundant per CLAUDE.md
  "no comments explaining what code does").
- **`mini_app/src/screens/owner/OwnRequestDetail.tsx`** — same.
- **`src/api/routers/contracts.py`** — added inline comment to
  `get_platform_rules_text` documenting the Phase 1 §1.B.2
  carve-out (text-only legal content, both audiences consume).
- **`scripts/check_forbidden_patterns.sh`** — 14 new patterns:
  - 6 numeric-literal patterns (`0.035`, `0.015` × 3 frontends).
  - 8 string-percentage patterns (`3,5%`, `1,5%` × 3 frontends;
    `78,8%`, `21,2%` × web_portal).
  - All exclude `lib/constants.ts` (single source of truth).

### Часть B — Bot handler scenario string corrected (15.11.5)

- **`src/bot/handlers/placement/placement.py:622`** —
  `scenario="after_escrow_before_confirmation"` →
  `scenario="after_confirmation"`. One-line edit. UI promised
  "Возврат 50%" but routed to the 100% scenario; now routed to
  the 50/40/10 scenario.
- **`tests/test_bot_cancel_scenario_consistency.py`** (new) —
  4 source-inspection tests: bot handler uses `after_confirmation`,
  UI text mentions 50%, auto-cancel tasks still use
  `after_escrow_before_confirmation` (100% to advertiser, owner
  at fault), disputes still use `after_confirmation` for partial
  verdicts.

### Часть C — Middleware fail-closed (mini-fix)

- **`src/bot/middlewares/acceptance_middleware.py`** —
  `needs_accept_rules` exception branch changed from
  `return await handler(event, data)` (fail-open) to: log + send
  `TECHNICAL_ERROR_TEXT` notice + `return None` (fail-closed).
  Sub-stages re-numbered 13a-13d to follow BL-037 pattern. New
  module-level constant `TECHNICAL_ERROR_TEXT`.
- **`tests/test_acceptance_middleware_fail_closed.py`** (new) —
  3 tests: fail-closed on exception, pass-through on
  `needs=False`, block on `needs=True` (non-exempt).

## Business logic impact

- **Bot user-initiated cancel from escrow** now correctly applies
  the 50/40/10 split. Previously the user got a silent 100% refund
  while UI promised 50%. (DB пустая → no real users affected on
  deploy.)
- **Auto-cancel paths** (publish failure, SLA timeout, stuck escrow
  recovery): UNCHANGED. Still 100% advertiser refund — owner is at
  fault, advertiser made no choice to cancel.
- **Disputes "partial" verdict**: UNCHANGED. Admin-resolved 50/40/10.
- **Bot middleware** now blocks user with technical-error notice on
  any `needs_accept_rules` exception, instead of silently letting
  the handler run. Trade-off: transient DB errors will block
  legitimate users until DB recovers; accepted per Marina (safer
  than silent fail-open once real users exist).

## New/changed API/FSM/DB contracts

- **No DB schema changes.**
- **No FSM changes.**
- **API additions:**
  - `GET /api/billing/fee-config` — already existed (Промт 15.7).
    Now consumed via `useFeeConfig` hook in both frontends.
- **No new endpoints, no removed endpoints.**

## Sub-stage tracking (BL-037 application)

- `AcceptanceMiddleware.__call__`:
  - 13a — extract `telegram_id` from `event_from_user`.
  - 13b — `UserRepository.get_by_telegram_id`; pass-through on
    None (new user → onboarding).
  - 13c — `ContractService.needs_accept_rules`; if False
    pass-through; if True and event non-exempt, send accept
    prompt + return None.
  - 13d — exception branch: log + send `TECHNICAL_ERROR_TEXT` +
    return None (fail-closed).

## Surfaced finding (informational, not requiring action now)

The semantic naming of cancel scenarios is confusing:
- `after_escrow_before_confirmation` actually means "system
  decided to cancel after escrow but before publication
  confirmed" (refund 100% to advertiser, owner at fault).
- `after_confirmation` actually means "advertiser CONFIRMED their
  own cancellation" (refund 50/40/10).

The naming makes it look like a publication-state distinction,
but it's actually an actor-distinction (system vs advertiser).
Renaming for clarity is deferred — out of scope here, would
require coordinated edit to BillingService + 4 callers +
dispute flow.

## Gate baseline (pre → post)

| Gate | Pre | Post | Notes |
|---|---|---|---|
| Forbidden-patterns | 17/17 | 31/31 | +14 patterns for TS fee literals |
| Ruff `src/` | 21 | 21 | At ceiling, no regression |
| Mypy `src/` | 10 | 10 | At ceiling, no regression |
| Pytest baseline | 76F + 17E + 661P + 7S | 76F + 17E + 668P + 7S | +7 new tests, all passing |

## BACKLOG / CHANGELOG

- BL-040 added (this session).
- CHANGELOG `[Unreleased]` updated.

## Origins

- PLAN_centralized_fee_model_consistency.md (Промт 15.10 + 15.11.5).
- 15.7 priority finding — `TopUpConfirm.tsx:66` literal `0.035`.
- BL-039 surfaced finding — middleware fail-mode.
- 2026-04-29 inventory — bot UI/DB scenario mismatch (root cause:
  one-line scenario string in bot handler, NOT BillingService logic).

## Next prompt — 15.11

Dead act-templates wire через legal_status. 5 templates without
callers: `act_advertiser`, `act_owner_fl`, `act_owner_ie`,
`act_owner_le`, `act_owner_np` — wire через legal_status branching.

🔍 Verified against: `c95908e` | 📅 Updated: 2026-04-29
