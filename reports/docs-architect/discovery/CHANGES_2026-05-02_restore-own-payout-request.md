# CHANGES — 2026-05-02 — Restore `OwnPayoutRequest.tsx` placeholder + register route

## Summary

Phase 3 preparation. Restores the mini_app placeholder
`mini_app/src/screens/owner/OwnPayoutRequest.tsx` and registers the
matching route `own/payouts/request` in `mini_app/src/App.tsx` so that
bot deeplinks introduced in 16.3 (`WebAppInfo(url=mini_app + /own/payouts/request)`)
resolve to a portal-bridge screen instead of falling through to
`NotFoundScreen` (catch-all `*`).

Drift surfaced during Phase 3 research consolidation
(`PHASE3_RESEARCH_2026-05-02.md` § 5 D5 / CON-4 / GAP-4): the 16.3
closure CHANGES described a created placeholder that the empirical
verification could not find on disk. This commit closes that gap.

## Why

- 16.3 (BL-045) deleted the bot payout FSM and converted three
  entry-point buttons (`own_menu` "💸 Выплаты", `cabinet`
  "💸 Запросить вывод", post-completion notification) to
  `web_app=portal_webapp("/own/payouts/request")` deeplinks
  (`src/bot/utils/portal_deeplink.py`).
- The deeplink target `/own/payouts/request` had no matching route in
  `mini_app/src/App.tsx`. Until today, a tap on any of the three
  buttons opened the mini_app at a 404 screen (`<NotFoundScreen />`
  via the catch-all `*` route at App.tsx:174).
- ФЗ-152 enforcement: payout requisites (card / phone / account) must
  never be entered through Telegram or mini_app. This screen
  intentionally renders zero PII surface — it only mints a
  short-lived portal ticket via the existing
  `OpenInWebPortal` → `useOpenInWebPortal` →
  `POST /api/auth/exchange-miniapp-to-portal` chain (Phase 1 §1.B.3)
  and redirects the user to the portal at `/own/payouts/request`.

## What changed

### Created
- **`mini_app/src/screens/owner/OwnPayoutRequest.tsx`** (32 LOC) —
  pattern-matched on `mini_app/src/screens/common/LegalProfileView.tsx`
  (Phase 1 §1.B.2 placeholder). `ScreenShell` + `Card` +
  `OpenInWebPortal target="/own/payouts/request"`. No state, no PII,
  no API calls beyond the bridge.

### Modified
- **`mini_app/src/App.tsx`** — added lazy import for
  `OwnPayoutRequest` next to existing `OwnPayouts` import (line 64)
  and route registration `{ path: 'own/payouts/request',
  element: <OwnPayoutRequest /> }` immediately after the
  `own/payouts` route (line 154), preserving alphabetical / flow
  grouping in the owner block.

### Untouched
- Bot payout flow logic (`src/bot/utils/portal_deeplink.py`,
  `src/bot/keyboards/owner/own_menu.py`, `src/bot/keyboards/shared/cabinet.py`,
  `src/bot/handlers/shared/notifications.py`) — 16.3 deeplink
  architecture preserved end-to-end.
- Web portal payout setup screen
  (`web_portal/src/screens/owner/OwnPayoutRequest.tsx`, 181 LOC) —
  remains the canonical entry point.
- Backend `/api/payouts/*` endpoints — already pinned web_portal-only
  (16.1).
- `mini_app/src/screens/owner/OwnPayoutRequest.module.css` —
  pre-existing orphan from the pre-16.3 full-form implementation;
  retained as orphan to match the established Phase 1 placeholder
  precedent (`LegalProfileView.module.css` is also orphan; the
  placeholder pattern uses Tailwind classes via `className` prop, no
  CSS module import). Cleanup of both orphan css files is out of
  scope for this prep commit and tracked separately as a low-priority
  hygiene item.

## Architecture flow (post-restore)

```
User (bot)
   │ 1. Tap "💸 Выплаты" / "💸 Запросить вывод"
   ▼
Telegram client
   │ WebAppInfo url = https://app.rekharbor.ru/own/payouts/request
   ▼
mini_app router → OwnPayoutRequest.tsx (this placeholder)
   │ OpenInWebPortal target="/own/payouts/request"
   │ → POST /api/auth/exchange-miniapp-to-portal
   ▼
Web portal /login/ticket?ticket=...&redirect=/own/payouts/request
   │ POST /api/auth/consume-ticket (one-shot, web_portal JWT)
   ▼
Web portal /own/payouts/request — full payout form (181 LOC)
```

Net effect identical to the 16.3 design intent. PII never touches
Telegram or mini_app at any point in this chain.

## References

- **PHASE3_RESEARCH_2026-05-02.md** § 5 D5 (Marina decision: restore
  placeholder + document), § 2.2 CON-4 (drift), § 2.3 GAP-4
  (verification surface).
- **CHANGES_2026-04-30_remove-bot-payout-flow.md** — describes the
  placeholder as part of the 16.3 architecture; this commit
  reconciles the doc-vs-reality drift.
- **BL-045** (CLOSED 2026-04-30) — bot payout FSM removal that
  introduced the deeplink architecture.
- **BL-055** (NEW, deferred post-16.x) — tracks a future
  direct bot→portal exchange endpoint that would obviate this
  placeholder. Until that lands, the mini_app intermediate is
  required for `exchange-miniapp-to-portal` to issue tickets.
- **Pattern reference:** `mini_app/src/screens/common/LegalProfileView.tsx`
  (Phase 1 §1.B.2).

## Verify

- `npx tsc --noEmit` — exit 0 (no new errors).
- `npm run build` (mini_app) — built in 973ms; emitted
  `dist/assets/OwnPayoutRequest-*.js` chunk alongside existing
  `OwnPayouts-*.js`.
- Route resolution: `own/payouts/request` no longer falls through to
  `NotFoundScreen` catch-all.

## Out of scope

- Direct bot→portal exchange (BL-055) — architectural improvement,
  not blocking launch.
- Orphan css cleanup
  (`OwnPayoutRequest.module.css`, `LegalProfileView.module.css`) —
  separate hygiene commit; matches established Phase 1 precedent.
- Phase 3 implementation work — this is preparation only.

🔍 Verified against: <commit_hash_filled_post_commit> | 📅 Updated: 2026-05-02T00:00:00Z
