# CHANGES 2026-04-24 — web_portal mobile jitter + residual bugfix sweep

## Scope

Third iteration after user feedback that phase-1 and phase-2 fixes left
visible bugs on 4 screens (Каналы, Пополнить, Размещение, Выплаты) and —
more importantly — "horizontal jitter / UI не зафиксирован" при
вертикальном скролле across most screens. Root-cause diagnosis done, fix
applied globally + residual bugs patched.

## Root causes identified

1. **Scrollbar width toggling the layout horizontally.** `<main>` in
   `PortalShell` was `overflow-y-auto scrollbar-thin` — scrollbar appears
   only when content overflows vertically, which means every new screen
   briefly renders without a scrollbar, then the scrollbar claims its
   4px, and the content shifts left by 4px. On pages where content
   height changes dynamically (lists loading, expanding sections), the
   scrollbar flickers in/out — reading as "jitter".
2. **`hover:-translate-y-0.5` on touch targets.** 3 components had
   hover-triggered `transform: translateY(-2px)`. On touch devices the
   `:hover` state is sticky after a tap until another element is tapped
   — so any row the user tapped stays `translated -2px`, and neighbouring
   rows don't, producing visible vertical shifts that read as "UI не
   зафиксирован жестко".
3. **iOS overscroll / rubber-band on `<body>`.** Outer `div` had
   `overflow-hidden` but `html`/`body` did not have `overscroll-behavior`
   set, so reaching the end of the main scroll container let the entire
   body bounce.
4. **Double `overflow-x-auto`.** Campaign wizard `_shell` wrapped
   `StepIndicator` in `overflow-x-auto` — but `StepIndicator` itself
   already grew its own `overflow-x-auto` in phase 0, creating a nested
   scroll that users could accidentally trigger.

## Files changed

### Global (affects all screens)

- `web_portal/src/components/layout/PortalShell.tsx` — main:
  `overflow-y-auto` → `overflow-x-hidden overflow-y-scroll
  [scrollbar-gutter:stable] overscroll-contain`. `scrollbar-gutter:stable`
  reserves the scrollbar gutter even when content doesn't overflow —
  eliminates the horizontal jitter on every screen. `overflow-x-hidden`
  clips any accidental horizontal overflow (a safety net against future
  bugs). `overscroll-contain` prevents scroll-chain to the body.
- `web_portal/src/styles/globals.css` — `html` and `body` now
  `overflow-x: hidden; height: 100%; overscroll-behavior: none`.
  Prevents iOS rubber-band on the document root.

### Hover-transform removal (jitter on touch)

- `web_portal/src/screens/shared/Plans.tsx:223` — PlanCard
  `hover:-translate-y-0.5` → `hover:border-accent/50`; `transition-all`
  → `transition-colors`.
- `web_portal/src/screens/owner/OwnChannelDetail.tsx:262` — ActionTile
  `hover:-translate-y-0.5 hover:border-accent/40 transition-all` →
  `hover:border-accent/40 hover:bg-harbor-elevated/40 transition-colors`.
- `web_portal/src/screens/common/cabinet/QuickActions.tsx:49` —
  `hover:bg-harbor-elevated hover:-translate-y-0.5 transition-all` →
  `hover:bg-harbor-elevated transition-colors`.

All three continue to provide clear hover feedback via color/border,
just without the layout-shifting transform.

### Residual bugs on the 4 screens the user called out

- **Пополнить (`shared/TopUp.tsx:156`)** — removed duplicated class
  pair `w-8.5 h-8.5 w-[34px] h-[34px]` (Tailwind arbitrary `w-8.5` is
  not defined; kept `w-[34px] h-[34px]`).
- **Пополнить/подтверждение (`shared/TopUpConfirm.tsx:209`)** — inline
  `style={{ gridTemplateColumns: live === 'succeeded' ? '1fr 1fr' :
  '1fr 1fr 1fr' }}` on the buttons grid forced 3 buttons onto one row
  on mobile. Replaced with `grid-cols-1 sm:grid-cols-3` (2 cols when
  succeeded).
- **Размещения (`owner/OwnRequests.tsx:250-295`)** — the request-row
  was a strict horizontal flex with icon + content + price
  (`min-w-[110px]`) + action button → didn't fit on 343px. Rewritten
  into a stacked card on `<sm`: icon + channel + id in the header row,
  ad-text + date on the next, price shown inline on mobile (right of
  date) and as a desktop cell on `sm+`; desktop grid preserved.
- **Размещение/деталь (`owner/OwnRequestDetail.tsx:210`)** —
  `whitespace-pre-wrap` on the ad_text `<p>` didn't break long URLs /
  tokens. Added `break-words [overflow-wrap:anywhere]` so any long
  inline string wraps cleanly inside a 343px card.
- **Каналы/деталь (`owner/OwnChannelDetail.tsx:85-99`)** — removed the
  "Активен / Скрыт" uppercase text pill; status is now carried by the
  avatar colour (accent-muted vs harbor-elevated) + a 5×5 dot in a
  circle next to the title with `aria-label` / `title`. Hover transform
  on ActionTile also removed (see above).
- **Выплаты (`owner/OwnPayouts.tsx:106-112`)** — hero amount
  `text-[34px]` clipped on 375px when the sum reached 6+ digits. Now
  `text-[26px] sm:text-[34px] break-words`; the "минимум · комиссия ·
  кулдаун" meta row wraps with `flex-wrap` and the info icon is
  `flex-shrink-0`.

### Other residual issues found during sweep

- `web_portal/src/screens/common/cabinet/PerformanceChart.tsx:87` —
  three-metric strip (Доходы / Расходы / Нетто) with `gap-6` didn't
  fit on 375px. Now `flex-wrap gap-3 md:gap-6`.
- `web_portal/src/screens/advertiser/campaign/_shell.tsx:31` — removed
  the redundant `overflow-x-auto` wrapper around `StepIndicator` (the
  indicator manages its own horizontal overflow since phase 0).

## Audited — no bugs found

Scanned with targeted greps for: `hover:-translate`, `hover:scale-`,
`hover:shadow-*` (layout-shifting), `100vh` / `min-h-screen` (iOS
address-bar resize), `min-w-[>=300px]` (viewport overflow), inline
`style={{ gridTemplateColumns: ... }}` with fixed pixel columns,
`absolute` elements with `left-[Npx]` escaping viewport, `overflow-x-*`
nested inside another `overflow-x-*`, `width={N}` on SVG/img ≥ 300
without `responsive`, `group-hover:-translate/-scale`, `focus:-translate`
/ `active:-translate` (outside `active:scale-[0.98]` on Button which is
intentional press-feedback that doesn't affect layout).

Remaining inline `gridTemplateColumns` occurrences (14 total) are all
`repeat(auto-fit, minmax(Npx, 1fr))` with `N ≤ 240` — safely collapse
to 1 column on 343px mobile width. Left untouched.

## Business / API impact

Zero. Pure UI. No API, no FSM, no DB, no business logic, no schemas.

## Verification

- `cd web_portal && npx tsc --noEmit -p tsconfig.app.json` — exit 0.
- `npm run lint` — no new warnings (pre-existing `AIInsightCard.tsx:31`
  error unrelated).
- `npx vite build` — 616ms, bundle sizes unchanged.
- `docker compose build --no-cache nginx` + `docker compose up -d
  --force-recreate nginx` — nginx running `(healthy)`, serving fresh
  web_portal/dist.

## Not verified (same limitations as previous sessions)

No headless browser or Playwright in this environment — visual QA on
375/390px Chrome DevTools remains a manual step before production merge.

🔍 Verified against: 2b5375f9178ee18ac233a01acac4ca8748fd95f5 | 📅 Updated: 2026-04-24T00:00:00Z
