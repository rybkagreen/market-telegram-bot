# CHANGES — Phase 8.1 block B iter 1: ScreenHeader action wrap on mobile

Audits the 20+ screens that use `<ScreenHeader>` against the newly
captured mobile-webkit baselines. Three screens had their action slot
clip off the right edge of the 320px viewport:

| Screen                          | Action buttons                         |
| ------------------------------- | -------------------------------------- |
| `/adv/campaigns`                | Обновить + Создать кампанию           |
| `/own/channels`                 | Обновить + Добавить канал             |
| `/billing/history`              | Экспорт CSV + Экспорт PDF             |

All three wrapped their two buttons in an inner `<div className="flex gap-2">`,
which blocked `ScreenHeader`'s outer `flex flex-wrap` from taking effect —
flex-wrap only wraps direct children, not grandchildren.

## Fix

Replace the inner `<div>` with a fragment in the three affected screens.
`ScreenHeader` already declares `flex flex-wrap gap-2 sm:flex-nowrap
sm:flex-shrink-0` on its action wrapper, so:
- Mobile: the second button wraps to its own line when the combined width
  exceeds the viewport. No overflow, no clipping.
- Desktop (≥sm): `flex-nowrap` restores the original horizontal layout.
  No change in behaviour.

No change to `ScreenHeader.tsx` itself — the existing contract is correct;
it was being bypassed by the extra DOM level.

## Files changed

- `web_portal/src/screens/advertiser/MyCampaigns.tsx`
- `web_portal/src/screens/owner/OwnChannels.tsx`
- `web_portal/src/screens/common/TransactionHistory.tsx`

Each diff is ~3 lines — drop `<div className="flex gap-2">` and closing
`</div>`, replace with `<>` / `</>`.

## Audit summary (screens not needing fixes)

Walked all 20+ ScreenHeader users via the captured 320-wide baselines:

- Single-button headers (most screens) already stack cleanly thanks to
  the S-47 flex-col stack fix.
- `/admin/users` table uses progressive `hidden sm:table-cell` /
  `hidden md:table-cell` — drops "Тариф" and "Баланс" columns on narrow
  viewports by design. Working correctly.
- `/own/payouts`, `/own/requests`, `/adv/analytics`, `/own/analytics`,
  all admin list screens — single action button, no issue.

## Public contract changes

None.

## Verification

- Visual regression baselines refreshed via `make test-e2e-visual-update`.
  Only the three fixed screens' mobile PNGs changed materially; desktop
  and all other mobile screenshots are pixel-stable.
- Smoke route-sweep (105/105) + API contract (76/76) remain green.

---
🔍 Verified against: f158495..HEAD | 📅 Updated: 2026-04-20T13:00:00+03:00
