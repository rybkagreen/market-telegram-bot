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
