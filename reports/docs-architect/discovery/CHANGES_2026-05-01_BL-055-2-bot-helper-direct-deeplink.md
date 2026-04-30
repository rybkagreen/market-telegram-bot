---
backlog: BL-055
commit: 2/3 — bot helper rewrite + tests
date: 2026-05-01
branch: feat/bl-055-direct-bot-to-portal-exchange
---

# CHANGES — BL-055 Commit 2: bot helper direct deeplink

Rewires the bot's payout button so it now opens the portal directly via
the new `/api/auth/exchange-bot-token-to-portal` endpoint (Commit 1),
replacing the WebAppInfo-into-mini_app placeholder hop.

## Affected files

| File | Type | Notes |
|---|---|---|
| `src/bot/utils/portal_deeplink.py` | rewritten | drops sync `portal_webapp(target) -> WebAppInfo`; adds `async build_portal_deeplink(...) -> str` + `PortalDeeplinkError`; httpx-based with injectable client for tests |
| `src/bot/keyboards/owner/own_menu.py` | edited | accepts new `payout_url: str \| None` kwarg; falsy → button omitted; uses `InlineKeyboardButton(url=…)` instead of `web_app=…` |
| `src/bot/keyboards/shared/cabinet.py` | edited | same pattern; gating logic now `earned_rub >= 1000 AND payout_url` |
| `src/bot/handlers/shared/cabinet.py` | edited | awaits `build_portal_deeplink` once before rendering cabinet; soft-fails to None on `PortalDeeplinkError` (warn-log) |
| `src/bot/handlers/shared/start.py` | edited | same pattern for owner-menu render path |
| `src/bot/handlers/shared/notifications.py` | edited | `notify_owner_post_completed` mints URL inline; same warn-log fallback |
| `tests/unit/test_bot_portal_deeplink.py` | NEW | 8 tests — happy path, signature byte-equality with verifier, every HTTP failure mode raises `PortalDeeplinkError` |

## Business logic / contract impact

### User-visible behaviour change

**Before BL-055.** Bot inline button (Запросить вывод / Выплаты / 💸):
WebAppInfo → mini_app placeholder `/own/payouts/request` → mini_app
mints ticket via `/api/auth/exchange-miniapp-to-portal` → opens portal
in external browser.

**After BL-055.** Bot mints portal URL server-side at button-build time,
attaches it to a regular `url=` button. Tap → external browser opens
portal directly, exchanges ticket, lands on `/own/payouts/request`.

UX difference for the user: opens external browser immediately
(skipping a Telegram WebApp shell). One fewer client-side roundtrip.

### TTL note (documented in `portal_deeplink.py` module docstring)

The minted URL carries a ticket with TTL =
`settings.ticket_jwt_ttl_seconds` (default 300 s). A button that the
user taps within 5 minutes lands authenticated. Beyond 5 minutes, the
portal returns 401 and the user re-opens the bot menu to mint a fresh
URL. Same TTL the existing exchange-miniapp ticket already had —
behaviour parity, not a regression.

### Soft-fail behaviour

If the API endpoint is unreachable (`httpx.HTTPError`), returns
non-2xx, or returns malformed JSON, the helper raises
`PortalDeeplinkError`. All three callers catch it and:
- Log `…_payout_button_skipped` with the error reason.
- Continue rendering the rest of the keyboard with the button omitted.

This is a deliberate UX trade-off: the cabinet/menu must still render
even if a transient API hiccup happens. Users who notice the missing
button can `/cabinet` again and the helper retries.

## Adaptations applied (Type 2)

- **Internal API base URL.** The helper resolves to
  `settings.internal_api_base_url + /api/auth/exchange-bot-token-to-portal`
  (default `http://api:8001/...`). Bot calls API through Docker DNS,
  bypassing public nginx + Cloudflare.
- **Soft-fail model.** Plan A5 didn't specify failure semantics; we
  surface `PortalDeeplinkError` and let callers decide. Picked because
  hard-failing the entire keyboard render on a transient HTTP issue
  would be a worse UX regression than a missing button.

## Adjacent improvements (Type 1)

- `notifications.py` — collapsed inline `_notification_kb_with_payout`-style
  shape into the existing builder, single try/except around the
  payout-button row only. No new helper, no new file.

## Within-commit skips (Type 3)

None.

## Verify gate

| Check | Result |
|---|---|
| `ruff check src/bot/` | 1 error — pre-existing `SIM108` in `channel_owner.py:80` (baseline) |
| `ruff check src/ tests/` | 20 errors (baseline preserved) |
| `ruff format --check src/ tests/` | clean (372 files) |
| `pytest tests/unit/test_bot_portal_deeplink.py` | 8 passed |
| `pytest tests/unit/test_no_dead_methods.py` | 4 passed (no dead-callsite revivals introduced) |
| `pytest tests/integration/test_bot_topup_handler.py` | 2 passed (regression smoke for unrelated bot handler path) |
| `rg "portal_webapp\|web_app=portal" src/ tests/` | 0 matches (sync helper fully retired) |

🔍 Verified against: 6e6d56b (Commit 1) + working tree
📅 Updated: 2026-05-01
