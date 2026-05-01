---
backlog: BL-055
commit: 3/3 — mini_app OwnPayoutRequest placeholder removal
date: 2026-05-01
branch: feat/bl-055-direct-bot-to-portal-exchange
---

# CHANGES — BL-055 Commit 3: mini_app placeholder removal

Drops the now-unreached `OwnPayoutRequest` placeholder screen from the
mini_app and rewires the in-mini_app "Запросить вывод" button on the
`OwnPayouts` list page to use the same portal-bridge hook the rest of
the PII flows already use.

## Affected files

| File | Type | Notes |
|---|---|---|
| `mini_app/src/screens/owner/OwnPayoutRequest.tsx` | DELETED | placeholder retired — bot now opens portal directly (Commit 2), and the in-mini_app entry point switches to `useOpenInWebPortal` (below) |
| `mini_app/src/App.tsx` | edited | drops lazy import + route registration for `OwnPayoutRequest`; updates the comment that listed it as a known placeholder |
| `mini_app/src/screens/owner/OwnPayouts.tsx` | edited | "Запросить вывод" button now calls `useOpenInWebPortal('/own/payouts/request').mutate()` instead of `navigate('/own/payouts/request')`; uses `isPending` for the same loading-state UX as `OpenInWebPortal` |

## Business logic / contract impact

### User-visible behaviour change

**Before BL-055.** In the mini_app, `/own/payouts` → tap "Запросить
вывод" → mini_app navigates to `/own/payouts/request` placeholder
screen → that screen renders `OpenInWebPortal` button → user taps
again → portal opens.

**After BL-055.** In the mini_app, `/own/payouts` → tap "Запросить
вывод" → portal-ticket mint fires immediately → external browser
opens the portal authenticated. One tap removed; placeholder route
no longer exists.

### Web portal unaffected

`web_portal/src/screens/owner/OwnPayoutRequest.tsx` is the *real*
screen (with bank-requisites form, fee breakdown, etc.) — kept
unchanged. Only the mini_app placeholder of the same name is removed.

## Adaptations applied (Type 2)

- **In-mini_app `OwnPayouts` button rewired.** Plan A6 said "remove
  entirely / no fallback." Without rewiring the in-mini_app caller,
  `navigate('/own/payouts/request')` would land on `NotFoundScreen`
  (the route is gone). Replaced with the
  `useOpenInWebPortal('/own/payouts/request')` hook — same pattern
  `MainMenu` and `Cabinet` already use for PII bridges. Documented
  in the research file § O.2.

## Adjacent improvements (Type 1)

- `OwnPayouts.tsx` button label now mirrors the
  `OpenInWebPortal` component's "Открываем…" loading-state text while
  the portal-ticket mint is pending. Single ternary, no new
  abstraction.
- Removed unused `useNavigate` import from `OwnPayouts.tsx` (no
  remaining `navigate(...)` calls in the file after the rewire).

## Within-commit skips (Type 3)

None. The `mini_app/src/lib/types.ts` mention of `OpenInWebPortal`
in a comment block was reviewed and left intact — it's documenting
the shared bridge component which still exists.

## Verify gate

| Check | Result |
|---|---|
| `mini_app/$ tsc --noEmit` | clean (RC=0) — 0 import / type errors after the strip |
| `web_portal/$ tsc --noEmit` | clean (RC=0) — confirms the `OwnPayoutRequest` strip didn't break the unrelated portal-side route of the same name |
| `rg "OwnPayoutRequest" mini_app/src/` | 0 hits |
| `rg "navigate\('/own/payouts/request'\)" mini_app/src/` | 0 hits |
| `rg "navigate\('/own/payouts/request'\)" web_portal/src/` | 0 hits (portal still navigates to it via its own route, unaffected) |

🔍 Verified against: 66f6c66 (Commit 2) + working tree
📅 Updated: 2026-05-01
