# S-47 — UI Redesign DS v2 (progress)

Feature branch: `feat/s-47-ui-redesign-ds-v2` (from main `5d7451d`).
Source of truth: `reports/20260419_diagnostics/FIX_PLAN_07_ui_redesign_ds_v2.md`.

## Phase 1 — Foundation (tokens, fonts, icon sprite) — completed 2026-04-20

### globals.css (§7.1)
- **Verified:** existing `web_portal/src/styles/globals.css` already mirrors handoff
  `project/globals.css` verbatim (@theme tokens, light-mode `@layer theme`, base-layer
  rules, custom utilities). No rewrite needed.
- **Added:** `.rh-icon .rh-stroke` and `.rh-icon .rh-fill` component-layer rules so
  the 132-symbol sprite renders correctly.
- **Added:** `@keyframes ui-spin` and `@keyframes ui-skeleton` (ported from handoff
  `ui.jsx` runtime-inject, now static CSS — so primitives can reference them without
  a JS side-effect).

### Fonts (§7.2.1)
- **Verified:** Google Fonts `Outfit` / `DM Sans` / `JetBrains Mono` already wired in
  `web_portal/index.html` (`preconnect` + `css2?family=…`). No change needed.

### Icon system (§7.2.2)
- **Added:** `web_portal/public/icons/rh-sprite.svg` — direct copy of handoff
  `icons/icons.svg` (132 symbols in 10 groups, 20×20, stroke 1.5, rounded joins,
  24 fill variants for nav states).
- **Added:** `web_portal/src/shared/ui/icon-names.ts` — `ICON_NAMES` literal-union
  const + `IconName` type + `FILLED_AVAILABLE` set. Mirrors handoff `Icons.jsx`.
- **Added:** `web_portal/src/shared/ui/Icon.tsx` — TSX port of handoff `<Icon>`.
  Props: `name: IconName`, `variant: outline|fill`, `size=20`, `strokeWidth?`,
  `className?`, `title?`. Uses `<use href="/icons/rh-sprite.svg#rh-{name}">` with
  `window.__RH_ICON_SPRITE` override hook for post-inline-injection path rewriting.
- **Added:** `web_portal/src/shared/ui/IconSpriteLoader.tsx` — fetches sprite once,
  inlines into `<body>` under `#__rh-icon-sprite`, sets `__RH_ICON_SPRITE=""` so
  subsequent `<use>` refs resolve locally.
- **Mounted:** `IconSpriteLoader` inside `PortalShell.tsx` return root (once per
  session), so all shell + screen icons share a single inline-sprite copy.
- **Exported** `Icon`, `IconSpriteLoader`, `IconName`, `ICON_NAMES`, `FILLED_AVAILABLE`
  from `@shared/ui/index.ts`.

### Files touched
- `web_portal/src/styles/globals.css` — +20 lines (icon rules + 2 keyframes)
- `web_portal/public/icons/rh-sprite.svg` — new (37 KB)
- `web_portal/src/shared/ui/icon-names.ts` — new (43 lines)
- `web_portal/src/shared/ui/Icon.tsx` — new (63 lines)
- `web_portal/src/shared/ui/IconSpriteLoader.tsx` — new (33 lines)
- `web_portal/src/shared/ui/index.ts` — +4 exports
- `web_portal/src/components/layout/PortalShell.tsx` — mount IconSpriteLoader

### Verification
- `cd web_portal && npx tsc --noEmit -p tsconfig.app.json` → 0 errors.

### Deferred
- `LUCIDE_MAPPING.md` — will be authored when migration of existing `lucide-react`
  imports begins (Phase 8). The full table is already in `FIX_PLAN_07 §7.23` so the
  standalone file is a duplicate until it starts serving as the migration checklist.
- ESLint `no-restricted-imports` rule for `lucide-react` — added with other Phase 8
  polish to avoid churning the lint config before any call-site is migrated.
- Dev-only icon gallery route `/dev/icons` — backlog.

---

🔍 Verified against: feat/s-47-ui-redesign-ds-v2 (post `5d7451d`) | 📅 Updated: 2026-04-20T02:30:00Z

## Phase 3 — Backend endpoints (§7.21) — completed 2026-04-20

### `GET /api/billing/frozen` (§7.21.1)
- Schema `FrozenPlacementItem` + `FrozenBalanceResponse` в `src/api/routers/billing.py`.
- Repo-метод `PlacementRequestRepository.get_frozen_for_advertiser(advertiser_id, limit)` —
  eager-load channel для title без N+1.
- Handler `get_frozen_balance(CurrentUser)` суммирует escrow + pending_payment,
  разбивает counts и items. Объявлен ПЕРЕД `/history` (static-path-before-`{int}`-rule).
- Суммы в рублях (Decimal), `amount = final_price ?? proposed_price`.

### `GET /api/analytics/cashflow?days=7|30|90` (§7.21.2)
- Schema `CashflowDataPoint` (ISO date) + `CashflowResponse` (total_income, total_expense,
  net, period_days, points[days]).
- Классификатор `_INCOME_TX_TYPES` / `_EXPENSE_TX_TYPES` по `TransactionType` enum
  (amount всегда положителен; направление инферится по type).
- Запрос `SELECT DATE(created_at), type, SUM(amount) GROUP BY` отфильтрован по
  `is_reversed=false`.
- Handler zero-fills пропущенные дни, возвращая exactly `days` точек — ось X
  графика равномерна.
- `days: Literal[7, 30, 90]` — строгая Pydantic-валидация.

### `GET /api/users/me/attention` (§7.21.3)
- Новый service `src/core/services/user_attention_service.py`:
  `build_attention_feed(user, session)` — агрегат 3 сигналов: legal_profile_incomplete
  (danger), placement_pending_approval (warning, >24h), new_topup_success (success, <48h).
- `AttentionFeedItem` — `@dataclass(slots=True)` (ruff B903).
- Pydantic schemas `AttentionItem` / `AttentionFeedResponse` + `count_attention_dots`
  для red-dot в Topbar.
- Handler объявлен ПЕРЕД `/me/referrals`.
- Redis-кэш — в бэклог; сейчас прямой DB-запрос.

### `GET /api/channels/recommended?limit=5&category=...` (§7.21.4)
- Schema `RecommendedChannelsResponse { items: ChannelResponse[]; algorithm: str }`.
- Алгоритм: topics из успешных placement'ов → каналы в тех категориях по last_er desc;
  fallback — top-ER overall. Query-параметр `category` перегружает.
- Объявлен в блоке static-path-GET'ов ПЕРЕД `/{channel_id}` (route-ordering rule).
- Исключает каналы, принадлежащие самому пользователю.

### TS API clients + React Query hooks (§7.21.5)
- `web_portal/src/api/billing.ts` → `getFrozenBalance()` + `FrozenBalanceResponse`.
- `web_portal/src/api/analytics.ts` → `getCashflow(days)` + `CashflowResponse`,
  `CashflowDays` union literal.
- `web_portal/src/api/users.ts` → `getAttentionFeed()` + `AttentionFeedResponse`,
  `AttentionSeverity`/`AttentionType` unions.
- `web_portal/src/api/channels.ts` → `getRecommendedChannels(limit, category?)`.
- Hooks: `useFrozenBalance`, `useCashflow(days)`, `useAttentionFeed`,
  `useRecommendedChannels(limit, category?)` с `staleTime: 60_000`.

### Verification
- `poetry run ruff check src/...` → clean.
- `cd web_portal && npx tsc --noEmit -p tsconfig.app.json` → 0 errors.
- Pyright import-not-resolved diagnostics are pre-existing venv-wiring issue — not S-47.

### Files touched (Phase 3)
- `src/api/routers/billing.py` — +1 endpoint, +2 schemas, +1 import (Literal).
- `src/api/routers/analytics.py` — +1 endpoint, +2 schemas, +1 date import, classifier sets.
- `src/api/routers/users.py` — +1 endpoint, +3 schemas, +1 Literal import.
- `src/api/routers/channels.py` — +1 endpoint, +1 schema.
- `src/db/repositories/placement_request_repo.py` — +1 repo method (get_frozen_for_advertiser).
- `src/core/services/user_attention_service.py` — new file (147 lines).
- `web_portal/src/api/{billing,analytics,users,channels}.ts` — +4 client fns, +4 type groups.
- `web_portal/src/hooks/use{Billing,Analytics,User,Channel}Queries.ts` — +4 hooks.

### Deferred
- Redis 60s TTL кэш по `attention:{user_id}` — пока прямой DB-запрос.
- Invalidation хуки на write-actions (payout/placement/legal updates) — ожидается
  когда cache будет включён.

🔍 Verified against: feat/s-47-ui-redesign-ds-v2 | 📅 Updated: 2026-04-20T02:50:00Z

## Phase 4 — Cabinet widgets (§§7.5–7.12) — completed 2026-04-20

### New widgets (`web_portal/src/screens/common/cabinet/`)
- **BalanceHero.tsx** — split info/success tiles, period toggle (7д/30д),
  sparkline, delta chip, secondary metrics (frozen + count), CTA.
  Feeds from `useMe` + `useFrozenBalance` + `useTransactionHistory` and computes
  running balance spark client-side.
- **PerformanceChart.tsx** — dual-line SVG (600×200) income/expense with gradient
  areas, grid + X/Y ticks + end dots, 7|30|90-day toggle backed by `useCashflow`.
- **QuickActions.tsx** — 6-tile grid, advertiser + owner variants (role prop),
  iconed tiles with tone-colored icon pill + chevron.
- **NotificationsCard.tsx** — attention feed rows with severity-colored square
  icon, relative timestamp, click-through `item.url`. Uses `useAttentionFeed`.
- **ProfileCompleteness.tsx** — SVG ring (R=26, 5-step), checklist with
  strike-through on done; steps derived from `useMe` + `useMyLegalProfile` +
  `useContracts('advertiser_framework')`.
- **RecommendedChannels.tsx** — horizontal 5-card grid, avatar OKLCH hue by
  channel id, tier badges (Premium / Verified), subs+ER breakdown.
  Uses `useRecommendedChannels(5)`.
- **RecentActivity.tsx** — tabs Транзакции / Кампании with live counts.
  TX rows: tone icon + amount (+/−/frozen), campaign rows: status pill + price.

### `Sparkline` shared primitive (`web_portal/src/shared/ui/Sparkline.tsx`)
- Inline SVG area + line, per-instance gradient id (no DOM collision),
  defaults `color=currentColor`.

### Cabinet shell (`web_portal/src/screens/common/Cabinet.tsx`) — rewrite
- Role caps + wave icon + greeting h1 + subtitle.
- Two CTAs (secondary Отчёт → `/adv/analytics`; primary Создать кампанию).
- BalanceHero as first grid block.
- Two-column 1.6fr/1fr grid: chart + actions left, attention + profile right.
- RecommendedChannels row, RecentActivity full-width, compass footer waterline.

### Verification
- `npx tsc --noEmit -p tsconfig.app.json` → 0 errors.
- All widgets tolerate loading/error/empty states.

## Phase 2 — PortalShell v2 (§7.3) — completed 2026-04-20

### New files
- **Sidebar.tsx** (`web_portal/src/components/layout/`) — 6 grouped nav
  sections (Финансы / Реклама / Каналы / Юридический / Прочее / Админ),
  live count chips from `useMyChannels` + `useMyPlacements('active')`,
  badges (plan label), gradient-anchor logo, waterline divider,
  collapsed-mode via `portalUiStore.sidebarMode`.
- **Topbar.tsx** — sidebar toggle, breadcrumb map (~30 routes), search-stub
  button with ⌘K mono-font tail, bell with red-dot driven by
  `useAttentionFeed().total`.

### `PortalShell.tsx` — rewrite
- Thin composition: `IconSpriteLoader` + mobile overlay + Sidebar + Topbar
  + `<Outlet/>` + optional AcceptRules notification.
- No lucide-react imports (migrated to DS v2 sprite).

### Verification
- `npx tsc --noEmit -p tsconfig.app.json` → 0 errors.
- `docker compose up -d --build nginx api` → containers rebuilt, nginx healthy,
  api up. All 4 new endpoints register (verified via `/api/openapi.json`):
  `/api/billing/frozen`, `/api/analytics/cashflow`, `/api/users/me/attention`,
  `/api/channels/recommended` — each returns 401 without JWT (route matches).

## Deferred to next sessions (not in S-47 base branch yet)

These are the explicit out-of-scope items for this session — follow-ups in
next S-47 chunk(s) before merge to develop:

- **Phase 5 (§7.5a)** — 13 pre-designed handoff screens: Plans, TopUp,
  TopUpConfirm, TransactionHistory, ReputationHistory, MyActs, Referral,
  Help, Feedback, LegalProfileSetup, ContractList, DocumentUpload, AcceptRules.
- **Phase 6 (§7.17)** — ~25 screens without handoff mockups
  (advertiser wizard + owner + admin) with design-from-tokens interpretation.
- **Phase 7 (§§7.13, 7.15, 7.18, 7.19)** — role switcher store + Topbar pill,
  density toggle, a11y pass (`:focus-visible`, ARIA landmarks, reduced-motion),
  perf/bundle measurement.
- **Phase 8 (§§7.2, 7.17 aftermath)** — flip `no-restricted-imports` from
  `warn` to `error` for `lucide-react` after all call-sites migrated; assert
  `grep -rn "from 'lucide-react'"` → 0 in `web_portal/src`.
- **Backlog** — §7.14 (⌘K Command Palette full), §7.20 (Storybook).

Shell/Cabinet/Backend base is sufficient to land standalone without breaking
the portal — the legacy screens continue to work under the DS v2 tokens
that were already in place.

🔍 Verified against: feat/s-47-ui-redesign-ds-v2 (post `09d91d4`) | 📅 Updated: 2026-04-20T03:00:00Z
