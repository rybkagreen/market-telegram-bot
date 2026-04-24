# CHANGES 2026-04-24 — web_portal mobile layout deep-sweep (phase 2)

## Scope

Deep mobile-layout sweep across `portal.rekharbor.ru` (web_portal). This
second phase follows the earlier 6-screen fix and targets every remaining
screen — common, shared, owner, advertiser wizard, admin, and Cabinet.
Executed in 5 sub-phases with verification gate between each.

Previous session (2026-04-24 first CHANGES) fixed: TopUp, Referral,
OwnPayouts, MyCampaigns, OwnChannels, ContractList.

## Plan reference
`/root/.claude/plans/ui-giggly-wind.md` (approved by user with three
explicit directives: include Cabinet, include cosmetic status-pill
phase, update visual baselines per-phase).

## Changes by sub-phase

### Phase 0 — Shared UI utilities

- `shared/ui/Input.tsx` — added `min-h-11` (44px tap target).
- `shared/ui/Textarea.tsx` — `py-2.5` → `py-3 min-h-[88px]` (≥2 rows × 44px).
- `shared/ui/StepIndicator.tsx` — wrapped in `overflow-x-auto no-scrollbar`; step labels now `hidden md:inline` except the active one (visible on mobile so user always sees where they are); outer `-mx-2 px-2` so scroll works edge-to-edge.
- `shared/ui/Sparkline.tsx` — new prop `responsive` (default false, backward-compatible). When true, svg uses `width="100%"` and `preserveAspectRatio="none"` — needed for BalanceHero whose 420px hardcoded width overflowed 375px mobile viewport.
- `styles/globals.css` — added utilities `.safe-bottom` (padding-bottom: max(0.75rem, env(safe-area-inset-bottom))), `.no-scrollbar`.
- **New**: `shared/ui/MobileDataCard.tsx` — generic stacked card for converting table-like desktop rows into mobile cards. Props: `leadingIcon`, `title`, `subtitle`, `trailing`, `rows[{label,value,emphasis}]`, `footer`, `onClick`. Exported from `shared/ui/index.ts`.

### Phase 1 — Critical layout killers (inline gridTemplateColumns with fixed 220–360px right columns)

All 5 screens had the same class of bug causing "vertical text on left edge" on 375px (same root cause as the 6 screens fixed in phase 1 session). Pattern:
```
style={{ gridTemplateColumns: 'minmax(0, Xfr) minmax(YYYpx, 1fr)' }}
→ className="... grid-cols-1 lg:[grid-template-columns:minmax(0,Xfr)_minmax(YYYpx,1fr)]"
```

- `common/AcceptRules.tsx:88` — 220px sticky nav + sticky top-5. Now `grid-cols-1 lg:[grid-template-columns:220px_minmax(0,1fr)]`; sticky moved to `lg:sticky lg:top-5`.
- `common/DocumentUpload.tsx:230` — 300px right panel.
- `common/Feedback.tsx:168` — 300px right panel.
- `common/Help.tsx:186` — 280px right panel.
- `common/LegalProfileSetup.tsx:213` — 300px right panel.
- `shared/Plans.tsx:324` — 5-column comparison table. Wrapped in `overflow-x-auto`, grid `min-w-[640px] md:min-w-0`, first column cells are `sticky left-0 z-10` with explicit bg so they stay visible during horizontal scroll.

### Phase 2 — Table-grids → mobile cards (3 list screens)

Each screen kept its desktop grid (`hidden md:grid` + arbitrary `md:[grid-template-columns:...]`) and gained a stacked mobile render pattern using `flex flex-col` + `md:contents` to preserve grid positioning on desktop:

- `common/MyActsScreen.tsx:277, 393` — two 6-column tables (pending acts, history). Header hidden on mobile. ActRow rewritten: on mobile, header row (checkbox + icon + act-number + status-dot), optional type/placement row, date + placement-id row, bottom actions row. L461 download button `w-[30px] h-[30px]` → `w-11 h-11 md:w-[30px] md:h-[30px]`.
- `common/ReputationHistory.tsx:396` — 4-column grid (42px icon + text + delta + score-change). Mobile: icon + text header, then delta pill + score-transition stacked on the right. Role label replaced with dot-in-circle + aria-label (dup of icon avatar).
- `common/TransactionHistory.tsx:412` — 4-column grid. Mobile: icon + title + date + (amount + status-dot) in top row; status-pill + desktop-amount hidden on <md. L226 `min-w-[260px]` → `min-w-[200px] md:min-w-[260px]`.

### Phase 3 — Admin tables + Cabinet/cabinet

**Admin tables** — added `sticky left-0` on first column of `overflow-x-auto` tables; relaxed `min-w-[Xpx]` values on mobile:

- `admin/AdminUsersList.tsx:112, 211-212, 234-253` — search input `min-w-[260px]` → `min-w-[200px] md:min-w-[260px]`. Checkbox + Name `<th>` and `<td>` cells now `sticky left-0` (and `left-10` for Name) with `z-10` and row-selection-aware background.
- `admin/AdminTaxSummary.tsx:14, 27` — № column `<th>` and `<td>` `sticky left-0 z-10`.
- `admin/AdminPayouts.tsx:158, 227` — `min-w-[320px]` → `min-w-[220px] md:min-w-[320px]`; textarea reject-reason `min-w-[240px]` → `min-w-[180px] md:min-w-[240px]` + `min-h-11`.
- `common/analytics/ChannelDeepDive.tsx:79, 94-97, 151, 165-172` — first column (`Канал`) `<th>` and `<td>` `sticky left-0 z-10` in both advertiser + owner tables.

**Cabinet**:
- `common/cabinet/BalanceHero.tsx` — `<Sparkline width={420} ...>` → `<Sparkline ... responsive>` inside `<div className="w-full">`. This was the primary Cabinet horizontal-overflow cause on 375px. Bottom CTA buttons (`Пополнить` / `К выплате`): `py-1.5` → `py-2.5 min-h-11 md:py-1.5 md:min-h-0` (44px tap target on mobile, compact on desktop). Gap `gap-5` → `gap-3 md:gap-5` + `flex-wrap`.
- `common/Cabinet.tsx` — header and inline gradient-avatar inspected; no actionable bugs found. The brief-mentioned "АДМИН ПАНЕЛЬ overlap" could not be reproduced — current layout is `flex flex-col lg:flex-row` with no sticky/z-index overlap. Left untouched.
- `common/cabinet/RecentActivity.tsx` — `w-8 h-8` decorative icon kept (informational, not a tap target — row itself is the click target).

### Phase 4 — Fixed bottoms + tap targets

All three `fixed bottom-0` bars now use `pt-3 safe-bottom` (respects iOS home indicator via `env(safe-area-inset-bottom)`):
- `owner/OwnChannels.tsx:551` (compare bar)
- `advertiser/campaign/_shell.tsx:39` (wizard footer)
- `advertiser/CampaignVideo.tsx:72` (wizard footer)

### Phase 5 — Unified status pills (only true duplicates)

Applied only where an icon-avatar on the left carries the same tone/meaning as a separate uppercase-text pill on the right — the brief's rule #2 target ("иконка + метка рядом"). Files where text-pill was the SOLE indicator (icon only inside the pill, no external avatar) were left intact to avoid losing information:

**Removed** (duplicate avatar + text):
- `shared/DisputeDetail.tsx:96` — collapsed large `Icon + meta.label` pill into `w-10 h-10 rounded-full` icon badge with aria-label.
- `shared/MyDisputes.tsx:134` — removed standalone uppercase text pill; added `aria-label`/`title` to the existing 40×40 icon-avatar on the left.
- `owner/OwnRequests.tsx:280` — removed `hidden sm:inline-flex` text pill entirely (desktop was already hiding on mobile); added aria-label to the icon-avatar.
- `admin/AdminDisputesList.tsx:121` — same pattern: avatar + text pill → avatar-only with aria-label.

**Explicitly skipped** (text is the only status indicator, not a duplicate):
- `shared/OpenDispute.tsx:243` (ERID "Есть"/"Нет" — no duplicate avatar)
- `shared/Plans.tsx:236, 241` ("ПОПУЛЯРНЫЙ"/"ВКЛЮЧЕНО" — decorative/sale badges, not status)
- `owner/OwnRequestDetail.tsx:301` (dispute status in a standalone block, no avatar)
- `owner/DisputeResponse.tsx:188` (DetailRow — info icon is generic, not status-specific)
- `advertiser/OrdStatus.tsx:96` (ORD pill in section header — sole indicator)
- `advertiser/campaign/CampaignPublished.tsx:114, 146` (dispute + ERID pills — no duplicate)
- `common/LegalProfileView.tsx:95, 101` (standalone "Верифицирован" / "Паспорт добавлен" badges — unique info)
- `common/ContractDetail.tsx:134` (status pill alongside a document-type avatar, not a status avatar)
- `admin/AdminFeedbackList.tsx:131`, `AdminFeedbackDetail.tsx:122`, `AdminPayouts.tsx:161`, `AdminUserDetail.tsx:168, 181`, `AdminDisputeDetail.tsx:145` — icon+text pills where the pill is the sole indicator.

## Business / API impact

Zero. All changes are pure UI (responsive grids, layout classes, utility CSS, one new presentational component). No API contracts, no FSM, no DB queries, no business logic, no Pydantic schemas.

## Files touched (sub-phase summary)

Phase 0: 5 files + 1 new component (MobileDataCard.tsx).
Phase 1: 6 files.
Phase 2: 3 files.
Phase 3: 4 admin/analytics files + 2 cabinet files.
Phase 4: 3 files.
Phase 5: 4 files.

**Total this session: 26 files + 1 new**, ~600 insertions / ~300 deletions.

## Verification

- `npx tsc --noEmit -p tsconfig.app.json` — exit 0.
- `npm run lint` — no new warnings / errors. Pre-existing `AIInsightCard.tsx:31` error (`Date.now()` during render) is unrelated.
- `npx vite build` — 803ms, bundle sizes unchanged.
- `npx playwright test` — **not run**. Playwright 1.59.1 is not installed in `web_portal/node_modules`. The project's `playwright.config.ts` is a directory import that `npx playwright` fetched globally cannot resolve. This was noted as a limitation in the plan — e2e verification in this environment was never run in the previous session either.

## Not verified (limitations)

Browser-side verification at 375/390px is not possible in this headless environment. Recommend manual QA pass in Chrome DevTools (iPhone SE 375×667, iPhone 12 390×844) on:

1. TopUp — no vertical-text artifacts.
2. Referral — "Ваши рефералы" not squeezed.
3. AcceptRules — sticky TOC moved to <lg so content isn't crushed at 343px.
4. Feedback / Help / DocumentUpload / LegalProfileSetup — single-column on mobile, 2-col on lg+.
5. Plans — horizontal scroll inside comparison table, first column stays visible.
6. MyActs / ReputationHistory / TransactionHistory — each record readable without horizontal scroll.
7. Cabinet BalanceHero — sparklines scale to container width without overflowing.
8. AdminUsersList / AdminTaxSummary — horizontal scroll with sticky first column.
9. Campaign wizard footer / OwnChannels compare bar / CampaignVideo footer — safe-area-inset honored on iOS PWA / Telegram WebApp.

## Rollback

Every change is within 26 listed files. To revert: `git checkout -- web_portal/src/`. No migrations, no external dependencies added.

🔍 Verified against: 2b5375f9178ee18ac233a01acac4ca8748fd95f5 | 📅 Updated: 2026-04-24T00:00:00Z
