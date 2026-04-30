# CHANGES — 2026-04-30 — Remove bot payout flow, replace with portal deeplink (16.3)

## Summary

Series 16.x Group C — architectural fix. Bot payout setup flow removed
completely. Entry-point buttons (cabinet, owner menu, post-completion
notification) now use Telegram WebApp inline buttons that open the
mini_app at `/own/payouts/request`; that mini_app screen is a Phase 1
placeholder that wraps `OpenInWebPortal` and bridges into the web
portal via the existing ticket exchange.

Closes BL-045 (CRIT-1: bot payout FSM accepts financial PII via
`message.text`, echoes plaintext at line 347, persists plaintext at
rest — last leg covered by 16.2 encryption, but the in-flight Telegram
exposure required removal of the flow itself).

## Why

Per project rule "ПД никогда через mini_app/bot": Telegram message
text travels through Telegram's servers in the clear, the bot's
acknowledgement message echoes the requisites back to the chat, and
even with PayoutRequest.requisites encrypted at rest (16.2) the
in-flight exposure remains. The fix is structural: PII setup belongs
in the web portal, never in bot/mini_app.

## Architectural deviation from prompt — surfaced + adopted

Prompt §6 step 4 suggested a server-side `build_portal_deeplink`
helper that calls `POST /api/auth/exchange-miniapp-to-portal` from
the bot. **That endpoint requires
`Depends(get_current_user_from_mini_app)`** — a mini_app JWT, which
the bot does not possess. Calling it from the bot would either fail
auth or require building a parallel "bot-to-portal" exchange path
(new endpoint + new audit surface).

Adopted instead: reuse the Phase 1 mini_app placeholder bridge.
- Bot inline button → `WebAppInfo(url=mini_app_url + /own/payouts/request)`.
- Telegram opens the mini_app at that path.
- The placeholder `mini_app/src/screens/owner/OwnPayoutRequest.tsx` (added
  Phase 1 §1.B.2) wraps `OpenInWebPortal target="/own/payouts/request"`.
- `OpenInWebPortal` exchanges the mini_app JWT for a one-shot ticket
  via `POST /api/auth/exchange-miniapp-to-portal`, then opens
  `{portal_url}/login/ticket?ticket=...&redirect=/own/payouts/request`.
- Net result identical to the prompt's intent, no new server-side
  helper, no new audit surface, security model preserved.

Rest of the prompt's plan executed as written.

## What removed

### Bot handlers (delete)
- `src/bot/handlers/payout/payout.py` (351 LOC) — full delete.
  - `show_payouts` (callback `main:payouts`)
  - `payout_request_start` (callback `payout:request_start`)
  - `payout_select_amount` (callback `payout:amount:*`)
  - `payout_custom_input` (message handler in `entering_amount`)
  - `_show_amount_confirmation` (helper)
  - `payout_confirm` (callback `payout:confirm`)
  - `payout_requisites_input` (message handler in `entering_requisites`)
    — the BL-045 root: lines 281–351 accepted card / phone via
    `message.text`, echoed back at line 347 inside `f"Реквизиты: {requisites}"`.
- `src/bot/handlers/payout/__init__.py` — empty, dir removed entirely.

### FSM states (delete)
- `src/bot/states/payout.py` — `class PayoutStates(StatesGroup)` with
  `entering_amount`, `confirming`, `entering_requisites`.
- `src/bot/states/__init__.py` — removed the `from src.bot.states.payout
  import PayoutStates` line and the `PayoutStates` entry from `__all__`.

### Dead helpers (delete)
- `src/bot/keyboards/payout/payout.py` — `payout_amounts_kb`,
  `payout_confirm_kb`. Defined but never imported anywhere — handler
  built keyboards inline. Dir removed entirely.

### Router registration cleanup
- `src/bot/handlers/__init__.py` — removed `payout_router` import and
  `main_router.include_router(payout_router)` line; updated router-order
  comment to reflect the change.

## What replaced (entry points)

### `src/bot/keyboards/owner/own_menu.py:16`
"💸 Выплаты" button switched from `callback_data="main:payouts"` to
`web_app=portal_webapp("/own/payouts/request")`.

### `src/bot/keyboards/shared/cabinet.py:17-22`
"💸 Запросить вывод" button (shown when `earned_rub >= 1000`) switched
from `callback_data="payout:request_start"` to
`web_app=portal_webapp("/own/payouts/request")`.

### `src/bot/handlers/shared/notifications.py:244-250`
`notify_owner_post_completed` — "💸 Запросить вывод" inline button after
post completion notification switched from `callback_data="payout:request_start"`
to `web_app=portal_webapp("/own/payouts/request")`. Kept the second
"📊 Статистика" button unchanged.

### New helper
- `src/bot/utils/portal_deeplink.py` (32 LOC) — `portal_webapp(target)`
  returns `WebAppInfo(url=mini_app_url + target)`. Single responsibility,
  reused 3 times.

## What kept (out of scope)

- Backend `/api/payouts/*` endpoints — already pinned `web_portal`
  audience in 16.1.
- `PayoutRequest` model + `requisites` `EncryptedString` column — done in
  16.2.
- Web portal payout setup screen + API client — full form, verified
  active at `/own/payouts/request` (181 LOC).
- Outcome notifications:
  - `notify_owner_payout_done` (`notifications.py:260-279`) — system
    message after admin processes payout, no setup PII involved.
- Admin-side payout management:
  - `src/bot/handlers/admin/users.py:41-66` — admin list / approve /
    reject pending payouts; admin views requisites that already exist
    in encrypted DB, no PII entry through bot.
  - `src/bot/handlers/admin/disputes.py:212` — dispute outcome strings
    mentioning payouts.
- Help / info text mentions of "выплаты" in `help.py:12`,
  `contract_signing.py:120`.

## Architecture flow (post-16.3)

```
User (bot)
   │
   │  1. Tap "💸 Выплаты" / "💸 Запросить вывод"
   ▼
Telegram client
   │  WebAppInfo url = https://app.rekharbor.ru/own/payouts/request
   ▼
Mini_app placeholder OwnPayoutRequest.tsx
   │  OpenInWebPortal target="/own/payouts/request"
   │  → POST /api/auth/exchange-miniapp-to-portal  (mini_app JWT, sets ticket)
   ▼
Web portal /login/ticket?ticket=...&redirect=/own/payouts/request
   │  POST /api/auth/consume-ticket  (one-shot, web_portal JWT issued)
   ▼
Web portal /own/payouts/request
   │  User enters amount + requisites in HTTPS form
   │  POST /api/payouts/  (web_portal-only audience, 16.1)
   ▼
PayoutRequest persisted with requisites encrypted (16.2)
```

PII never touches Telegram or the bot at any point in this chain.

## Tests

### Deleted / modified
- `tests/unit/test_fsm_middlewares.py::TestFSMStates::test_payout_states_defined`
  — deleted (the asserted module is gone).
- `tests/unit/test_fsm_middlewares.py::TestFSMStates::test_all_states_importable`
  — removed the `PayoutStates` import + the `assert PayoutStates is not None` line.

### New regression
- `tests/unit/test_fsm_middlewares.py::TestNoBotPayoutFlow::test_payout_handler_module_absent`
  — asserts `src/bot/handlers/payout/` does not exist on disk.
- `tests/unit/test_fsm_middlewares.py::TestNoBotPayoutFlow::test_payout_states_module_absent`
  — asserts `src.bot.states.payout` import raises `ImportError` and that
  `src.bot.states.PayoutStates` attribute does not exist.

Both new tests pass; they are guard-rails against accidental
re-introduction of the bot payout flow.

## CI baseline

| Check | Before (develop ecec072) | After (16.3) |
|-------|--------------------------|--------------|
| `make lint` (ruff src/) | 21 errors | 21 errors |
| `make typecheck` (mypy src/) | 10 errors | 10 errors |
| `pytest tests/unit/test_fsm_middlewares.py` | 1 file, 11 passed / 9 failed (BL-054) | 11 passed / 8 failed |

Net: −1 deleted test, −1 modified test, +2 regression tests. Pre-existing
BL-054 failures (state-name drift, missing `src.bot.states.admin`,
missing `ChannelOwnerStates`, missing `FSM_TIMEOUT` / `THROTTLE_TIME`
constants) untouched. Touched files (`portal_deeplink.py`, `own_menu.py`,
`cabinet.py`, `notifications.py`, `handlers/__init__.py`,
`states/__init__.py`) — 0 ruff / mypy errors.

## Smoke / verification

### Static (Шаг 0 inventory + Шаг 8)
- Ticket bridge endpoints `POST /api/auth/exchange-miniapp-to-portal` +
  `POST /api/auth/consume-ticket` — verified active in
  `src/api/routers/auth.py:219` + `:294`.
- `OpenInWebPortal` component + `useOpenInWebPortal` hook — verified in
  `mini_app/src/components/OpenInWebPortal` + `mini_app/src/hooks/useOpenInWebPortal.ts`.
- `mini_app/src/screens/owner/OwnPayoutRequest.tsx` placeholder wrapping
  `OpenInWebPortal target="/own/payouts/request"` — verified.
- `web_portal/src/screens/owner/OwnPayoutRequest.tsx` (181 LOC, full
  form) — verified.
- `web_portal/src/App.tsx:180` route `own/payouts/request` — verified.
- `web_portal/src/api/payouts.ts` `createPayout` POST `/payouts` — verified.

### Dynamic
- Docker rebuild `api bot` — green (Шаг 10).
- Manual button → mini_app → portal redirect — best-effort manual smoke
  noted in STOP report.

## Deferred / not in scope

- BL-054 (pre-existing test-suite failures: bot-side state-name drift +
  `test_main_menu.py` collection error). Not fixed; touched-file scope
  preserved.
- 16.4 — `UserResponse.referral_code` exposure in `/api/users/me` (BL-050,
  MED-6). Next promt.
- 16.5 — LOW batch (BL-051 etc.). Final clean-up after 16.4.

## Origins

- `PII_AUDIT_2026-04-28.md` § O.1 (CRIT-1).
- BACKLOG.md BL-045 (Open → Closed).
- Project rule "ПД никогда через mini_app/bot".
- Phase 1 ticket-bridge infrastructure
  (`exchange-miniapp-to-portal` + `consume-ticket` + `OpenInWebPortal` +
  per-flow placeholder screens) reused as the deeplink mechanism.
- 16.1 (`/api/payouts/*` web_portal-only) — load-bearing precondition.
- 16.2 (`PayoutRequest.requisites` encryption) — load-bearing
  precondition for any residual plaintext exposure scenarios.

🔍 Verified against: <commit_hash_filled_post_commit> | 📅 Updated: 2026-04-30T00:00:00Z
