# CHANGES 2026-04-24 — web_portal mobile layout fixes

## Scope
Systemic mobile-layout fixes on `portal.rekharbor.ru` (web_portal). Cabinet
screen was explicitly out of scope per task brief. Verified against
viewport widths 375px and 390px mentally; in-browser screenshot
verification not possible in this headless environment (see "Not verified"
below).

## Affected files

### screens/
- `web_portal/src/screens/shared/TopUp.tsx` — dropped inline
  `grid-template-columns: minmax(0,1fr) 360px` that caused the "vertical
  text on the left edge" artifact at narrow widths. Now stacks single-column
  on `<md`, switches to 2-col at `md+`. `aside` panel loses `sticky top-5`
  below `md` so it no longer floats.
- `web_portal/src/screens/common/Referral.tsx` — 3 inline grid templates
  replaced with responsive single-col on `<md` (the main problem: the
  `minmax(0,1.6fr) minmax(280px,1fr)` grid squeezed "Ваши рефералы" to
  ~60px width on 375px, visually hiding it under "Как это работает"). Also
  replaced the "Активен/Новый" text pill next to each referral with a
  dot-only indicator carrying `aria-label`/`title`.
- `web_portal/src/screens/owner/OwnPayouts.tsx` — history row refactored
  from flex-row with `min-w-[160px]`/`min-w-[120px]` cells (which clipped
  "ЗАПРОШЕНО"/"К ЗАЧИСЛЕНИЮ" headings) to a stacked card on `<sm`
  (header: icon + #id + date; body: 2-col grid with "Запрошено" and
  "К зачислению"). Dropped the redundant "ВЫПЛАЧЕНО/В ОБРАБОТКЕ" uppercase
  text pill; icon + color still carry state, aria-label/title expose it.
- `web_portal/src/screens/advertiser/MyCampaigns.tsx` — filter-pill row
  converted: on `<sm` it becomes a horizontally-scrollable strip with
  `snap-mandatory`; on `sm+` it keeps `flex-wrap`. Sort control moved to
  a separate row on mobile. `FilterPill` grew `flex-shrink-0 snap-start`
  to anchor scroll positions.
- `web_portal/src/screens/owner/OwnChannels.tsx` — bottom action cluster
  gets `gap-2` on mobile (was `gap-1.5`). Each of the three icon buttons
  gained `!w-11 !h-11 @3xl:!w-8 @3xl:!h-8`, giving 44×44 tap targets on
  mobile and reverting to Button's native `sm` size on desktop via the
  existing container query. The "Активен/Скрыт" uppercase text pill next
  to `@username` replaced with a dot-in-circle indicator
  (aria-label/title).
- `web_portal/src/screens/common/ContractList.tsx` — the table-style grid
  (`1.4fr 2fr 1.2fr 0.9fr auto`) now hides its header on `<md` and the
  rows restructure into a stacked mobile card: icon + `#id` + type label
  on row 1, `vN` underneath, period `DD.MM.YYYY — бессрочно` on its own
  line, status reduced to a dot-in-circle (same rule #2). Status pill
  also collapsed to dot-only on desktop per brief. `fmtDate` switched
  from `'19 апр. 2026 г.'` to `'19.04.2026'` (2-digit month). New helper
  `fmtPeriod` yields `'DD.MM.YYYY — бессрочно'` when `expires_at` is
  null. PDF download button is 44×44 on mobile.

## Business logic
Pure UI changes — no API contracts, no FSM, no DB, no business logic.

## Contract / API
Not touched.

## Verification
- `cd web_portal && npm run lint` — no new warnings/errors introduced.
  The one pre-existing error (`AIInsightCard.tsx:31` — `Date.now()` in
  render) is unrelated to this change and predates the branch.
- `npx tsc --noEmit -p tsconfig.app.json` — exit 0, no type errors.
- `npx vite build` — production build succeeds in 810ms.

## Not verified (limitations)
No browser screenshot verification was possible in this session (no
access to a graphical DevTools). The following should be checked by hand
on 375px and 390px after deploy:
1. Horizontal scrollbar on `<body>` across all touched screens.
2. Absolute absence of "character-per-line" text artifacts in TopUp.
3. No overlap between Referral's "Ваши рефералы" and "Как это работает".
4. PDF button tap target actually renders 44×44 in ContractList mobile.
5. Campaign filter pill horizontal scroll snaps correctly.
6. OwnChannels action buttons render consistently with Button's own
   focus/hover states (the `!important` sizing may lose some shadow/ring
   nuances — visual QA needed).

## Screens NOT touched (per brief's "кроме Кабинет" and scope control)
- `Cabinet.tsx` and its `cabinet/*` children — explicitly excluded.
- Cross-project status-label cleanup per brief rule #2: applied only to
  the explicitly-listed priority screens. Other screens still using a
  icon+uppercase-text pill pattern (e.g., `MyActsScreen`,
  `TransactionHistory`, `DisputeDetail`, `OpenDispute`, `OwnRequests`,
  `CampaignPublished`, `OrdStatus`, `LegalProfileView`, admin screens)
  are unchanged. Recommend a follow-up sweep if the brief is meant
  repo-wide.

🔍 Verified against: 2b5375f9178ee18ac233a01acac4ca8748fd95f5 | 📅 Updated: 2026-04-24T00:00:00Z
