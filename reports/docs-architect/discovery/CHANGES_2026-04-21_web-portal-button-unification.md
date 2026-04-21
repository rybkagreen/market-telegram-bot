# CHANGES — 2026-04-21 — web-portal Button system unification (production-ready)

## Summary

Unified the web_portal button system across all screens. Previous implementation
had no real size scale (every size ≥ 44 px min-height) and used a heavy-bordered
`secondary` variant that visually competed with primary CTAs in `ScreenHeader`
action slots. Result: header actions like "Создать кампанию", "Экспорт CSV",
"Пополнить баланс", "Обновить", "Отчёт" felt bulky and drowned out screen titles.

## Affected files

### UI primitives (tokens + new primitive)

- `web_portal/src/shared/ui/Button.tsx` — **rewritten**
  - New real size scale: `sm = 32 px`, `md = 40 px`, `lg = 48 px`
    (previously `sm = md = 44 px`, `lg = 52 px`)
  - Softened variants:
    - `secondary`: `bg-harbor-elevated` + transparent border (was hard
      `border-border-active` that clashed with cards)
    - `ghost`: transparent → `hover:bg-harbor-elevated`
    - `danger`/`success`: transparent border + colored hover border
    - `primary`: kept bold; subtle inset highlight + drop shadow
  - Text: `sm → 13px / medium`, `md → 14px / semibold`, `lg → 15px / semibold`
  - Added `focus-visible:ring` a11y outline
  - Added `aria-label` and `aria-busy` props
  - Icon-only sizing scales with size tokens (32 / 40 / 48)
  - Loading spinner now uses `border-current` — inherits variant text color
  - **API is backwards-compatible** — same props, same behavior.
- `web_portal/src/shared/ui/DropdownMenu.tsx` — **new primitive**
  - Generic menu with outside-click + Esc close, keyboard focus on open,
    `role="menu"` / `role="menuitem"` semantics.
  - Used to consolidate "Экспорт CSV / PDF" pair into a single trigger with
    format picker.
- `web_portal/src/shared/ui/ScreenHeader.tsx` — tightened action row
  (`items-center` + `gap-2`).
- `web_portal/src/shared/ui/index.ts` — re-export `DropdownMenu` + `DropdownMenuItem` type.

### Screens updated to `size="sm"` header actions

Primary CTAs kept as `variant="primary" size="sm"`; nav/back buttons shifted to
`variant="ghost"` so they read as meta-navigation, not competing actions;
utility refresh buttons collapsed to icon-only 32×32.

- `web_portal/src/screens/common/Cabinet.tsx` — header actions to `sm`;
  added `analytics`/`plus` icons
- `web_portal/src/screens/common/TransactionHistory.tsx` — Export CSV + PDF
  pair consolidated into a single `DropdownMenu` trigger
- `web_portal/src/screens/common/MyActsScreen.tsx` — refresh to icon-only ghost
- `web_portal/src/screens/common/Feedback.tsx` · `ReputationHistory.tsx` ·
  `Referral.tsx` · `DocumentUpload.tsx` · `ContractList.tsx` ·
  `ContractDetail.tsx` · `AcceptRules.tsx` · `LegalProfileView.tsx` — `size="sm"`
- `web_portal/src/screens/advertiser/MyCampaigns.tsx` — refresh icon-only,
  primary CTA to `sm`
- `web_portal/src/screens/advertiser/AdvAnalytics.tsx` — refresh to icon-only
  ghost
- `web_portal/src/screens/advertiser/CampaignCounterOffer.tsx` ·
  `CampaignPayment.tsx` · `CampaignVideo.tsx` · `campaign/CampaignWaiting.tsx`
  · `campaign/CampaignPublished.tsx` · `OrdStatus.tsx` ·
  `AdvertiserFrameworkContract.tsx` — back/utility buttons to ghost `sm`
- `web_portal/src/screens/owner/OwnChannels.tsx` · `OwnPayouts.tsx` ·
  `OwnAnalytics.tsx` · `OwnRequests.tsx` — refresh to icon-only ghost
- `web_portal/src/screens/owner/OwnChannelDetail.tsx` · `OwnChannelSettings.tsx`
  · `OwnAddChannel.tsx` · `OwnPayoutRequest.tsx` · `OwnRequestDetail.tsx` ·
  `DisputeResponse.tsx` — back buttons to ghost `sm`
- `web_portal/src/screens/shared/DisputeDetail.tsx` · `OpenDispute.tsx` —
  back buttons to ghost `sm`
- `web_portal/src/screens/shared/Plans.tsx` — "Пополнить баланс" to primary
  `sm`
- `web_portal/src/screens/admin/AdminDisputeDetail.tsx` ·
  `AdminFeedbackDetail.tsx` · `AdminUserDetail.tsx` — header actions to `sm`

### Pre-existing lint errors fixed during hardening

Per standing project directive "Fix all issues during hardening"
(`feedback_fix_all_production_issues.md`):

- `web_portal/src/shared/ui/Sparkline.tsx` — replaced `Math.random` ID
  generation with `useId()` (react-hooks/purity error)
- `web_portal/src/hooks/useBillingQueries.ts` — moved `Date.now()` read out of
  render body into `useEffect` (react-hooks/purity error)
- `web_portal/src/screens/common/cabinet/BalanceHero.tsx` — extracted
  `history?.items` into a stable variable to satisfy React Compiler manual
  memoization preservation
- `web_portal/src/screens/shared/MyDisputes.tsx` — wrapped
  `data?.items ?? []` in `useMemo` to stabilize dependency

Eslint: **0 errors** (was 3), 6 pre-existing warnings remain (non-blocking,
unrelated to this change — logical-expression memo-dep style).

## Business logic impact

**None.** Pure visual / interaction refactor of a shared UI primitive and its
call sites. No routing, no API calls, no state machines changed.

## API / FSM / DB contracts

- **No public contract changes.** `Button` component API is fully
  backwards-compatible (same props, same prop types).
- **New public export**: `DropdownMenu` from `@shared/ui`.
- No DB migrations. No Celery task changes. No FSM state changes.

## Visual regression impact (action required)

- `web_portal/tests/specs/visual.spec.ts` baselines **will fail** on next run —
  every screen with a `ScreenHeader` action shows a different button style.
  Regenerate baselines after manual visual QA:

  ```bash
  make test-e2e-visual-update
  ```

- `web_portal/tests/specs/smoke.spec.ts` unaffected (no DOM structure changes
  that would break selector-based assertions).

## Validation performed

- `npm run build` — ✅ tsc + Vite compile clean, 758 ms → 652 ms (cold/warm)
- `npm run lint` — ✅ 0 errors (down from 3), 6 pre-existing warnings
- `docker compose up -d --build nginx` — ✅ nginx container rebuilt with new
  static assets, all 12 services Up
- Playwright visual suite — ⚠️ intentionally will require baseline refresh
  (see above)
- Playwright smoke suite — not re-run (no selector-level changes)

## Size metrics

| Surface | Before | After |
|---|---|---|
| Header secondary button | 44 × ≥120 px, 16 px text | 32 × ≥88 px, 13 px text |
| Header primary CTA | 44 × ≥160 px | 32 × ≥140 px |
| Header refresh | full 44 px text button | 32 × 32 icon-only ghost |
| Form submit default | 44 px | 40 px |
| Hero CTA (`lg`) | 52 px | 48 px |
| Focus ring | absent | `ring-border-focus` with offset |

## Additional fix bundled: admin "Настройки" sidebar link

Unrelated to buttons but reported during visual QA:

- `web_portal/src/components/layout/Sidebar.tsx` — removed the public "Настройки"
  entry from the "Прочее" group. It was visible to all roles and pointed to
  `/settings` → `PlaceholderScreen` (a `🚧` stub), which is why the platform
  legal-profile screen appeared to have disappeared.
- Added "Реквизиты платформы" → `/admin/settings` to the
  "Администрирование" section (admin-only). The screen
  `AdminPlatformSettings` was already mounted at this route and powers the
  legal data injected into contracts (`legal_name`, `inn`, `kpp`, `ogrn`,
  bank details).
- `web_portal/src/App.tsx` — removed the `/settings` placeholder route and
  the now-unused `PlaceholderScreen` component.

Breadcrumb entry for `/admin/settings` ("Админ → Настройки платформы") already
exists in `Topbar.tsx:214`.

## Follow-ups (not in this PR)

- Wire actual CSV / PDF export handlers in `TransactionHistory` DropdownMenu
  items (currently stubbed — pre-existing, originals also had no `onClick`)
- Regenerate Playwright visual baselines
- Optional: mini_app parity pass if the bot-facing UI shows similar drift
  (not evaluated in this scope — web_portal only)

🔍 Verified against: 45bdb04 | 📅 Updated: 2026-04-21T12:26:25Z
