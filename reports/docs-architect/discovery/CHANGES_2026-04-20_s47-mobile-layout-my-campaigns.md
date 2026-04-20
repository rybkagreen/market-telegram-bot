# CHANGES — S-47 pre-merge — mobile layout: ScreenHeader + MyCampaigns

**Sprint:** S-47 (UI redesign DS v2), Phase 8 pre-merge follow-up.

## Symptom

«Экран "Мои кампании" в мобильной версии сломан» — on iPhone-width
viewports (< 400px) the `/adv/campaigns` page overflowed: the two
`ScreenHeader` action buttons («Обновить» + «Создать кампанию»,
~253–268px together) pushed the title out of the viewport, and each
row in the campaign list overflowed horizontally because of its
fixed-width price column (`min-w-[110px]`) stacked next to icon,
status pill, 420-px-clamped description, and two action buttons.

## Root cause

- `ScreenHeader` used a single `flex items-end justify-between`
  layout with `flex-shrink-0` on the action slot. That forces
  action + title on one row regardless of viewport; on narrow mobile
  screens the title loses the min-w-0 race and disappears / truncates
  harshly.
- `MyCampaigns` row was a single `flex items-center gap-4` with five
  siblings (icon / flex-1 text / status / price / actions), each of
  which set `flex-shrink-0` or fixed widths. The combined intrinsic
  width was greater than the mobile content area, so the layout
  overflowed into horizontal scroll or wrapped unpredictably.

## Fix

### ScreenHeader (universal — affects every screen)

- Outer container is now `flex flex-col sm:flex-row
  sm:items-end sm:justify-between gap-3 sm:gap-5`. Mobile: title/
  subtitle row, then action row. `sm+`: unchanged horizontal layout.
- Title scales down to `text-[22px]` on mobile (`sm:text-[26px]`),
  and gains `break-words` so long titles don't overflow.
- Action wrapper is `flex flex-wrap gap-2 sm:flex-nowrap
  sm:flex-shrink-0`, allowing a Fragment-style action to wrap onto
  two lines on very narrow viewports (the existing `<div className="
  flex gap-2">…</div>` wrappers continue to work — they simply don't
  take advantage of the wrap, but they do get the full content-width
  second row under the title, which resolves the original overflow).

### MyCampaigns row (list-specific)

- Row base: `gap-3 sm:gap-4 px-4 sm:px-[18px]` — tighter on mobile.
- On mobile (< sm) the status pill and the separate price column are
  hidden (`sm:inline-flex` / `sm:inline-block`). Price reappears
  inline inside the text block's meta line, right-aligned next to the
  date, via `justify-between` on that line.
- Description clamp `max-w-[420px]` is now `sm:max-w-[420px]` —
  applies only on sm+ so on mobile the description gets full row width.
- Icon / text / actions are the only three top-level columns on
  mobile, which fits comfortably down to 320px viewports.
- Desktop layout (sm+) is byte-for-byte equivalent to before.

## Files

- `web_portal/src/shared/ui/ScreenHeader.tsx`
- `web_portal/src/screens/advertiser/MyCampaigns.tsx`

See commit `297f043 fix(web-portal): mobile layout for ScreenHeader +
MyCampaigns list`.

## Quality gates

- `npx tsc -b --noEmit` → clean
- `docker compose up -d --build nginx` → ok
- `curl -sk https://portal.rekharbor.ru/` → 200

## Follow-ups noted (not in this commit)

- Similar single-row list layouts exist on other screens (`OwnChannels`,
  `OwnRequests`, `TransactionHistory`, `AdminUsersList`, etc.). The
  ScreenHeader stack fix already helps their top chrome on mobile; the
  row-level responsive refactor would be a per-screen effort and is
  out of scope for this hotfix — flag for Phase 8.1 polish.

🔍 Verified against: `297f043` | 📅 Updated: 2026-04-20
