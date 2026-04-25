# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed — Phase 1 §1.B.0b: audit middleware refactor in place (PF.4) (2026-04-25)

Closes Phase 0's `FIXME(security)` on `_extract_user_id_from_token`. The
middleware no longer re-decodes the JWT (the previous pattern decoded
without signature verification — safe in practice because the auth dep
ran first, but a code smell). Identity now flows through `request.state`,
populated by the auth dependency.

- `src/api/dependencies.py::_resolve_user_for_audience` — accepts
  `request: Request | None`; on success, writes `request.state.user_id`
  and `request.state.user_aud` (the JWT `aud` claim).
- Public deps `get_current_user`, `get_current_user_from_web_portal`,
  `get_current_user_from_mini_app` now take `request: Request` as their
  first parameter (auto-injected by FastAPI). Tests pass a stub.
- `src/api/middleware/audit_middleware.py` — `_extract_user_id_from_token`
  helper deleted. `dispatch` reads
  `getattr(request.state, "user_id", None)` and adds the `aud` claim
  to the audit-log `extra` dict.
- `/api/acts/*` added to sensitive prefixes; `_path_to_resource_type`
  now returns `"act"` for that prefix.
- New test cases in `tests/unit/api/test_jwt_aud_claim.py`:
  `test_resolve_writes_user_id_and_aud_to_request_state_mini_app`,
  `test_resolve_writes_user_aud_web_portal`. `tests/integration/test_ticket_bridge_e2e.py`
  step 4 also asserts the state contract.
- `audit_middleware.py` removed from CLAUDE.md NEVER TOUCH (PF.4 lifted
  the freeze for this refactor).

### Breaking — Phase 1 §1.B.0a: legacy aud-less JWT rejected with 426 instead of 401 (2026-04-25)

Phase 0 shipped 401 for aud-less JWT (`src/api/dependencies.py:67`). PF.2
research found this semantically imprecise — RFC 7231 §6.5.15 426 Upgrade
Required communicates "your token format is obsolete, re-authenticate"
more precisely than 401 ("credentials missing or wrong"). Pre-prod
fact-check (DB users / Redis sessions / api logs) confirmed zero active
legacy-token holders, so the flip is a pure signal-correctness change.

Bonus fix in the same commit: the aud-less branch previously omitted
`WWW-Authenticate: Bearer`, while the missing-credentials branch at
`dependencies.py:44-49` always set it. Both branches now match RFC 7235
§3.1 SHOULD-include guidance.

- `_resolve_user_for_audience` aud-less branch: `HTTP_401_UNAUTHORIZED`
  → `HTTP_426_UPGRADE_REQUIRED` + `headers={"WWW-Authenticate": "Bearer"}`.
- `tests/unit/api/test_jwt_aud_claim.py::test_case3_*` updated to assert
  the new status + header.

### Added — Phase 0: ENABLE_E2E_AUTH flag, centralised URLs, JWT `aud` + ticket bridge (2026-04-25)

Production-readiness Phase 0 (`feature/env-constants-jwt-aud`). Six
commits, all sub-phases green; full report:
`reports/docs-architect/discovery/CHANGES_2026-04-25_phase0-env-constants-jwt.md`.

- **JWT now carries an explicit `aud` claim** (`mini_app` or `web_portal`).
  - New endpoints:
    - `POST /api/auth/exchange-miniapp-to-portal` — mints short-lived
      ticket-JWT (default TTL 300s) for a mini_app session. Stores
      `auth:ticket:jti:{jti}` in Redis with `{user_id, issued_at, ip}`.
    - `POST /api/auth/consume-ticket` — public endpoint, manual Redis
      INCR+EXPIRE rate-limits (10 req/min/IP, 5 fails/5min/user). One-shot
      Redis DELETE on jti — replay returns 401 with structured WARN log.
  - New dependencies: `get_current_user_from_web_portal` (rejects mini_app
    JWT with 403 — used by ФЗ-152 paths in Phase 1) and
    `get_current_user_from_mini_app` (used by the bridge endpoint).
  - New Pydantic schemas `TicketResponse`, `AuthTokenResponse` with
    snapshot-pinned contracts.
- **New settings** in `src/config/settings.py`: `enable_e2e_auth`,
  `mini_app_url`, `web_portal_url`, `landing_url`, `api_public_url`,
  `tracking_base_url`, `terms_url`, `ticket_jwt_ttl_seconds`,
  `sandbox_telegram_channel_id`. Subdomain-correct defaults
  (`portal.rekharbor.ru`, `t.rekharbor.ru`, `app.rekharbor.ru/`).
- **New** `src/constants/erid.py` with `ERID_STUB_PREFIX = "STUB-ERID-"`
  (provider type — orthogonal to placement-test-mode in Phase 5).
- **New tests**: `tests/unit/api/test_jwt_aud_claim.py` (9 cases) and
  `tests/unit/api/test_jwt_rate_limit.py` (2 cases). FakeRedis stub +
  monkeypatched session factory — sub-second runs.

### Changed — Phase 0 hygiene (2026-04-25)

- 8 hardcoded `rekharbor.ru` URLs in `src/` replaced with `settings.*`
  references (CORS, bot menu webapp, legal-profile portal redirect, ToS
  link, /login code template, publication post tracking, link-tracking
  service ×2). 2 mini_app fallbacks (`LegalProfileSetup`,
  `LegalProfilePrompt`) now read `import.meta.env.VITE_PORTAL_URL`
  without a hidden hardcode.
- `create_jwt_token` requires `source: Literal["mini_app", "web_portal"]`.
  All four token-issuing endpoints updated.
- `decode_jwt_token` requires positional `audience` argument (no default).
  `None` is the explicit opt-out for legacy/audit helpers.
- `ENABLE_E2E_AUTH` replaces the `ENVIRONMENT == "testing"` check at
  `src/api/main.py:193` (`/api/auth/e2e-login` mount gate).
- `scripts/check_forbidden_patterns.sh` extended with three new guards
  on hardcoded `rekharbor.ru` URLs across `src/`, `mini_app/src/`,
  `web_portal/src/`.
- `docker/Dockerfile.nginx` carries `ARG VITE_PORTAL_URL` in the
  `builder-miniapp` stage; `docker-compose.yml` pipes
  `${VITE_PORTAL_URL:-https://portal.rekharbor.ru}` into the build args.
- `audit_middleware.py` carries a one-line `FIXME(security)` comment on
  the unsigned-JWT decode helper. No logic change.

### Fixed — Phase 0 (2026-04-25)

- Typo `rekhaborbot.ru → rekharbor.ru` in `src/constants/legal.py`
  (4 sites: lines 53, 83, 107, 108).

### Removed — Phase 0 (2026-04-25)

- `src/config/__init__.py` — dead parallel `Settings` class with zero
  importers across `src/` and `tests/`.
- `environment` field, `is_development/is_production/is_testing`
  properties, and the `environment` key in `/health` JSON response.
- `ENVIRONMENT=` from `.env.example`, `.env.test.example`. `.env`,
  `.env.test` updated locally (gitignored, not part of this commit).

### Breaking — Phase 0 (2026-04-25)

- All JWTs issued before this phase **lack the `aud` claim** and are
  rejected with `401: Invalid token: missing audience claim`. Pre-prod
  policy — one re-login per existing session is the migration cost.
  After Phase 1 ships, ФЗ-152 paths additionally reject mini_app-aud
  tokens with 403.

### Changed — Project rules: objections section + phase mode discipline (2026-04-25)

Documentation-only update to `CLAUDE.md` and `IMPLEMENTATION_PLAN_ACTIVE.md`.
No `src/` or runtime changes. Triggered by Phase 0 research stop-point
review where the consolidation report rubber-stamped a known-imprecise
plan directive and proposed a "WARN-and-accept" legacy JWT fallback. See
`reports/docs-architect/discovery/CHANGES_2026-04-25_meta-rules-objections-phase-discipline.md`.

- New `CLAUDE.md` section **"Research reports — Objections section
  (MANDATORY)"** before "Documentation & Changelog Sync". Three
  sub-rules:
  - Research reports must contain a "Возражения и риски" section *before*
    "Вопросы для подтверждения". Five categories listed (security,
    contradictions, missed edge cases, bad naming, API ergonomics traps).
    Disguising objections as confirmation questions is prohibited.
  - **Phase mode discipline:** research/planning = critical, dispute
    decisions; implementation = execute as written, stop only on blocking
    issues, no scope creep.
  - **Raise-vs-defer split:** four blocking categories (security, bugs,
    contradictions, future-maintenance burden) raised explicitly; five
    cosmetic categories (refactors, style, untouched-code coverage,
    unmeasured perf, naming preferences) deferred to a one-line footnote.
- Same three rules mirrored into `IMPLEMENTATION_PLAN_ACTIVE.md`
  "Общие правила" so each phase's resume prompt picks them up
  automatically.
- `IMPLEMENTATION_PLAN_ACTIVE.md` Phase 0 sections rewritten to bake in
  security-hardened decisions (legacy aud-less → 401 not WARN;
  `decode_jwt_token` audience required; `/consume-ticket` rate-limit +
  replay logging; JTI value with context not `"1"`; `STUB-ERID` retained
  not renamed; VITE_PORTAL_URL fallback removed; `audit_middleware`
  FIXME-only). Test count raised from 3 to 8 functional + 2 rate-limit.

### Changed — Consolidated escrow pipeline + unified Bot factory (2026-04-24)

Diagnostic of a reported "advertiser vs owner status desync" exposed
three architectural defects in the escrow path. All fixed in one
coordinated change; see
`reports/docs-architect/discovery/CHANGES_2026-04-24_escrow-pipeline-bot-factory.md`.

- `BillingService.freeze_escrow(...)` removed. All freeze paths now
  go through `BillingService.freeze_escrow_for_placement(placement_id,
  advertiser_id, amount, is_test=False) -> Transaction`. The unified
  method is idempotent (`escrow_freeze:placement={id}`), updates
  `platform_account.escrow_reserved`, and returns the created
  Transaction so callers can persist `escrow_transaction_id`.
- `PlacementRequestService._freeze_escrow_for_payment` no longer has
  an `is_test` shortcut that skipped billing. `is_test=true` now
  creates a normal freeze transaction (with the given `amount`,
  not zero) that just doesn't deduct `user.balance_rub`. This removes
  all downstream NULL-handling for `escrow_transaction_id` and
  `final_price`.
- Bot handler `camp_pay_balance` rewritten to delegate to
  `PlacementRequestService.process_payment()`. Direct
  `req.status = PlacementStatus.escrow`, direct `billing.freeze_escrow`,
  and duplicated `schedule_placement_publication.delay(...)` removed.
- New `src/bot/session_factory.py` with `new_bot()` — the single
  factory for aiogram `Bot` instances. It applies
  `AiohttpSession(proxy=settings.telegram_proxy)` automatically.
  Used by `src/bot/main.py`, `src/tasks/_bot_factory.py`, and
  `src/utils/telegram/sender.py`. Fixes all Celery Bot calls failing
  with `TelegramNetworkError` on proxy-required hosts.
- `settings.telegram_proxy` now validated at boot: must start with
  `socks5://`, `socks4://`, `http://`, or `https://`.
- `scripts/check_forbidden_patterns.sh` extended with two Python
  guards: aiogram `Bot(token=...)` outside the factory; direct
  `.status = PlacementStatus.escrow` outside the repository.

### Breaking

- **Python API:** `BillingService.freeze_escrow` removed. Callers
  must migrate to `freeze_escrow_for_placement` (different kwargs:
  `advertiser_id` in place of `user_id`, returns `Transaction`,
  new `is_test` flag).

### Fixed — DB invariant for escrow state (INV-1)

- New `CHECK constraint placement_escrow_integrity` on
  `placement_requests`: `status != 'escrow' OR
  (escrow_transaction_id IS NOT NULL AND final_price IS NOT NULL)`.
  Prevents any future code path (accidental direct SQL, migration
  backfill, flaky service) from persisting a broken escrow row.

### Migration Notes

- Pre-production rule applies: initial migration
  `src/db/migrations/versions/0001_initial_schema.py` was edited
  in place. DB dropped and re-created with `dropdb && createdb &&
  alembic upgrade head`. `alembic check` clean.

### Fixed — Cabinet account card + unified list cards on mobile (2026-04-24, phase 4)

- `Cabinet.tsx` account card — previously rendered on mobile as four
  disconnected pieces (avatar / 3 label-value pairs / logout button
  stacked). Now a single horizontal row: avatar + name with
  `@handle · telegram_id` meta + 44×44 icon-only logout. Desktop layout
  preserved.
- Unified list-card pattern across Кампании (`MyCampaigns`),
  Размещения (`OwnRequests`), Каналы (`OwnChannels`). All three
  follow the same mobile skeleton now: status-avatar + title/id/meta
  header + date↔price row + right-justified action row.
  - `MyCampaigns`: row was a single tight flex that squeezed into
    343px; now `flex flex-col sm:flex-row`.
  - `OwnChannels`: category chip pulled into the header instead of
    its own mobile row; edit-mode category picker rendered as a
    full-width row only on mobile. Card drops from 4 to 3 visual
    sections on mobile.

Breaking: none. Pure UI.

### Fixed — web_portal mobile jitter + residual bugs (2026-04-24, phase 3)

Follow-up after user reported (a) remaining visible bugs on 4 screens
(Каналы, Пополнить, Размещение, Выплаты) and (b) horizontal jitter /
"экраны не зафиксированы по вертикали" across most screens.

**Root cause of jitter — fixed globally:**
- `PortalShell.tsx` main scroll container — `overflow-y-auto` →
  `overflow-x-hidden overflow-y-scroll [scrollbar-gutter:stable]
  overscroll-contain`. Reserves scrollbar gutter so the content doesn't
  shift horizontally when the scrollbar appears/disappears; clips
  accidental horizontal overflow; prevents scroll-chain to body.
- `globals.css` — `html` and `body` now `overflow-x: hidden; height:
  100%; overscroll-behavior: none` — stops iOS rubber-band at the
  document root.
- Removed `hover:-translate-y-0.5` from three components (`Plans`
  PlanCard, `OwnChannelDetail` ActionTile, cabinet `QuickActions`) —
  on touch devices the sticky `:hover` state caused rows to stay
  shifted by -2px after a tap, creating visible layout jumps
  ("UI не зафиксирован жестко"). Replaced with
  color/border-only hover feedback.

**Residual per-screen bugs:**
- `TopUp.tsx` — removed a duplicated-and-shadowed class pair
  (`w-8.5 h-8.5 w-[34px] h-[34px]`).
- `TopUpConfirm.tsx` — inline 3-column grid-template replaced with
  responsive `grid-cols-1 sm:grid-cols-3` so the 3 action buttons no
  longer squeeze onto one row on 375px.
- `OwnRequests.tsx` — request row rewritten as a stacked card on
  `<sm` (icon + channel + id header, ad-text + date + inline price,
  action below); desktop grid preserved.
- `OwnRequestDetail.tsx` — ad_text gains `break-words
  [overflow-wrap:anywhere]` so long URLs/tokens no longer overflow
  the 343px card.
- `OwnChannelDetail.tsx` — redundant "Активен / Скрыт" uppercase
  pill replaced with an avatar-colour + small dot-indicator
  (aria-label preserved for screen readers).
- `OwnPayouts.tsx` — hero amount `text-[34px]` now `text-[26px]
  sm:text-[34px] break-words` to avoid 6+ digit clipping on 375px;
  meta row wraps.
- `PerformanceChart.tsx` — three-metric header `gap-6` → `flex-wrap
  gap-3 md:gap-6` so Доходы/Расходы/Нетто don't run off a 343px row.
- `advertiser/campaign/_shell.tsx` — removed redundant
  `overflow-x-auto` wrapper around `StepIndicator` (indicator
  manages its own horizontal overflow).

Breaking: none. Pure UI.

### Fixed — web_portal mobile deep-sweep phase 2 (2026-04-24)

Follow-up sweep across every remaining screen (Cabinet, Common, Shared,
Owner, Advertiser wizard, Admin, Analytics). 26 files + 1 new generic
mobile component (`MobileDataCard`) in 5 sub-phases. Pure UI; zero API /
DB / business-logic impact.

- **Shared UI**: `Input` and `Textarea` now enforce 44px+ tap targets
  (`min-h-11` / `min-h-[88px]`). `StepIndicator` collapses step labels
  to active-only + horizontal scroll on mobile. `Sparkline` grew a
  `responsive` prop that stretches to container width — fixes the
  Cabinet/BalanceHero horizontal overflow (sparkline was hardcoded
  `width={420}` on 375px viewport). New `.safe-bottom` utility in
  `globals.css` applies `env(safe-area-inset-bottom)` to fixed footers.
- **Layout-killer grids (6 screens)**: AcceptRules, DocumentUpload,
  Feedback, Help, LegalProfileSetup, Plans — all had inline
  `gridTemplateColumns` with fixed 220–360px side panels that
  crushed the main column on 375px. Migrated to responsive
  `grid-cols-1 lg:[grid-template-columns:...]`. Plans comparison
  table got `overflow-x-auto` + `sticky left-0` feature column.
- **Table → stack on mobile (3 screens)**: MyActsScreen (two 6-column
  grids), ReputationHistory (4-col), TransactionHistory (4-col) — each
  now `hidden md:grid` on desktop, stacked mobile render with labels
  inline. Download/PDF buttons sized to 44×44 on mobile.
- **Admin tables (4 screens)**: AdminUsersList, AdminTaxSummary,
  AdminPayouts, ChannelDeepDive — `sticky left-0` on first column of
  `overflow-x-auto` tables; `min-w-[260-320px]` values relaxed on
  mobile.
- **Cabinet**: `BalanceHero` sparkline now responsive; CTA buttons
  (Пополнить / К выплате) 44px on mobile. Top header reviewed —
  reported "АДМИН ПАНЕЛЬ overlap" could not be reproduced; no sticky
  or z-index conflicts exist in current layout.
- **Fixed bottoms**: OwnChannels compare bar, campaign wizard footer,
  CampaignVideo footer all gained `safe-bottom` utility.
- **Status pills**: removed redundant uppercase-text labels next to
  icon-avatars in 4 files where the duplication was real
  (DisputeDetail, MyDisputes, OwnRequests, AdminDisputesList). The
  remaining ~13 places where text is the sole indicator (icon lives
  inside the pill, not in a separate avatar) were left intact.

Total: 26 files touched, ~600 insertions / ~300 deletions.

Verified: typecheck + lint + vite build clean. Playwright not run —
not installed in `web_portal/node_modules` (same condition as phase 1
session). Manual QA at 375/390 Chrome DevTools recommended before
merge.

### Fixed — web_portal mobile layout on 375/390px (2026-04-24)

Systemic mobile-viewport cleanup on `portal.rekharbor.ru` across six
high-traffic screens. Cabinet intentionally left untouched (out of
scope). No API / DB / business-logic changes.

- **TopUp**: dropped the inline `grid-template-columns: minmax(0,1fr)
  360px` that was the root cause of the "vertical text on the left
  edge" artefact on narrow viewports — the right column tried to reserve
  360px on a ~343px content width, crushing the left column to ~0px.
  Now single-column on `<md`, 2-col on `md+`. Sticky summary panel
  becomes in-flow on mobile.
- **Referral**: the `1.6fr / minmax(280px,1fr)` grid squeezed "Ваши
  рефералы" to ~60px on 375px (visually hidden under "Как это
  работает"). Replaced with responsive single-column on `<md`. All
  inline grid styles converted to responsive Tailwind arbitrary
  `[grid-template-columns:…]` variants. Active/new referral label
  collapsed to a dot indicator with aria-label.
- **OwnPayouts**: history row was a flex-row with hard `min-w-[160/120]`
  cells, which clipped the "ЗАПРОШЕНО"/"К ЗАЧИСЛЕНИЮ" column headers
  on mobile. Refactored to a stacked mobile card: icon + `#id` + date
  in the header, amounts in a 2-column grid below. Removed the
  redundant uppercase status label; status is conveyed by icon colour +
  `aria-label`/`title`.
- **MyCampaigns**: filter pills gain a horizontally-scrollable strip
  with `snap-mandatory` on `<sm`; kept `flex-wrap` on `sm+`. Sort
  control stacked on its own row on mobile. `FilterPill` gets
  `flex-shrink-0 snap-start`.
- **OwnChannels**: bottom action cluster gets 44×44 tap targets on
  mobile (via `!w-11 !h-11 @3xl:!w-8 @3xl:!h-8` per button) and wider
  gap (`gap-2`). The "Активен/Скрыт" uppercase label next to
  `@username` replaced with a dot-in-circle indicator.
- **ContractList**: per-row grid (`1.4fr 2fr 1.2fr 0.9fr auto`) now
  stacks into a mobile card (icon + `#id` + type on row 1, period on
  row 2, status dot, full-width buttons). Date format switched from
  `'19 апр. 2026 г.'` to `'19.04.2026'`. New helper `fmtPeriod` yields
  `'DD.MM.YYYY — бессрочно'` when `expires_at` is null. Status pill
  reduced to dot-only on desktop per brief rule (icon/colour is
  self-sufficient). PDF download button is 44×44 on mobile.

Breaking: none. Contract-drift guard unaffected (no schema changes).

### Added — Unified `/analytics` screen with Mistral AI insights (2026-04-23)

Replaces `/adv/analytics` and `/own/analytics` with a single `/analytics`
that shifts focus from duplicated KPIs (already on Cabinet) to real
AI-generated narrative, actionable recommendations, a per-period
forecast, detected anomalies, and a role-aware channel deep-dive with
AI-assigned flags.

- **Backend**: new `GET /api/analytics/ai-insights?role={advertiser|owner}`
  returning `AIInsightsUnifiedResponse`. Calls Mistral with a strict-JSON
  prompt (8 s timeout, Redis-cached 15 min per `ai_insights:{user_id}:{role}:v1`);
  on any Mistral failure (missing key, timeout, invalid JSON) transparently
  falls back to a deterministic rule-based engine with the same output
  shape, surfacing `ai_backend: "rules"` for UI badge display. Existing
  `/analytics/advertiser`, `/analytics/owner`, `/cashflow`, `/summary` etc.
  are untouched.
- **Service**: new method `AnalyticsService.generate_unified_insights`
  plus helpers (`_rules_advertiser`, `_rules_owner`,
  `_sanitize_mistral_payload`) in `src/core/services/analytics_service.py`.
  Reuses existing `get_advertiser_stats` / `get_owner_stats` /
  `get_top_channels_by_reach`.
- **web_portal**: new `screens/common/Analytics.tsx` + four subcomponents
  (`AIInsightCard`, `ChannelDeepDive`, `TrendComparison`, `RoleTabs`).
  The AI insight card is the hero element — narrative summary, up to
  three action items with estimated impact and CTAs, forecast strip,
  severity-coded anomalies, and a Mistral/Rules backend badge.
- **mini_app**: parallel `screens/common/Analytics.tsx` (no chart
  library; leaner layout for Telegram WebApp).
- **Contract drift guard**: `AIInsightsUnifiedResponse` registered in
  `tests/unit/test_contract_schemas.py` with a new JSON snapshot.
- **Tests**: 15 service-layer unit tests + 5 HTTP endpoint tests.

### Changed — Analytics navigation consolidated (2026-04-23)

- **web_portal**: Sidebar collapses two legacy "Аналитика" entries
  (under "Реклама" and "Каналы") into a single entry under a new
  dedicated "Аналитика" section. Topbar breadcrumb entries for the old
  paths are removed; `/analytics` has its own breadcrumb.
- **web_portal / mini_app**: `/adv/analytics` and `/own/analytics` now
  `<Navigate replace />` to `/analytics?role=<role>` — bookmarks and
  notification deep-links continue to work.
- **web_portal**: Cabinet header CTA ("Отчёт" → "Аналитика"),
  QuickActions owner tile, and post-publication redirect on
  `CampaignPublished` all point at `/analytics`.
- **mini_app**: `AdvMenu`, `OwnMenu`, and `CampaignPublished` navigate
  to `/analytics`.
- **Playwright**: `web_portal/tests/fixtures/routes.ts` replaces the two
  legacy route entries with a single `/analytics` under common routes.

### Removed — Legacy per-role analytics screens (2026-04-23)

- `web_portal/src/screens/advertiser/AdvAnalytics.tsx`
- `web_portal/src/screens/owner/OwnAnalytics.tsx`
- `mini_app/src/screens/advertiser/AdvAnalytics.tsx` + `.module.css`
- `mini_app/src/screens/owner/OwnAnalytics.tsx` + `.module.css`

### Migration Notes — Unified analytics

- After rebuilding containers (`docker compose up -d --build nginx api`),
  the legacy URLs redirect transparently — no user action required.
- If `MISTRAL_API_KEY` is not set in the API container's environment,
  the feature continues to work using the rule-based engine (badge
  displays "Rules" instead of "AI"). No 500s, no blank screens.
- **Pre-existing issue noted (not fixed)**: the notification button
  callback `analytics:by_campaign:{campaign_id}` emitted from
  `src/tasks/notification_tasks.py:660` has no handler anywhere in the
  codebase. Separate ticket recommended.

### Changed — RekHarbor logo refresh (2026-04-23)

Swaps placeholder anchor/emoji/RH-badge marks across all frontends
for the new brand-grade RekHarbor logo (icon + wordmark).

- **web_portal**: new `public/brand/` folder holds four SVG variants
  (`rekharbor_full_light`, `rekharbor_full_dark`,
  `rekharbor_icon_teal`, `rekharbor_icon_dark`). `Sidebar.tsx` and
  `LoginPage.tsx` render them via `<picture>` with
  `<source media="(prefers-color-scheme: light)">` so the correct
  light/dark variant loads natively without JS. The old gradient-box
  `<Icon name="anchor">` + literal `RekHarbor` span in the sidebar
  is gone; the old `⚓` emoji + `<h1>` duo in `LoginPage` is gone.
- **web_portal**: added `public/favicon.svg` (was missing — `index.html`
  referenced a 404).
- **mini_app, landing**: `favicon.svg` replaced with the new teal icon
  (was `⚓`-on-gradient and `RH`-badge respectively).
- **landing**: `public/assets/og-cover.svg` (1200×630) rewritten with
  the new full logo and brand accent `#14A5A8`.

No API, DB, FSM, Celery task, or Pydantic schema changes; purely visual.

Follow-up same day: (1) retargeted all brand colours from placeholder
teal `#14A5A8` to the real portal accent `#00AEEE` (= `oklch(0.70 0.16
230)`) and text-primary `#0C121A` / `#E1E5EB`; (2) fixed a logo-swap
bug in the sidebar where React reused the `<img>` DOM node across the
ternary branches — old full logo was rendered squished into the new
32×32 attrs while the new SVG loaded, creating a "shrinking" illusion
instead of a clean swap. Resolved via `key` props forcing a remount
plus explicit pixel dimensions.

### Changed — plan-06 integration test SAVEPOINT isolation (2026-04-21)

Replaces the TRUNCATE-based cleanup in
`tests/integration/test_payout_lifecycle.py` with the SQLAlchemy 2
"join into an external transaction" pattern. All sessions opened by
`PayoutService` (via `async_session_factory`) now bind to a single
connection wrapped in an outer transaction;
`join_transaction_mode="create_savepoint"` makes the service's
internal `session.begin()` open a SAVEPOINT, and the outer rollback
discards everything at test end.

- **Modified** `tests/integration/test_payout_lifecycle.py`:
  rewritten `bound_factory` (savepoint-bound), removed
  `_cleanup_after_test` autouse fixture (outer rollback replaces
  TRUNCATE), removed unused `text` / TRUNCATE machinery.
- **Modified** `tests/integration/test_payout_concurrent.py`:
  docstring updated to flag the deliberate use of engine + TRUNCATE
  (Pattern C) — SAVEPOINT cannot serve `asyncio.gather` on a single
  asyncpg connection.
- **New** `tests/integration/README.md`: documents the three
  legitimate session isolation patterns (A — service accepts
  session, B — savepoint, C — engine + TRUNCATE) with a decision
  tree and four common pitfalls.

Benefits over TRUNCATE+RESTART: no `RESTART IDENTITY` masking
ordering bugs, no cross-test state leakage, parallel-safe
(`pytest -n` won't deadlock), faster (SAVEPOINT release ≪
TRUNCATE … RESTART IDENTITY at scale).

Validation: 4 lifecycle tests green across 3 consecutive runs; full
payout slice (lifecycle + concurrent) → 7 passed. No `src/` change.

### Fixed — plan-02 concurrent payout approve / reject race (2026-04-21)

Closes a financial double-spend race in
`PayoutService.approve_request` / `reject_request`. The pre-fix code
ran in three sequential sessions (status check → financial move →
admin_id stamp); two parallel admin clicks could both pass the
status check in independent sessions, causing
`PlatformAccount.payout_reserved -= gross` to apply twice (and the
USN expense to be recorded twice). Same class of bug as ESCROW-002.

**Modified — `src/core/services/payout_service.py`:**
- `approve_request` and `reject_request` rewritten to a single
  session under `async with session.begin():` whose first statement
  is `select(PayoutRequest).where(id=…).with_for_update()`.
  Concurrent admins now serialize on the row lock; the second
  arrival sees the already-finalized status and raises
  `ValueError("already finalized")`.
- Lock order documented (`PayoutRequest → PlatformAccount`) and
  identical between approve and reject — no approve↔reject
  deadlock.
- `complete_payout` and `reject_payout` no longer open their own
  `async with session.begin():`. Per Service Transaction Contract
  (CLAUDE.md § S-48), the outermost caller owns the transaction;
  these methods now `flush` only. Audit confirmed both methods are
  called only by `approve_request` / `reject_request` (no external
  callers).

**New — `tests/integration/test_payout_concurrent.py` (3 tests):**
- `test_three_concurrent_approves_yield_one_success` — 3 ×
  `approve_request` via `asyncio.gather`; asserts exactly 1 success
  and `platform.payout_reserved == 0` (would land at `-gross` /
  `-2*gross` pre-fix).
- `test_concurrent_approve_then_reject_one_wins` — `approve` ‖
  `reject`; asserts exactly 1 winner with state consistent with the
  winner.
- `test_three_concurrent_rejects_yield_one_success` — 3 × `reject`;
  asserts `owner.earned_rub == gross` (not `2*gross` / `3*gross`).

Validation: 16 passed across `test_payout_lifecycle.py` (4) +
`test_payout_concurrent.py` (3) + `test_admin_payouts.py` (9). Ruff
clean. Grep-guard 7/7. No DB migration; no public-API change.

### Added — plan-03 placement PATCH coverage completion (2026-04-21)

Closes the gaps in `tests/unit/api/test_placements_patch.py` left
after FIX_PLAN_06 §6.6: 2 of 7 PATCH actions had no tests, and the
router's three error branches (`HTTPException`, `ValueError → 409`,
`Exception → 500`) — all of which call `session.rollback()` — were
unreachable from the suite because every previous test mocked the
service with `return_value=…` and never raised.

- **Modified** `tests/unit/api/test_placements_patch.py` — +11 unit
  tests (5 new classes), now 22 total:
  - `TestPatchAcceptCounter` (3) — `accept-counter` happy path,
    409 wrong status, 403 owner-not-advertiser.
  - `TestPatchCounterReply` (3) — `counter-reply` happy path with
    price+comment (4-arg autospec match — FIX #20 / S-45 safety
    net), 400 missing price, 403 owner-not-advertiser.
  - `TestPatchRejectReasonCode` (1) — router falls back to
    `reason_code` when `reason_text` is absent.
  - `TestChannelNotFound` (1) — placement exists but channel was
    deleted → 404.
  - `TestErrorPathsCallRollback` (3) — ESCROW-002 regression
    guard: `ValueError`, `HTTPException`, `RuntimeError` all
    assert `session.rollback.assert_awaited_once()` and
    `session.commit.assert_not_awaited()`.
- New fixtures `session_spy`, `client_as_owner_with_spy`,
  `client_as_advertiser_with_spy` — share one session-mock between
  the dependency-override and the test so `rollback` / `commit`
  call counts can be inspected after the request returns.

Validation: `pytest tests/unit/api/test_placements_patch.py` →
22 passed; ruff clean; grep-guard 7/7.

### Changed — plan-08 deferred E2E flows formalized in BACKLOG.md (2026-04-21)

Three `test.fixme(true, …)` blocks in
`web_portal/tests/specs/deep-flows.spec.ts` had no trackable
re-activation contract — they were sliding toward permanent dead
code. Now each one references a BL-ID in the new project backlog.

- **New** `reports/docs-architect/BACKLOG.md` — top-level project
  backlog. Three deferred items:
  - **BL-001** Dispute round-trip — needs seed-fixture (escrow
    placement + open disputable window).
  - **BL-002** Channel add via bot verification — needs Telegram Bot
    API mock in `docker-compose.test.yml`.
  - **BL-003** KEP signature on framework contract — needs
    КриптоПро stub or `signature_method=sms_code` fallback.
- **Modified** `.gitignore` — `!reports/docs-architect/BACKLOG.md`
  exception so the new backlog file escapes the broad `reports/*`
  ignore.
- **Modified** `web_portal/tests/specs/deep-flows.spec.ts` — all
  three fixme blocks rewritten: `test.fixme(true, reason)` + empty
  `test()` → single `test.fixme(title, body)` whose title points at
  the BL-ID, body holds the re-activation hint as a comment.
- **Modified** `CLAUDE.md` — added `## Deferred E2E items (plan-08)`
  with the BL-ID table and a rule against silent
  `test.fixme(true, …)` blocks going forward.

Validation: TypeScript clean. No `src/` changes.

### Added — plan-04 list-response contract snapshots (2026-04-21)

Closes the drift-guard gap left by FIX_PLAN_06 §6.1 Variant B: only
item schemas (`UserResponse`, `PlacementResponse`, …) were locked,
but the web_portal admin pages and Mini App actually consume the
**pagination wrapper** shape (`{items, total, limit, offset}`). A
rename of `total → count` or `items → rows` would have been invisible
to the contract-check CI.

- `tests/unit/test_contract_schemas.py` — `CONTRACT_SCHEMAS` extended
  from 8 to 18 entries. Added wrappers (with the router endpoint each
  one is consumed by, in parens):
  - `AdminPayoutListResponse` (`/api/admin/payouts`),
  - `AdminContractListResponse` (`/api/admin/contracts`),
  - `UserListAdminResponse` (`/api/admin/users`),
  - `DisputeListAdminResponse` (`/api/admin/disputes`),
  - `FeedbackListAdminResponse` (`/api/admin/feedback`),
  - `DisputeListResponse` (`/api/disputes/`),
  - `FeedbackListResponse` (`/api/feedback/`),
  - `ContractListResponse` (`/api/contracts/`),
  - `CampaignListResponse` (`/api/campaigns`),
  - `CampaignsListResponse` (`/api/campaigns/list`).
- 10 new files in `tests/unit/snapshots/*_list_response.json`.
- `CLAUDE.md § Contract drift guard` rewritten — 18 schemas, explicit
  list of intentionally skipped endpoints (`GET /api/payouts/`,
  `GET /api/admin/audit-logs`) with reason.

The 8 existing item snapshots were **not** modified — verified via
`git status` after `UPDATE_SNAPSHOTS=1` regeneration.

Validation: `pytest tests/unit/test_contract_schemas.py` → 19 passed
(18 schema asserts + duplicate-guard); ruff clean; grep-guard 7/7.

### Changed — plan-01 deep-flow spec hardening (2026-04-21)

Follow-up to FIX_PLAN_06 §§6.2, 6.5, 6.6 after re-review flagged three
silent-pass regressions in the tests shipped with the previous block:

- **`web_portal/tests/specs/deep-flows.spec.ts`**
  - Channel-settings flow: PATCH path corrected
    `/api/channels/:id/settings` → `/api/channel-settings/?channel_id=:id`.
    Previously the spec hit a 404 that passed under `< 500` — the
    PATCH was never actually performed. Now asserts round-trip
    (`price_per_post` written, then read back).
  - All `status < 500` and `status < 300` replaced with explicit
    expectations (`ok()`, `[200, 201, 409]`, etc.). Any 404/422 on a
    valid request now fails the spec instead of silently passing.
  - Top-up flow: body fixed to `{ desired_amount, method: 'yookassa' }`
    (was `{ amount }`); asserts `payment_url`, not `confirmation_url`
    (the latter is the internal YooKassa SDK field). Added
    `test.skip` guard when `YOOKASSA_SHOP_ID`/`_SECRET_KEY` are not
    in the runner env, so the scenario only runs where YooKassa is
    reachable.
  - Review POST path changed to `/api/reviews/` (trailing slash) to
    match FastAPI router mount exactly and avoid a 307 that could
    drop the body.
- **`tests/unit/api/test_admin_payouts.py`** — all five
  `patch("…payout_service.{approve,reject}_request", AsyncMock(...))`
  sites rewritten to `patch.object(payout_service, name, autospec=True)`.
  Renaming or resignaturing `approve_request` / `reject_request` now
  breaks the tests at import/patch time instead of producing a green
  test on a broken service.
- **`tests/unit/api/test_placements_patch.py`** — `_patch_router_repos`
  switched from `MagicMock() + setattr(AsyncMock)` to
  `create_autospec(PlacementRequestService, instance=True, spec_set=True)`.
  Any drift in `owner_accept`, `owner_reject`, `owner_counter_offer`,
  `process_payment`, `advertiser_cancel` now fails the suite.

Validation: 20 / 20 pytest passes, ruff clean, grep-guard 7/7,
Playwright `tsc --noEmit` clean. No `src/` changes.

### Added — FIX_PLAN_06 §§6.1–6.7 finish: tests + guards + CI + docs (2026-04-21)

Closes the remaining subsections of `reports/20260419_diagnostics/FIX_PLAN_06_tests_and_guards.md`
that were not shipped with the S-47 / S-48 sprints
(contract-drift snapshots + grep-guards). Scope: **tests + tooling +
docs only**; no changes to `src/`, `mini_app/src/`, `web_portal/src/`,
`landing/src/`.

**Added — tests:**
- `tests/unit/api/test_admin_payouts.py` — 9 unit-тестов на роутер
  `/api/admin/payouts*` через `app.dependency_overrides` + мок
  `payout_service`. Покрывают 403 для не-админа, 401 для анонима, 200
  на approve/reject с корректным `AdminPayoutResponse`, 400 на
  уже-финализированную выплату, 404 на отсутствующую, 422 на пустую
  `reason`. (§6.5 unit)
- `tests/integration/test_payout_lifecycle.py` — 4 integration-теста
  поверх testcontainers + реальной Postgres-схемы. Патчит
  `async_session_factory` в `src.db.session` и
  `src.core.services.payout_service`; sessionmaker привязан к
  `test_engine`. Закрепляет финансовые инварианты approve (`pending
  → paid`, `admin_id`, `processed_at`, `platform_account.payout_reserved`
  уменьшен на gross) и reject (`pending → rejected`, `earned_rub`
  восстановлен). (§6.5 integration)
- `tests/unit/api/test_placements_patch.py` — 11 unit-тестов на
  unified `PATCH /api/placements/{id}`, заменивший legacy
  `POST /accept|/reject|/counter|/pay|/cancel` в S-44. Мокаются
  репозитории и `PlacementRequestService`. Покрывают пять action'ов
  + роль-guard (403 при попытке accept от advertiser), `price
  required` для counter, 409 при pay вне `pending_payment`, 404 на
  отсутствующий placement. (§6.6)
- `web_portal/tests/specs/deep-flows.spec.ts` — 7 Playwright-сценариев
  поверх docker-compose.test.yml: accept-rules, campaign wizard
  navigation, channel settings PATCH, placement lifecycle PATCH (adv
  → owner accept → adv pay), payouts list (owner + admin + 403),
  top-up intent, review-after-published. Три недостижимых потока
  (Telegram login widget, channel add via bot, KEP подпись в ЦС)
  скаффолдены как `test.fixme` с пояснением. (§6.2)

**Added — CI:**
- `.github/workflows/contract-check.yml` — `bash
  scripts/check_forbidden_patterns.sh` (§6.4 grep-guards) +
  `pytest tests/unit/test_contract_schemas.py` (§6.1 contract-drift
  snapshots) + `pytest tests/unit/api/` (§6.5 + §6.6 unit). Триггеры
  `pull_request`/`push` на `develop` и `main`.
- `.github/workflows/frontend.yml` — `tsc --noEmit` по матрице трёх
  фронтендов (web_portal / mini_app / landing). Для landing
  используется `npm run typecheck`, для остальных — прямой
  `npx tsc --noEmit -p tsconfig.json`. (§6.3)
- `ci.yml.disabled` и `deploy.yml` не изменены.

**Added — docs:**
- `CLAUDE.md` → два новых раздела:
  - «API Conventions (FIX_PLAN_06 §6.7)» — формализовано правило
    `screen → hook → api-module` и три-слойная защита (ESLint → grep
    → CI).
  - «Contract drift guard (FIX_PLAN_06 §6.1 Variant B)» — описание
    snapshot-тестов, workflow обновления через `UPDATE_SNAPSHOTS=1`.
- `web_portal/README.md` **(new)** — структура директории, правила
  добавления endpoint'а, команды разработки, ссылки на CI workflow'ы.

**Validation:**
- `make check-forbidden` → 7/7 ok.
- `poetry run pytest tests/unit/api/ tests/unit/test_contract_schemas.py
  tests/integration/test_payout_lifecycle.py --no-cov` → **33 passed**.
- `poetry run ruff check tests/unit/api/
  tests/integration/test_payout_lifecycle.py` → clean.
- `web_portal` tsc: `npx tsc --noEmit -p tests/tsconfig.json` → 0 errors
  для нового `deep-flows.spec.ts`.

**Known deviation from plan:**
- §6.1 Variant A (openapi-typescript codegen → `api-generated.ts`) не
  выполнен — остаётся отложенным в пользу Variant B.
- §6.5 плановое ожидание 409 на already-finalized payout в admin API
  закреплено как 400 (фактическое поведение роутера
  `admin.py:1146-1149`). Изменение маппинга на 409 — отдельная задача
  с breaking-change для frontend'ов.

### Fixed — legal-status validation hardening (2026-04-21)

Closes the two pre-launch validation gaps surfaced by the 2026-04-21 test
suite (both were marked `xfail(strict=True)` — now flipped to `passed`).

**Fixed:**
- `LegalProfileService.create_profile` / `update_profile` now raise
  `ValueError` for missing / unknown `legal_status`. Previously the
  profile was silently persisted and `legal_status_completed` was set
  to `True` because `get_required_fields` fell through to an empty
  list. (`src/core/services/legal_profile_service.py`)
- `get_required_fields(legal_status)` now raises on unknown statuses
  (was returning an empty `_EMPTY_FIELDS` dict). The API endpoint
  `GET /api/legal-profile/required-fields` surfaces this as HTTP 422.
- `fns_validation_service.validate_entity_type_match` kept its narrow
  INN-length responsibility; a new `validate_entity_documents(
  legal_status, *, ogrn, ogrnip, passport_series, passport_number)`
  enforces status-specific document rules (OGRN for `legal_entity`,
  OGRNIP for `individual_entrepreneur`, neither for `self_employed`,
  passport for `individual`). Wired into
  `POST /api/legal-profile/validate-entity` and the write path of
  `LegalProfileService`.

**Added tests:**
- 15-row parametrised `TestValidateEntityDocuments` matrix
  (`tests/unit/test_fns_validation_service.py`).
- Integration-level regressions for unknown / missing status and
  `self_employed + OGRNIP` rejection at service and API layers.

**Breaking error-shape change:**
- `GET /api/legal-profile/required-fields?legal_status=<unknown>`:
  `200 with empty fields` → `422 with {detail: "Unknown legal_status: …"}`.
- No DB / Pydantic schema changes.

### Added — test suite for legal profiles, contracts, placement↔ORD (2026-04-21)

New automated test coverage for the four flows that gate the
`ORD_PROVIDER=stub → yandex` switch: legal profiles (all 4 statuses),
contract generation, placement ↔ ORD ↔ contract wiring, and the
`YandexOrdProvider` request/response contract via `httpx.MockTransport`.

**Added:**
- `tests/unit/test_fns_validation_service.py` — INN/OGRN/KPP checksum
  coverage and matrix for `validate_entity_type_match`.
- `tests/unit/test_contract_template_map.py` — asserts every
  `(contract_type, legal_status)` → template file mapping.
- `tests/unit/test_yandex_ord_provider.py` +
  `tests/unit/test_yandex_ord_org_type_map.py` — provider methods,
  error matrix, org-type mapping helpers.
- `tests/integration/test_legal_profile_service.py` — CRUD / completeness
  / encrypted round-trip / scan upload / calculate_tax across 4 statuses.
- `tests/integration/test_api_legal_profile.py` — full
  `/api/legal-profile/*` HTTP coverage with ASGI transport.
- `tests/integration/test_contract_service.py` — owner_service
  generation across 4 templates, `_SNAPSHOT_WHITELIST` PII guard, dedup,
  signing audit trail.
- `tests/integration/test_ord_service_with_yandex_mock.py` —
  `OrdService.register_creative` end-to-end through `YandexOrdProvider`
  via `httpx.MockTransport` (all 4 endpoints).
- `tests/integration/test_placement_ord_contract_integration.py` —
  placement ↔ contract ↔ ORD wiring smoke test.
- `tests/integration/conftest.py` — testcontainers-based Postgres +
  per-test transaction rollback fixture.
- `tests/fixtures/yandex_ord/*.json` — 13 request/response fixtures.
- `docs/ord/YANDEX_ORD_API_NOTES.md` — Yandex ORD API v7 contract
  reference + sandbox-access procedure.

**Surfaced (documented as `xfail`, not fixed):**
- `LegalProfileService.create_profile` accepts unknown `legal_status`
  and silently marks the profile complete
  (`legal_profile_service.py:131-152`).
- `fns_validation_service.validate_entity_type_match` is too coarse on
  12-digit INN — does not distinguish individual / self_employed /
  individual_entrepreneur based on OGRNIP presence
  (`fns_validation_service.py:257`).

**Shared utilities:**
- `tests/conftest.py` gained `make_valid_inn10/12`, `make_valid_ogrn[ip]`,
  pre-computed `VALID_*` constants, and `legal_profile_data(status)` +
  `user_with_legal_profile(status)` factories.

**Results:** 198 passed, 4 skipped (pre-existing), 2 xfailed; ruff clean
on all new files.

### Fixed — escrow auto-release + post-deletion pipeline (2026-04-21)

Resolves a production-grade failure where placements that reached `published`
were never deleted and escrow was never released: 18× `InvalidRequestError`
and `RuntimeError('Event loop is closed')` in worker logs; Redis-dedup held
stuck placements for 1 h between retries. Root causes were three independent
bugs working together; Track A (surgical fix) closes the financial-loss
window and adds two recovery lanes.

#### Fixed
- `BillingService.release_escrow` / `refund_escrow` / `freeze_escrow` /
  `process_topup_webhook` no longer call `async with session.begin()` on a
  caller-owned session (root of `InvalidRequestError('A transaction is
  already begun on this Session')`). Transaction ownership rests with the
  outermost caller per CLAUDE.md service contract.
- `PublicationService.delete_published_post` adds a status guard — calls on
  `completed` placements are a no-op; calls on other non-`published` statuses
  log and return.
- Singleton `Bot` in `_bot_factory.get_bot()` was loop-bound and exploded on
  Celery retry (aiohttp session outlived the event loop). `ephemeral_bot()`
  async context manager creates and closes a Bot per task invocation.
- `platform_account_repo.get_for_update` now creates the singleton row if
  missing (was raising `NoResultFound` on fresh DB, matching sibling
  `get_singleton`).

#### Changed
- Replaced broken `MailingLog.status=paid` idempotency with
  `Transaction.idempotency_key` UNIQUE-index at the DB level. Keys follow a
  stable human-readable format:
  `escrow_freeze:placement={id}`,
  `escrow_release:placement={id}:{owner|platform}`,
  `refund:placement={id}:scenario={scenario}:{advertiser|owner}`.
- `BillingService` financial methods now materialise transactions via
  `session.flush()` and catch `IntegrityError` for race-past-EXISTS.
- `check_scheduled_deletions` dispatches `delete_published_post` without the
  60 s countdown (the window was the source of the double-dispatch race).
- `check_published_posts_health` now audits both active and expired posts
  (dropped `scheduled_delete_at > now` filter, which hid stuck placements).

#### Added
- `Transaction.idempotency_key` column: `String(128)` NULLable + UNIQUE index.
  Pre-production schema edit to `0001_initial_schema.py` per CLAUDE.md §
  Migration Strategy.
- `DEDUP_TTL['delete_published_post'] = 180` + task-level dedup gate blocks
  double-dispatch on two pool workers (task_acks_late race).
- `check_escrow_stuck` group C: `status=published` + `scheduled_delete_at <
  now - 1 h` + `message_id set` → auto re-dispatch `delete_published_post`
  and admin alert. Closes the recovery loop for any future deletion failure.
- `tasks/_bot_factory.ephemeral_bot()` async context manager.
- `tests/test_billing_service_idempotency.py` fully rewritten: 25 tests
  covering the new contract.

#### Migration Notes
- DB reset **not** required — column added in place via `ALTER TABLE
  transactions ADD COLUMN idempotency_key VARCHAR(128)` plus `CREATE UNIQUE
  INDEX ix_transactions_idempotency_key ON transactions (idempotency_key)`.
  Existing rows keep `idempotency_key = NULL`; Postgres UNIQUE treats NULL
  as distinct.
- `alembic -c alembic.ini check` confirms model / DB sync: "No new upgrade
  operations detected."

#### Verified
- Placement #1 (stuck since 2026-04-20) closed end-to-end on one attempt, no
  retries, no `InvalidRequestError`, no `Event loop is closed`.
- Idempotency confirmed: second dispatch of `delete_published_post` for the
  same placement is a status-guard no-op; transaction count and `earned_rub`
  unchanged.

#### Follow-up (Track B, separate sprint)
- `PlacementStatus.deleting` as status-machine lock, replacing Redis-dedup.
- Collapse `check_scheduled_deletions` + `delete_published_post` into one
  inline Beat task.
- Unify transactional contract across all services.
- Prometheus / Grafana metrics for `placement_stuck_seconds` and deletion
  failure counters.

See `reports/docs-architect/discovery/CHANGES_2026-04-21_fix-escrow-auto-release.md`
and `/root/.claude/plans/lexical-swinging-pony.md` for the full plan.

### Changed — web-portal button system unified (2026-04-21)

#### Changed
- `web_portal/src/shared/ui/Button.tsx` rewritten with a real size scale:
  `sm = 32 px`, `md = 40 px`, `lg = 48 px` (was `sm = md = 44 px`, `lg = 52 px`).
  Softened `secondary` variant (elevated background + transparent border — was
  hard `border-border-active` rim). Added `focus-visible:ring` outline, `aria-label`
  and `aria-busy` props. Public API is **backwards-compatible**.
- All `ScreenHeader.action` buttons across advertiser / owner / admin / common /
  shared screens now use `size="sm"`. Back/nav buttons shifted to `variant="ghost"`;
  utility refresh buttons collapsed to icon-only 32 × 32.
- Cabinet header ("Отчёт" + "Создать кампанию"), Plans ("Пополнить баланс"),
  MyCampaigns and OwnChannels primary CTAs tightened to `size="sm"`.
- `TransactionHistory` "Экспорт CSV" + "Экспорт PDF" pair consolidated into a
  single `DropdownMenu` trigger.

#### Added
- `web_portal/src/shared/ui/DropdownMenu.tsx` — new generic menu primitive
  (outside-click + Esc close, keyboard focus on open, ARIA menu semantics).
  Exported from `@shared/ui`.

#### Fixed (pre-existing lint errors resolved during hardening)
- `Sparkline.tsx` — `Math.random` ID generation → `useId()`.
- `useBillingQueries.ts` — `Date.now()` read moved out of render into effect.
- `BalanceHero.tsx` — stabilized `history?.items` for React Compiler memo inference.
- `MyDisputes.tsx` — wrapped `data?.items ?? []` in `useMemo`.

Eslint: 0 errors (was 3), 6 pre-existing warnings unchanged.

#### Visual regression (action required)
- Playwright `visual.spec.ts` baselines need regeneration:
  `make test-e2e-visual-update`. Every screen with a `ScreenHeader` action has
  a new — intentional — button style.

#### Fixed — admin "Настройки" sidebar link (bundled)
- Removed the public "Настройки" entry from sidebar — it was visible to all
  roles and pointed to a placeholder stub, masking the real platform
  legal-profile screen.
- Added "Реквизиты платформы" → `/admin/settings` (admin-only) which hosts the
  existing `AdminPlatformSettings` form that feeds `legal_name`/`inn`/`kpp`/
  `ogrn`/bank data into contract generation.
- Removed the dead `/settings` route and unused `PlaceholderScreen` component.

#### Not changed
- No API / FSM / DB contract changes. No new migrations. No Celery changes.
- `Button` API is source-compatible; no call-site migration beyond the
  deliberate size/variant updates listed above.

Detail report: [reports/docs-architect/discovery/CHANGES_2026-04-21_web-portal-button-unification.md](reports/docs-architect/discovery/CHANGES_2026-04-21_web-portal-button-unification.md).

### Fixed — web-portal top-up returned 404 on yookassa.ru (2026-04-21)

- `BillingService.create_payment` (`src/core/services/billing_service.py`) fabricated a
  local UUID and a synthetic URL `https://yookassa.ru/payment/{uuid}`, which always
  returned "Ошибка 404" because no payment was ever registered with YooKassa. The method
  now actually calls `yookassa.Payment.create` (wrapped in `asyncio.to_thread`) and
  stores the real `payment.id` and `payment.confirmation.confirmation_url` on the
  `YookassaPayment` row.
- Guards: raises `RuntimeError` if YooKassa credentials are unset or no confirmation URL
  is returned; propagates `yookassa.domain.exceptions.ApiError`.

#### Public contract change
- `POST /api/billing/topup` response schema unchanged; `payment_url` now holds a real
  YooKassa confirmation URL (e.g. `https://yoomoney.ru/checkout/payments/v2/contract?…`)
  instead of a 404-returning string.
- `yookassa_payments.payment_id` now holds the YooKassa-issued ID (previously a locally
  generated UUID), enabling reconciliation against the YooKassa dashboard. No schema
  change.

Detail report: [reports/docs-architect/discovery/CHANGES_2026-04-21_fix-yookassa-topup-404.md](reports/docs-architect/discovery/CHANGES_2026-04-21_fix-yookassa-topup-404.md).

### Docs — re-audit & drift fix (2026-04-21)

#### Changed
- `README.md` rewritten against verified counts: 27 routers · 131 endpoints · 35 services · 31 models · 26 repos · 22 handler files · 11 FSM groups (52 states) · 12 Celery files / 66 tasks / 9 queues / 18 periodic · Mini App 55 screens · Web Portal 66 screens / 126 Playwright specs · Landing page.
- `docs/AAA-01…AAA-10` synced: headers re-dated, metric tables rebuilt, inventories regenerated from filesystem. AAA-07 gained a dedicated Landing Page section.
- `docs/AAA-10_DISCREPANCY_REPORT.md` — added 2026-04-21 drift snapshot (earlier doc/CLAUDE.md claims vs reality).

#### Not changed
- `docs/AAA-11_PRODUCTION_FIX_PLAN.md`, `docs/AAA-12_CONTAINER_STARTUP_DEEP_DIVE.md` — point-in-time artefacts (S-29 / post-rebuild) intentionally left intact.
- No code, schema, API or Celery routing changes.

Detail report: [reports/docs-architect/discovery/CHANGES_2026-04-21_docs-sync-deep-dive.md](reports/docs-architect/discovery/CHANGES_2026-04-21_docs-sync-deep-dive.md).

### Disputes flow — deep audit + hardening (2026-04-21)

#### Fixed
- **Admin "Все" filter was empty** — `GET /disputes/admin/disputes`
  default `status="open"` в роутере `src/api/routers/disputes.py`;
  фронт при «Все» не передавал параметр → бэк фильтровал только
  open. Default переведён на `"all"`.
- **Статус-лейблы расходились** между экранами (MyDisputes фильтр
  «Ожидание» vs бейдж «Ответ владельца»; владелец читал про себя в
  3-ем лице). Введён единый источник —
  `web_portal/src/lib/disputeLabels.ts` + ролево-зависимые
  формулировки `getRoleAwareStatusLabel(status, role)`.
- **Shared `/disputes/:id` показывал форму «Ваш ответ» всем** —
  рекламодатель мог кликнуть Submit, бэк возвращал 403. Форма
  удалена; владельцу показывается CTA со ссылкой на
  `/own/disputes/:id`.
- **`useMyDisputeByPlacement`** делал full-scan последних 100
  disputes клиентски. Заменён на backend endpoint
  `GET /disputes/by-placement/{placement_request_id}`.
- `DisputeDetail` back-кнопка вела в `/disputes` (маршрут не
  существует) → `navigate(-1)` + лейбл «Назад».

#### Added
- `GET /disputes/by-placement/{placement_request_id}` — возвращает
  `DisputeResponse | null`; авторизация через проверку роли в
  размещении.

#### Security / Data integrity
- `POST /disputes` — добавлены серверные инварианты:
  создавать диспут может только рекламодатель размещения;
  размещение должно быть в статусе `published`; окно открытия —
  48 часов с момента `published_at`. Раньше проверка была только
  на фронте.

#### Deferred (ticket needed)
- Telegram-уведомления на события диспута
  (`notify_dispute_created/replied/resolved`).
- Celery auto-escalation для stale `owner_explained` диспутов (72h
  через поле `expires_at`).
- Унификация параллельных enum'ов `DisputeStatus`/`DisputeResolution`
  между `api.schemas.dispute` и `db.models.dispute`.

### Admin dispute filter + campaign-filter unification (2026-04-21)

#### Fixed
- `AdminDisputesList` — неверный ключ фильтра `owner_reply` в UI (бэк
  принимает `open|owner_explained|resolved|all`). Из-за этого клик по
  «Ответ владельца» возвращал 400 и дисп исчезал, а дефолтный
  `status=open` прятал записи `owner_explained` (ожидающие решения
  админа). Ключ переименован в `owner_explained`, дефолтный фильтр
  переведён на `all`.
- `OwnRequests` vs `MyCampaigns` — `status=published` классифицировался
  у рекламодателя как «Завершена», а у владельца канала как
  «Активные». Добавлен отдельный фильтр «Завершённые» для владельца,
  `ACTIVE_STATUSES` у него сужены до `['escrow']`. Обе стороны теперь
  трактуют `published` как завершённое размещение.

### Portal Disputes restructure (2026-04-21)

#### Fixed
- `AdminDisputesList` — клик по записи открывал общий
  `/disputes/:id` (shared `DisputeDetail` c textarea «Ваш ответ»), из-за
  чего админ мог отправить `owner_explanation` от имени владельца.
  Теперь список ведёт на `/admin/disputes/:id` (`AdminDisputeDetail`,
  admin-only resolve-UI).
- Все `/admin/**` маршруты теперь под `AdminGuard`: ранее только
  `accounting`, `tax-summary`, `settings` были защищены, остальные лишь
  скрывались в сайдбаре для не-админов.

#### Added
- `AdminDisputeDetail` — в header добавлена кнопка «Перейти к кампании
  #N» → `/own/requests/:id`, чтобы админ мог изучить контекст
  оспариваемого размещения.
- `OwnRequestDetail` — при `has_dispute=true` отображается карточка
  «Спор по этой заявке» с комментарием рекламодателя и кнопкой
  «Ответить на спор» / «Открыть детали спора».
- `CampaignPublished` (рекламодатель) — при существующем споре
  отображается карточка статуса (open / owner_explained / resolved /
  closed) и ответ владельца; кнопка «Открыть детали спора» ведёт на
  `/disputes/:disputeId`.
- Новый хук `useMyDisputeByPlacement(placementId)` —
  клиентский lookup дисп-записи по `placement_request_id` через
  существующий `GET /disputes`.

#### Changed
- Sidebar — удалён пункт «Мои споры» из группы «Реклама». Раздел
  «Споры» остаётся только у админа (`adminOnly: true`). Маршруты
  `/adv/disputes` и `/own/disputes` сохраняются как deep-links.

### Portal UI fixes: Legal Profile, Cabinet, Sidebar (2026-04-21)

#### Fixed
- `LegalProfileSetup` — карточка «Профиль заполнен» теперь строится
  динамически по `requiredFields` из бэкенда и флагам
  `showBank`/`showPassport`: для Физлица/Самозанятого показываются
  паспортные данные и ЮMoney-кошелёк, для ИП/ООО — КПП/ОГРН/банковские
  реквизиты. Процент заполнения считается только по релевантным полям.
- `LegalProfileSetup` — StepIndicator считает шаг по фактической
  готовности секций: этап «Банк»/«Паспорт» загорается после заполнения
  основных реквизитов; третий лейбл адаптируется под тип лица.
- `ProfileCompleteness` (Кабинет) — шаг «Юридический профиль»
  использует `legal.is_complete` (бэкенд-флаг
  `user.legal_status_completed`) вместо простого наличия
  `legal_status`; больше не помечается «выполненным» при частично
  заполненном профиле.
- `Sidebar` — `<aside>` получил `h-dvh min-h-0`, из-за чего внутренний
  `<nav className="flex-1 overflow-y-auto">` снова корректно
  прокручивается. Пункт «Администрирование» был скрыт за нижним краем
  экрана.

#### Removed
- `LegalProfileSetup` — удалена кнопка «Проверить ИНН» и блок
  «Результат проверки ФНС» (включая использование
  `useValidateEntity`). Валидация ИНН по контрольной сумме остаётся
  автоматической на `onBlur` через `useValidateInn`
  (`POST /legal-profile/validate-inn`).
- `LegalProfileSetup` — удалена кнопка «Шаблон заполнения» из
  `ScreenHeader.action` (не имела обработчика).

### Phase 8.1 iter 4: Mobile action-wrap fix (2026-04-20)

#### Fixed
- `MyCampaigns`, `OwnChannels`, `TransactionHistory` — the 2-button
  action slot clipped off the right edge at 320px because an inner
  `<div className="flex gap-2">` around the buttons blocked
  `ScreenHeader`'s outer `flex-wrap`. Replaced the wrapper with a
  fragment; the second button now wraps to its own line on mobile and
  keeps the original horizontal layout on ≥sm. No change to
  `ScreenHeader.tsx` itself — its contract was already right.
- Audited all 20+ ScreenHeader consumers against the freshly-captured
  mobile-webkit baselines; no other screens exhibit the issue.

### Phase 8.1 iter 3: Visual regression baseline (2026-04-20)

#### Added
- `web_portal/tests/specs/visual.spec.ts` — 35 routes × 3 viewports =
  105 full-page screenshot tests with committed baselines under
  `web_portal/tests/visual-snapshots/`.
- `make test-e2e-visual-update` — refreshes baselines in one shot.
- `playwright.config.ts`: `toHaveScreenshot` thresholds
  (`threshold: 0.2`, `maxDiffPixelRatio: 0.005`).

### Phase 8.1 iter 2: API contract test suite (2026-04-20)

#### Added
- `tests/e2e_api/` — pytest + httpx suite that runs inside the Docker
  test stack alongside Playwright (`docker-compose.test.yml` gains
  `api-contract` service). Asserts auth boundaries, query-param
  coercion, 401/403/200/422 contracts across 17 representative routes.
- `docker/Dockerfile.api-contract` — mirrors `Dockerfile.api` but
  installs Poetry dev-group (pytest, pytest-asyncio). Used only by the
  test stack; never in prod.
- `make test-e2e-api` — standalone target; `make test-e2e` now runs API
  contract + Playwright UI back-to-back in one stack bring-up.

#### Fixed
- `/api/analytics/summary`, `/activity`, `/cashflow` — all crashed with
  500 in any environment without `MISTRAL_API_KEY`. Root cause:
  `AnalyticsService.__init__` eagerly instantiated `MistralAIService()`.
  Fixed with a `@property`-backed lazy factory matching the module-level
  pattern from iter 1. Analytics queries that don't need AI (i.e. nearly
  all of them) no longer build a Mistral client at all.

### Phase 8.1: E2E test harness + production-readiness fixes (2026-04-20)

#### Added
- Dockerised Playwright harness: `docker-compose.test.yml` with isolated
  postgres-test / redis-test / seed-test / api-test / nginx-test / playwright
  services. Runs against a production-like runtime, not stubbed API. New
  Makefile targets: `test-e2e`, `test-e2e-up`, `test-e2e-down`, `test-e2e-logs`.
- `scripts/e2e/seed_e2e.py` — idempotent fixture loader (3 roles, channel,
  placements).
- `web_portal/tests/` — full Playwright suite: 35 routes × 3 viewports,
  asserts ≤1 breadcrumbs, no horizontal overflow, no external sprite refs,
  no uncaught client errors, axe-core baseline.

#### Added — API (testing env only)
- `POST /api/auth/e2e-login` — test-only JWT issuance by `telegram_id`,
  gated on `settings.environment == "testing"` at router mount time.
  Router is not imported in any other environment, so the path returns a
  plain 404. Never an attack surface in staging/prod.

#### Changed — Placements API
- `GET /api/placements/?status=…` now accepts semantic aliases `active`
  (pending_owner + counter_offer + pending_payment + escrow), `completed`
  (published), `cancelled` (cancelled + refunded + failed + failed_permissions)
  in addition to concrete `PlacementStatus` values. Unknown values return
  HTTP 400 with the valid list — previously 500'd with
  `ValueError: 'active' is not a valid PlacementStatus` on a call the
  frontend makes from every advertiser route.

#### Fixed
- `MistralAIService` module-level instantiation crashed any environment
  without `MISTRAL_API_KEY` at *import* time (tests, CI, smoke). Replaced
  the eager `mistral_ai_service = MistralAIService()` (plus
  `ai_service` / `admin_ai_service` aliases) with a module-level
  `__getattr__` that constructs on first access. Consumer imports
  unchanged; missing-key `RuntimeError` still raises — just at call-time.

#### Fixed — minor
- `src/api/main.py`: unused-param underscores (`lifespan`,
  `_scrub_pii`, `rekharbor_error_handler`), and ORD shutdown now guards
  the optional `close()` via `inspect.isawaitable` — no pyright narrowing
  error, same runtime behaviour.

### S-47: UI redesign per Design System v2 — EmptyState icon (2026-04-20)

#### Fixed
- `EmptyState`'s `icon` prop was typed as `string` with an emoji
  default (`'🌊'`) and rendered as literal text at `text-5xl`. Every
  caller already passed a rh-sprite icon name (`icon="campaign"`,
  `"channels"`, `"disputes"`, `"requests"`, `"payouts"`, `"contract"`,
  `"feedback"`, `"users"`, `"error"`), so on every empty list the
  literal word «campaign»/«channels»/etc. was shown above the title —
  visible duplication. Switched the prop to `icon?: IconName` rendered
  via `<Icon>` inside a 56×56 harbor-elevated tile, matching the
  design-system icon-bubble pattern used elsewhere. Emoji default
  removed; TS now enforces that only valid sprite names compile.

### S-47: UI redesign per Design System v2 — Mobile layout (2026-04-20)

#### Fixed
- `ScreenHeader` stacked title above action on mobile. Action's
  `flex-shrink-0` was overflowing the viewport on narrow screens
  (iPhone SE, 320–375px) when screens passed two buttons in the
  slot. Outer layout is now `flex-col` until `sm`, then switches to
  the original horizontal layout; title scales to `text-[22px]` on
  mobile and gains `break-words`.
- `MyCampaigns` list row was a fixed five-column flex strip that
  overflowed below ~400px. On mobile the status pill and the
  separate price column are now hidden; price reappears inline in
  the meta line next to the date (`justify-between`). Description
  `max-w-[420px]` clamp is `sm+`-only. Desktop layout unchanged.
- Other list-heavy screens (`OwnChannels`, `OwnRequests`,
  `TransactionHistory`, `AdminUsersList`, …) retain their original
  rows but already benefit from the ScreenHeader stack fix; full
  per-screen row-responsiveness is tracked as a Phase 8.1 follow-up.
- See `reports/docs-architect/discovery/CHANGES_2026-04-20_s47-mobile-layout-my-campaigns.md`.

### S-47: UI redesign per Design System v2 — Deduplicate breadcrumbs (2026-04-20)

#### Fixed
- Breadcrumbs rendered twice on every screen — once in the Topbar
  (introduced during the current pre-merge pass) and once inside the
  page body via `ScreenHeader`'s `crumbs` prop. Chose the Topbar chain
  as the single source (it supports dynamic-route normalisation,
  mobile collapse, and clickable parent links) and removed the
  in-screen duplicate across 50 screens plus `ScreenHeader`,
  `TaxSummaryBase`, and the dead `breadcrumbs` slice on
  `portalUiStore`. See
  `reports/docs-architect/discovery/CHANGES_2026-04-20_s47-dedupe-breadcrumbs.md`.

### S-47: UI redesign per Design System v2 — Cashflow query validation (2026-04-20)

#### Fixed
- `GET /api/analytics/cashflow` returned 422 for every request because
  the `days` query parameter was declared as
  `Annotated[Literal[7, 30, 90], Query(...)]`, and Pydantic 2 in strict
  mode does not coerce the raw query-string `"30"` to the integer
  literal `30`. The Cabinet's «Финансовая активность» widget
  (`PerformanceChart`) therefore always fell into its `isError` branch.
- Replaced the `Literal` with an `IntEnum` (`CashflowPeriod`), which is
  FastAPI's recommended pattern for enum-like integer query params and
  which coerces query strings natively. Request/response shapes and the
  TS client contract are unchanged; the TS side continues to send
  `?days=7|30|90`. See
  `reports/docs-architect/discovery/CHANGES_2026-04-20_s47-cashflow-validation.md`.

### S-47: UI redesign per Design System v2 — Mobile fixes (2026-04-20)

Hotfix after Phase 7 mobile visual review, before Phase 8 merge. Two
production-blocking defects on https://portal.rekharbor.ru/. See
`reports/docs-architect/discovery/CHANGES_2026-04-20_s47-mobile-fixes.md`.

#### Fixed — Icon sprite on mobile (two-pass fix)
- **Pass 1 — external `<use>` references.** Icons were blank on iOS
  Safari / some mobile Chrome builds due to external-file
  `<use href="/icons/rh-sprite.svg#…">` references, which those engines
  do not resolve reliably. The previous runtime `IconSpriteLoader` fix
  could not help already-mounted `<Icon>`s. Switched to **build-time
  inlining**: a Vite `transformIndexHtml` plugin
  (`web_portal/vite-plugins/inline-sprite.ts`) injects the sprite at
  the top of `<body>` in `index.html`; every `<Icon>` now references
  a local fragment (`#rh-foo`). `Icon.tsx` simplified;
  `IconSpriteLoader.tsx` deleted along with its export and its
  `PortalShell` mount point.
- **Pass 2 — shadow-tree stylesheet boundary.** Even with inlined
  symbols, iOS Safari rendered icons invisible because `<use>` creates
  a shadow tree and iOS Safari does not apply descendant selectors
  (`.rh-icon .rh-stroke`) from the outer document across that boundary.
  Fix: the plugin now **colocates the styling inside the sprite's
  `<defs>`** as a `<style>` block with the `.rh-stroke` / `.rh-fill`
  rules; styles declared inside an SVG travel with the shadow tree a
  `<use>` clones from it. `currentColor` and `--rh-stroke-w` continue
  to flow in via normal CSS inheritance.

#### Fixed — Breadcrumbs
- Detail pages (`/own/channels/:id`, `/adv/campaigns/:id/payment`,
  `/admin/users/:id`, `/disputes/:id`, `/contracts/:id`, …) fell back to
  «Главная» because `BREADCRUMB_MAP` was keyed by exact `location.pathname`.
- `Topbar.tsx` now normalises pathname (`/\d+/` → `/:id`) before lookup,
  and the map was extended with every dynamic route mounted in `App.tsx`.
- On narrow viewports the nav is `min-w-0 flex-1 overflow-hidden`, middle
  crumbs in 3+ chains are `hidden md:flex` (so mobile shows first › last,
  desktop shows the full chain), each crumb is `truncate`.

#### Not changed
- Sprite contents (`public/icons/rh-sprite.svg`) — untouched.
- Icon public API (`<Icon name … size … variant …/>`) — untouched.
- Route definitions in `App.tsx` — untouched.
- Backend, DB, Celery, business logic, FSM.

### S-47: UI redesign per Design System v2 — Phase 7 (2026-04-20)

Accessibility, performance, contract-sync, and routing pass before merge
into `develop`. See
`reports/docs-architect/discovery/CHANGES_2026-04-20_s47-phase7-a11y-perf.md`.

#### Added
- `/dev/icons` gallery (behind `import.meta.env.DEV` guard) — new
  `src/screens/dev/DevIcons.tsx` lists all 132 sprite icons with
  name-filter, outline/fill toggle, size slider, and click-to-copy.
  Stripped from production bundle by Vite tree-shake.

#### Changed — Accessibility (§7.18)
- `Tabs` primitive — `role="tablist"`, `role="tab"`, `aria-selected`, and
  a roving `tabIndex` so keyboard users focus the active tab.
- `RecentActivity` — same ARIA treatment on its inline tab switcher.
- `Modal` — `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
  (via `useId`) wired to the title heading; close ✕ button gains
  `aria-label="Закрыть"`; the former `div[role=button]` backdrop became a
  plain `<button>`.
- `Topbar` — search stub `aria-label`; bell `aria-label` now reports the
  unread count when the red dot is visible; dot marked `aria-hidden`.

#### Changed — Performance (§7.19)
- `PerformanceChart` wrapped in `React.memo` so Cabinet re-renders don't
  re-walk its ~200-line SVG body.

#### Verified (no code change)
- `:focus-visible` and `@media (prefers-reduced-motion: reduce)` were
  already globalised in `src/styles/globals.css` — confirmed to apply to
  the `pulse-ring` animation in `TopUpConfirm` and to Framer Motion.
- Icon tree-shaking — non-issue: `rh-sprite.svg` (37 KB) is a static file
  fetched once by `IconSpriteLoader`, not inlined into JS chunks.
- `lucide-react` — 0 imports remain across `web_portal/src/` (§7.23
  closed out as N/A).
- Cabinet widget endpoints (`billing/frozen`, `analytics/cashflow`,
  `users/me/attention`, `channels/recommended`) — backend Pydantic
  schemas vs TS clients and React Query hooks match field-for-field
  (§7.21).
- Routing audit — all 60+ screens mounted in `App.tsx`; no orphans.

#### Bundle baseline (production)
- Δ from Phase 6: +16 B raw / +0 KB gzip (React.memo wrapper only).
- Largest lazy chunk: `BarChart-*.js` at 101.89 KB gz (Recharts,
  loaded only on `/adv/analytics` and `/own/analytics`).
- Entry `index-*.js`: 58.40 KB gz.

#### Deferred
- **§7.20 Storybook** — not installed; not blocking. `/dev/icons`
  covers the most-requested primitives-gallery need. Will be a
  follow-up ticket in the next sprint.
- Chrome DevTools contrast audit on secondary/tertiary text — requires
  a browser; listed in the pre-merge checklist.
- Lighthouse Performance / Accessibility run — same reason; scores to
  be added to the merge PR description.

#### Not changed (Phase 7)
- Backend, DB, Celery, business logic, API routes, FSM transitions,
  query keys.
- DS v2 tokens (`globals.css`), sprite contents (`public/icons/rh-sprite.svg`).

### S-47: UI redesign per Design System v2 — Phase 6 (2026-04-20)

#### Changed — 30 design-from-tokens screens (§7.17)

Every screen in this section was redesigned from DS v2 tokens and primitives
(§§7.1–7.4) without a handoff mockup, following the patterns established in
§§7.5–7.12 and the pixel-perfect handoff screens (§7.5a). Business logic,
query keys, and routes are unchanged.

- **Advertiser (14 screens):** `MyCampaigns`, `CampaignCategory/Channels/
  Format/Text/Arbitration/Waiting/Published`, `CampaignPayment`,
  `CampaignCounterOffer`, `CampaignVideo`, `OrdStatus`,
  `AdvertiserFrameworkContract`, `AdvAnalytics`. Wizard creation steps now
  share `screens/advertiser/campaign/_shell.tsx` — a single
  `CampaignWizardShell` (ScreenHeader + StepIndicator + sticky footer).
  `Waiting` / `Published` are rebuilt as post-creation status screens (no
  wizard indicator). `OrdStatus` is wired to `useOrdStatus`/`useRegisterOrd`
  with a Timeline of 4 ОРД stages.
- **Owner (10 screens):** `OwnChannels/Detail/Add/Settings`,
  `OwnRequests/Detail`, `OwnPayouts`, `OwnPayoutRequest`, `OwnAnalytics`,
  `DisputeResponse`. `OwnChannels` drops the table/MobileCard duplication for
  a single responsive channel-card grid; `OwnPayouts` gains a cooldown
  countdown hero.
- **Shared + common (6 screens):** `MyDisputes`, `OpenDispute`,
  `DisputeDetail`, `LegalProfilePrompt`, `LegalProfileView`, `ContractDetail`.
- **Admin (11 screens + shared base):** `AdminDashboard`, `AdminUsersList`,
  `AdminUserDetail`, `AdminDisputesList`, `AdminDisputeDetail`,
  `AdminFeedbackList`, `AdminFeedbackDetail`, `AdminPayouts`,
  `AdminAccounting`, `AdminTaxSummary`, `AdminPlatformSettings`, and
  `components/admin/TaxSummaryBase` (ScreenHeader + KpiCells + subtitle /
  crumbs props).

#### Removed / replaced
- All legacy emoji labels inside interactive surfaces (🔵 / ❌ / 📊 / ➕ / 🔄
  / ✅ etc.) replaced with `<Icon name={...} />` from the DS v2 sprite.
- Dual desktop-table + MobileCard layouts on list screens reduced to a single
  responsive card/row grid per screen.
- Ad-hoc `Card title="..."` wrappers replaced with DS v2 SectionCards
  (bordered header strip + Icon + display font).

#### Behaviour changes
- `AdminDisputesList` rows are fully clickable — the former nested "Решить"
  button became a visual span; clicking anywhere on the row navigates to
  `/disputes/:id`.

#### Not changed
- Business logic, API routes, FSM transitions, query keys, mutation payloads.
- Wizard navigation order (`/adv/campaigns/new/category → channels → format →
  text → terms`) and post-creation status routes.
- Alembic migrations, Celery queues, backend services.

### S-47: UI redesign per Design System v2 — Phase 5 (2026-04-20)

#### Added
- **New primitives (§7.4.1):**
  - `web_portal/src/shared/ui/ScreenHeader.tsx` — breadcrumb + title +
    subtitle + action-slot pattern used by all 13 handoff screens.
  - `web_portal/src/shared/ui/LinkButton.tsx` — inline text-link button
    (accent/secondary/danger tones, optional underline).
  - `Button` extended with `iconLeft` / `iconRight: IconName` props,
    rendered via the DS v2 `<Icon>` sprite.
  - `StepIndicator` rewritten to numbered-pill + per-step inline labels
    (new semantics: `labels[i]` = label for step `i+1`).

#### Changed — 13 handoff screens ported pixel-perfect
- **Financial (Phase 5.1–5.4):**
  - `web_portal/src/screens/shared/Plans.tsx` — 4 plan-tiles with
    featured Pro + ribbon, current-plan highlight, low-balance warning,
    comparison table, 3-cell FAQ.
  - `web_portal/src/screens/shared/TopUp.tsx` — chip-amounts + custom
    input with ruble icon, 3-method payment selector (card/СБП/YooMoney),
    sticky summary card with "к оплате" total, autotopup toggle, balance
    tile with wallet glyph.
  - `web_portal/src/screens/shared/TopUpConfirm.tsx` — 4 live-states
    (pending with indet progress + counter, succeeded with success-glyph
    pulse-ring, canceled, timeout), details breakdown card, state-aware
    action row.
  - `web_portal/src/screens/common/TransactionHistory.tsx` — 4 summary
    tiles (income/expense/netto/balance), search + 4-period toggle +
    6-type filter-chips, day-grouped timeline, status-pills + mono
    signed amounts, pagination footer.
- **Reputation / acts / referral (Phase 5.5–5.7):**
  - `web_portal/src/screens/common/ReputationHistory.tsx` — 2 score-cards
    (Advertiser + Owner) with tier-progress sparkline, role/tone filters,
    tone-colored event rows with delta-pill and before→after progress.
  - `web_portal/src/screens/common/MyActsScreen.tsx` — pending-signature
    banner, 4 summary tiles, type+status filter-bar with bulk-action
    panel, table with checkbox + type-glyph + inline-actions.
  - `web_portal/src/screens/common/Referral.tsx` — gradient hero with
    code/link copy and 5 share-channels, 4-level progress
    (Bronze→Platinum), 4 stat-tiles, referrals list with mono-avatars,
    "how it works" sidebar.
- **Help / feedback / legal (Phase 5.8–5.13):**
  - `web_portal/src/screens/common/Help.tsx` — hero-search with ⌘K hint
    + 6 category-chips, 2-column FAQ accordion with full-text filter +
    helpful/not-helpful feedback, gradient support CTA + channels +
    popular docs sidebar.
  - `web_portal/src/screens/common/Feedback.tsx` — topic chips (5 tone-
    colored), priority tiles, textarea with char-counter + quick topics,
    email-for-response, secure-footer, success-state with ticket #,
    online-support + "what to write" sidebars.
  - `web_portal/src/screens/common/LegalProfileSetup.tsx` — 4 legal-type
    tiles (self/IP/OOO/individual), StepIndicator 1..4, 2-column layout
    with main form + bank + passport cards + right rail with SVG
    completeness ring. Preserves FNS validation, required-fields, INN
    checksum, passport logic.
  - `web_portal/src/screens/common/ContractList.tsx` — 4 summary tiles,
    filter-bar with 5 kind-chips + "active only" toggle, table with
    kind-glyph + status-pills + inline actions, rules viewer modal.
  - `web_portal/src/screens/common/DocumentUpload.tsx` — gradient hero
    with SVG progress ring, document type + passport-page selectors,
    drag-n-drop with image preview, full processing view (quality
    score, OCR confidence, extracted fields, validation results),
    requirements sidebar with encryption note.
  - `web_portal/src/screens/common/AcceptRules.tsx` — sticky TOC sidebar +
    read-progress tracker, rules-viewer with scroll-to-bottom detection,
    3 agreement checkboxes, sign-action footer with disabled-state hint.

#### Migration Notes
- 6 existing `StepIndicator` callers updated to the new labels-per-step
  format (`CampaignCategory`, `CampaignChannels`, `CampaignFormat`,
  `CampaignText`, `CampaignVideo`, `CampaignArbitration`, `TopUpConfirm`).
  Previously the labels array used off-by-one indexing; now `labels[0]`
  corresponds to step 1, `labels[1]` to step 2, etc.
- No backend / API change in Phase 5.
- Docker rebuild required: `docker compose up -d --build nginx api`.

### S-47: UI redesign per Design System v2 — Phases 1–4 (2026-04-20)

#### Added
- **Icon sprite system (Phase 1, §§7.1–7.2):**
  - `web_portal/public/icons/rh-sprite.svg` (132 symbols, 10 groups, stroke 1.5)
  - `web_portal/src/shared/ui/{Icon,IconSpriteLoader,icon-names}.{tsx,ts}` —
    typed `<Icon name>` component with literal-union `IconName`, and one-time
    inline sprite loader mounted inside `PortalShell`.
  - `.rh-stroke` / `.rh-fill` component rules and `ui-spin` / `ui-skeleton`
    keyframes in `web_portal/src/styles/globals.css`.
  - `Sparkline` shared primitive.
- **Backend Cabinet-widget endpoints (Phase 3, §7.21):**
  - `GET /api/billing/frozen` — escrow+pending_payment summary.
  - `GET /api/analytics/cashflow?days=7|30|90` — daily income/expense points.
  - `GET /api/users/me/attention` — danger>warning>info>success feed.
  - `GET /api/channels/recommended` — topic-matched top-ER list with fallback.
  - New service `src/core/services/user_attention_service.py`.
  - New repo method `PlacementRequestRepository.get_frozen_for_advertiser`.
  - All four respect FastAPI static-path-before-`/{int_id}` ordering
    (see `project_fastapi_route_ordering.md`).
- **TS clients + React Query hooks** for the four endpoints
  (`useFrozenBalance`, `useCashflow(days)`, `useAttentionFeed`,
  `useRecommendedChannels`).
- **Cabinet redesign (Phase 4, §§7.5–7.12):**
  - 7 new widgets under `web_portal/src/screens/common/cabinet/`:
    `BalanceHero`, `PerformanceChart`, `QuickActions`, `NotificationsCard`,
    `ProfileCompleteness`, `RecommendedChannels`, `RecentActivity`.
  - Cabinet shell rewritten with DS v2 greeting + 1.6fr/1fr grid + footer
    waterline; uses all new backend endpoints via hooks.
- **PortalShell v2 (Phase 2, §7.3):**
  - Split into `Sidebar.tsx` + `Topbar.tsx` + thin `PortalShell.tsx`.
  - Sidebar: 6 grouped nav sections, count chips bound to live hooks,
    gradient-anchor logo, waterline divider, collapsed-mode.
  - Topbar: sidebar toggle, breadcrumb map (~30 routes), search-stub
    button with ⌘K visual, bell with red-dot from attention feed.

#### Changed
- `web_portal/src/components/layout/PortalShell.tsx` — now composition-only.
- `web_portal/src/screens/common/Cabinet.tsx` — complete rewrite under DS v2.

#### Deferred (next sessions)
- Phase 5 — 13 handoff-designed screens (Plans, TopUp, TopUpConfirm,
  TransactionHistory, ReputationHistory, MyActs, Referral, Help, Feedback,
  LegalProfileSetup, ContractList, DocumentUpload, AcceptRules).
- Phase 6 — ~25 design-from-tokens screens (advertiser wizard, owner,
  admin).
- Phase 7 — Role switcher, density toggle, a11y audit, perf-check.
- Phase 8 — `lucide-react` → `<Icon>` migration lock (ESLint error-level).
- §7.21.5: Redis 60s TTL cache for `/users/me/attention` with write-action
  invalidation hooks.

#### Migration Notes
- No Alembic migration — all four new endpoints use existing tables.
- Frontend `IconSpriteLoader` fetches `/icons/rh-sprite.svg` once at shell
  mount; after that `<use href="#rh-foo"/>` resolves inline, no per-icon
  fetches.

### S-48: Grep-guards for regression patterns (2026-04-20)

#### Added
- **`scripts/check_forbidden_patterns.sh`** — bash `set -euo pipefail`
  script that scans the repo with GNU-grep PCRE and fails with a
  non-zero exit on any of seven regression patterns: direct
  `import { api }` in `web_portal/src/screens/**`, legacy
  `reject_reason` field name in `web_portal/src/**`, and five
  phantom API paths removed in earlier sprints
  (`acts/?placement_request_id`, `reviews/placement/`,
  `placements/${…}/start`, `reputation/history`, and raw
  `channels/${…}` outside `web_portal/src/api/**`). Cheap second net
  over the S-46 ESLint `no-restricted-imports` rule and the S-47
  snapshot test.
- **`Makefile`** — new `check-forbidden` target; `make ci` now
  depends on it in addition to `lint`, `format`, `typecheck`.

#### Developer Workflow
- Local: `make check-forbidden` or `bash scripts/check_forbidden_patterns.sh`.
- Script is already wired into `make ci`, so any `ci` invocation
  (local or future CI workflow) exercises it.
- To prove the script still catches regressions ("test-the-test"), add
  one offending line, run the script, observe `[FAIL]`, revert. See
  `reports/docs-architect/discovery/CHANGES_2026-04-20_s48-grep-guards.md`
  for a recorded run.

#### Breaking
- None. Tooling only; no runtime, behaviour, or schema change.

### S-47: Contract-drift guard (2026-04-20)

#### Added
- **`tests/unit/test_contract_schemas.py`** — parametrized pytest snapshot
  test for 8 critical backend response schemas. Captures
  `model_json_schema()` to stable JSON on disk. Any change to schema shape
  (added/removed/renamed field, type change) fails the test with a readable
  unified diff and forces an explicit snapshot regeneration, surfacing the
  contract change in code review.
- **`tests/unit/snapshots/*.json`** — 8 snapshot files locking in the current
  shape of `UserResponse`, `UserAdminResponse`, `PlacementResponse`,
  `PayoutResponse`, `ContractResponse`, `DisputeResponse`,
  `LegalProfileResponse`, `ChannelResponse`. 164 fields covered in total.

#### Developer Workflow
- Intentional schema change: run
  `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py`
  and commit the regenerated JSON alongside the schema change.
- Full CHANGES: `reports/docs-architect/discovery/CHANGES_2026-04-20_s47-contract-guards.md`.

#### Breaking
- None. Test-only addition; no runtime change.

### S-46: API module consolidation (2026-04-20)

#### Changed
- **14 direct `api.*` call sites** in `web_portal/src/screens/**`, `src/components/**`
  and `src/hooks/**` consolidated behind typed functions in `src/api/*` modules
  and React Query hooks in `src/hooks/*`. Unified architecture: `screen → hook →
  api-module → backend`. Files touched: `AdminUserDetail`, `AdminFeedbackDetail`,
  `AdminPlatformSettings`, `AdminDisputeDetail`, `AcceptRules`, `ContractDetail`,
  `ContractList`, `DocumentUpload`, `MyActsScreen`, `Feedback`, `LoginPage`,
  `AuthGuard`, `TaxSummaryBase`, `useDisputeQueries`. No behaviour change.
- **Type drift repairs**: `DisputeDetailResponse` in `web_portal/src/lib/types.ts`
  aligned with backend `DisputeResponse` schema (required `advertiser_id`/`owner_id`,
  added `resolution_comment`/`advertiser_refund_pct`/`owner_payout_pct`/`admin_id`/
  `expires_at`/`updated_at`; removed phantom embedded `placement` that backend
  never returned). `UserFeedback` renamed `response_text` → `admin_response`.
  `Act` type updated to match `acts.py:_act_to_dict`.

#### Added
- **`web_portal/src/api/auth.ts`** — `loginWidget`, `loginByCode`, `getMe`.
- **`web_portal/src/api/documents.ts`** — `uploadDocument` (multipart),
  `getUploadStatus`, `getPassportCompleteness`.
- **`web_portal/src/hooks/useActQueries.ts`** — `useMyActs`, `useSignAct`,
  `downloadActPdf` helper.
- **`web_portal/src/hooks/useDocumentQueries.ts`** — `usePassportCompleteness`,
  `useUploadDocument`, `useUploadStatus` (polls via React Query
  `refetchInterval` instead of bespoke `setTimeout`).
- **`web_portal/src/lib/types/documents.ts`** and **`platform.ts`** — typed
  responses for the new modules.
- **ESLint guard** (`web_portal/eslint.config.js`): `no-restricted-imports`
  pattern forbidding `api` from `@shared/api/client` / `@/lib/api` in
  `src/screens/**`, `src/components/**`, `src/hooks/**`. Prevents regression.

#### Fixed
- **`screens/shared/DisputeDetail.tsx`** — removed dead references to
  `dispute.placement.*` (backend never returned the embedded subobject;
  display was always silently empty). Replaced with `Размещение
  #{placement_request_id}`.
- **`ContractDetail` sign request body** — was `{method: 'button_accept'}`,
  backend expects `{signature_method: ...}`. Now routes through the existing
  `signContract()` function in `api/legal.ts` which uses the correct field.

#### Breaking
- None. Web portal only; no backend change.

#### Migration Notes
- Frontend rebuild required so the bundle picks up the refactored modules:
  `docker compose up -d --build nginx api`.

### S-45: Backend cleanup (2026-04-20)

#### Removed
- **Legacy placement action endpoints.** `POST /api/placements/{id}/accept`,
  `/reject`, `/counter`, `/accept-counter`, `/pay` and `DELETE /api/placements/{id}`
  have been dead code since S-35 when the unified `PATCH /api/placements/{id}`
  action-dispatch endpoint shipped. Audit of `mini_app/`, `web_portal/` and
  `src/bot/handlers/` confirmed no live callers remained. Alongside the endpoints,
  removed the `RejectRequest` / `CounterOfferRequest` schemas, the `field_validator`
  import, and the `NOT_CHANNEL_OWNER` / `NOT_PLACEMENT_ADVERTISER` constants
  (all only consumed by the removed handlers). `placements.py`: −259 lines.
- **Dead `rating` queue** listener from `worker_background` command in
  `docker-compose.yml`. `rating_tasks.py` was deleted in v4.3 and the
  `task_routes` entry was removed in S-36; the docker-compose listener was
  kept for in-flight safety only. Sufficient release cycles have elapsed.
- **Unused `DisputeRepository.get_by_user`** — all dispute listings use
  `get_by_user_paginated`. 11 lines removed from `src/db/repositories/dispute_repo.py`.

#### Breaking
- None. Public HTTP surface narrows to the unified PATCH endpoint that has
  been the sole client path since S-35.

#### Migration Notes
- No DB migrations. No deployment prerequisite beyond a normal worker
  rebuild so the updated docker-compose command takes effect:
  `docker compose up -d --build worker_background`.

### S-48: Prod smoke-test blockers hotfix (2026-04-19)

#### Fixed
- **A1 — `/api/channels/available` 422 (P0)** — `GET /{channel_id}` was declared
  before `GET /available`/`/stats`/`/preview` in `src/api/routers/channels.py`,
  so FastAPI tried to parse `"available"` as `int` → `int_parsing` 422. Moved all
  four `/{channel_id}*` routes to the end of the router, after the static-path
  GETs. Wizard "Создать кампанию" end-to-end unblocked. Side-effect: `/stats`
  and `/preview` (also broken) now resolve correctly too.
- **F1 — 500 on `/api/disputes/admin/disputes` (P0)** — `DisputeRepository.get_all_paginated`
  did not eager-load `PlacementDispute.advertiser` / `.owner`, so router access
  to `d.advertiser.username` triggered async lazy-load → `MissingGreenlet` →
  500. Added `selectinload` for both relationships. Also added `Query(alias="status")`
  on the admin router so the frontend's `?status=…` query param takes effect
  (previously silently ignored in favour of the default `"open"`).
- **D1 — passport field drift & badge (P0/P2)** — source already sends
  `passport_issue_date` (S-43 §2.5, commit `9c8d54a`); prod was on a stale
  bundle. Also added a `📇 Паспорт добавлен` pill to `LegalProfileView.tsx`
  (renders when `profile.has_passport_data === true`) so Individual/Self-employed
  users can confirm PII is on file without exposing values.
- **S-43 drift leftovers on dispute read side** — `DisputeDetailResponse.owner_comment`
  → `owner_explanation` in `web_portal/src/lib/types.ts`; corresponding reads
  in `MyDisputes.tsx` and `DisputeDetail.tsx`. PATCH body keeps `owner_comment`
  name (matches backend `DisputeUpdate` input schema).

#### Added
- **A7 — `/profile/reputation` SPA route (P1)** — new
  `web_portal/src/screens/common/ReputationHistory.tsx` screen consuming
  `useReputationHistory(50, 0)`. Registered at `profile/reputation` in
  `App.tsx` (inside RulesGuard). "История изменений →" link added to the
  Reputation card in Cabinet.

#### Investigated — no code change
- **E1 — AdminPayouts missing from prod bundle (P1)** — file, lazy import, and
  route are all present in source (`commit 366aafe` + `bcb56f6`). 404 was
  caused by a stale prod bundle. Fix is `docker compose up -d --build nginx`.
  Same applies to the `page_size` / `gross_amount` / `has_passport_data` "0
  occurrences" findings from the smoke report — all are present in source.

#### Deploy requirement
- `docker compose up -d --build nginx api` is **mandatory** after merge so
  Vite rebuilds `dist/` inside the nginx image. Without the `--build`, D1
  Part A, E1, and the stale-bundle parts of S-43 drift do not take effect.

#### Not in scope (deferred to next sprint)
- A2 (`useMyPlacements` page_size — already clean in source, bundle only).
- A3 (counter-offer wiring verification — needs a second account).
- B1/B2 (surface `last_er` / `avg_views` in channel UI).
- C1 (`GET /api/contracts/me` 422 — fallback works but still noisy).
- F1 user side (`/disputes` route not mounted; chunk exists).
- Stage 4–7 items from `FIX_PLAN_00_index.md`.

### S-47 Stage 7 planning — UI/UX redesign per DS v2 (2026-04-19)

#### Documentation
- **New fix-plan chapter** — `reports/20260419_diagnostics/FIX_PLAN_07_ui_redesign_ds_v2.md` (40–56 h, P1) covering Design System v2 tokens migration, PortalShell v2 (Sidebar + Topbar), full Cabinet redesign (BalanceHero × 3 variants, PerformanceChart, QuickActions, NotificationsCard, ProfileCompleteness, RecommendedChannels, RecentActivity), 30+ screens redesign checklist, A11y pass, performance audit.
- **Fix-plan index bumped** — `FIX_PLAN_00_index.md` totals 86–118 h across 7 stages (was 46–62 h / 6 stages).
- **Handoff deliverable logged** — `CHANGES_2026-04-19_s47-ui-redesign-plan-stage7.md`.

### GitHub Integration (2026-04-19)

#### Added
- **GitHub API integration** via `GitHubService` (`src/core/services/github_service.py`) with methods for issue/PR management.
- **Async GitHub operations** via Celery tasks (`src/tasks/github_tasks.py`): `github:create_issue`, `github:create_pr`, `github:add_comment`, `github:close_issue`.
- **GitHub configuration** — settings fields: `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`.
- **Celery routing** — `github:*` tasks routed to `background` queue (worker_background).

#### Dependencies
- PyGithub required (not yet in `pyproject.toml`); add via `poetry add PyGithub`.

### S-44 Stage 3: Missing frontend↔backend integration (P1) — fix plan Stage 3 of 6 (2026-04-19)

#### Added
- **TopUpConfirm polling** — `useTopupStatus(paymentId)` hook (`web_portal/src/hooks/useBillingQueries.ts`) опрашивает `GET /billing/topup/{payment_id}/status` каждые 3 сек до 120 сек; при `succeeded` инвалидирует `billing.balance`/`billing.history`/`user.me`, показывает соответствующий success/error/timeout UI в `TopUpConfirm.tsx`.
- **AdminPayouts в сайдбаре.** «Выплаты» (иконка `Banknote`) добавлен в `PortalShell.tsx` admin-секцию + breadcrumb `/admin/payouts`.
- **Accept-rules warning banner.** `useNeedsAcceptRules()` хук + orange Notification в `PortalShell` поверх контента (исключая `/accept-rules`) → кнопка «Принять» ведёт на `/accept-rules`. Fallback-слой рядом с `RulesGuard`.
- **Evidence в OpenDispute.** `useDisputeEvidence(placementId)` + карточка «Что мы знаем о публикации» (published_at, deleted_at + тип удаления, total_duration_minutes, ERID-флаг, раскрывающийся лог событий с ссылками на пост).
- **Admin manual credits** — в `AdminUserDetail.tsx` добавлены две карточки:
  - «Зачислить из доходов платформы» → `POST /admin/credits/platform-credit`.
  - «Геймификационный бонус» → `POST /admin/credits/gamification-bonus` (RUB + XP).
  Оба mutation'а инвалидируют `admin.user.{id}` и `admin.platform-stats`.

#### Fixed
- **KUDiR download 401 в AdminAccounting.** Режим `downloadMode='simple'` в `TaxSummaryBase` вызывал `window.open` без Bearer-токена → `/admin/tax/kudir/*/pdf|csv` отвечал 401. Переключено на `auth` (fetch+blob). Мёртвая `simple`-ветка удалена.
- **ContractData.status → contract_status** (`ContractDetail.tsx`) — Stage 2 carry-over, всплыл при `tsc`: локальный интерфейс использовал `status`, а роутер возвращает `contract_status` (см. S-43).
- **Phantom re-exports Payout/AdminPayout/PayoutListAdminResponse** из `lib/types/index.ts` — они уже были удалены из `types/billing.ts` в S-43, но барельный export об этом не знал.

#### Known follow-ups (deferred)
- **§3.3 CampaignVideo uploads** — требует или Redis-поллинг + deep-link в бота (новый `src/bot/handlers/upload_video.py`), или новый POST multipart endpoint. Вынесено в отдельное обсуждение.
- **§3.5 PRO/BUSINESS analytics** (`/analytics/summary|activity|top-chats|topics|ai-insights`) — зависит от бизнес-решения по продвижению PRO-тарифа.
- **§3.6 Channel preview в wizard** — low business value; кандидат на удаление в Stage 4.
- **§3.8 прочие admin-экраны** — LegalProfiles verify-UI, AuditLog screen, AdminContracts screen — заведены в бэклог как отдельные эпики.

### S-43 Stage 2: Contract drift alignment (P0) — fix plan Stage 2 of 6 (2026-04-19)

#### Added
- **Канонический TS-тип Payout** — `web_portal/src/lib/types/payout.ts` с `PayoutResponse`, `AdminPayoutResponse`, `AdminPayoutListResponse`, `PayoutStatus`, `PayoutCreateRequest`; поля точно соответствуют `src/api/schemas/payout.py`.
- **`CampaignActionResponse`, `CampaignDuplicateResponse`** — типы для ответов `campaigns/{id}/start|cancel|duplicate`.
- **PlacementRequest поля (TS)** — `advertiser_counter_price`, `advertiser_counter_schedule`, `advertiser_counter_comment`, `updated_at`.
- **ChannelResponse поля (TS)** — `last_er`, `avg_views`, `is_test`.
- **ReputationHistoryItem поля (TS)** — `user_id`, `role`, `comment`.
- **`.gitignore`** — исключение `!web_portal/src/lib/` для Python-правила `lib/`, которое скрывало 11 type/constant/timeline файлов из VCS.

#### Changed
- **User.referral_code** — `string` → `string | null` (соответствует `UserResponse.referral_code: str | None`).
- **PlacementRequest.expires_at / proposed_schedule** — → nullable.
- **Channel.category** — `string` → `string | null`.
- **ReputationHistoryItem.reason** → `comment` (под бэкенд `ReputationHistoryEntry.comment`).
- **DisputeReason (TS)** — добавлены bot-legacy значения `post_removed_early`, `bot_kicked`, `advertiser_complaint`.
- **OwnPayouts status pill map** — `completed` → `paid`, добавлен `cancelled`.

#### Fixed
- **Payout field drift** (3 определения → 1 канонический): `amount/fee/payment_details/completed` → `gross_amount/fee_amount/net_amount/paid`; `reject_reason` → `rejection_reason`.
- **`contract.status` was always undefined** — TS Contract декларировал не существующий на бэке `status`. Удалён; `contract_status` теперь required. Миграция потребителей в `ContractList.tsx`, `ContractDetail.tsx`, `lib/timeline.ts`.
- **LegalProfile PII utechka (mock)** — 4 паспортных поля удалены из response-типа (бэк их не возвращает); в `LegalProfileSetup.tsx` удалены pre-fill чтения из ответа, submit-поле переименовано `passport_issued_at` → `passport_issue_date`.
- **Dispute legacy тип** — удалён `interface Dispute` (placement_id/owner_comment/resolution_action); потребители переходят на `DisputeDetailResponse`.
- **`startCampaign/cancelCampaign/duplicateCampaign` response типы** — ранее декларировались как `PlacementRequest`; теперь соответствуют реальному ответу бэка.
- **PayoutStatus enum в `lib/types.ts`** — был `'completed'` вместо `'paid'` и без `'cancelled'`; удалён. Единый источник — `types/payout.ts`.

#### Removed
- `Payout/AdminPayout/PayoutListAdminResponse` как собственные интерфейсы в `lib/types/billing.ts` — теперь re-export из `types/payout.ts`.
- `Dispute` (legacy) interface из `lib/types/dispute.ts` и barrel-export.

### S-42 Stage 1: Phantom calls (P0) — fix plan Stage 1 of 6 (2026-04-19)

#### Added
- **`GET /api/channels/{channel_id}`** → `ChannelResponse`. Владелец или админ (404 если чужой канал). Перед `DELETE /{channel_id}`; int-типизация не перекрывает `/available`, `/stats`, `/preview`, `/compare/preview`.
- **`GET /api/acts/mine?placement_request_id={int}`** — новый опциональный query-фильтр по размещению (пробрасывается в `ActRepository.list_by_user`).
- **Admin Payouts API:**
  - `GET /api/admin/payouts?status=&limit=&offset=` → `AdminPayoutListResponse` (обогащён `owner_username`, `owner_telegram_id`).
  - `POST /api/admin/payouts/{id}/approve` → `paid`, фиксирует `admin_id`.
  - `POST /api/admin/payouts/{id}/reject` (body `{reason}`) → `rejected`, возвращает `gross_amount` на `earned_rub`, фиксирует `admin_id` и `rejection_reason`.
- **`PayoutService.approve_request(payout_id, admin_id)` / `reject_request(payout_id, admin_id, reason)`** — admin-обёртки над существующими `complete_payout` / `reject_payout`.
- **Pydantic:** `AdminPayoutResponse`, `AdminPayoutListResponse`, `AdminPayoutRejectRequest` в `src/api/schemas/payout.py`.
- **Frontend:** маршрут `/admin/payouts` в `web_portal/src/App.tsx` (подключение существующего orphan screen `AdminPayouts.tsx`).

#### Fixed
- **Phantom URL `reviews/placement/{id}`** → `reviews/{id}` (бэк без `/placement/` префикса). Экран отзывов размещения теперь работает.
- **Phantom URL `reputation/history`** → `reputation/me/history`; параметры выровнены на `limit`/`offset`.
- **Phantom URLs `placements/{id}/start|cancel|duplicate`** → `campaigns/{id}/start|cancel|duplicate`. Эндпоинты существуют только на `/api/campaigns/*`, не на `/placements/*`.
- **Placement list pagination** — `page`/`page_size` → `limit`/`offset` (на бэке последнее).
- **Phantom URL `acts/?placement_request_id=X`** → `acts/mine?placement_request_id=X`; response-тип выровнен на `ActListResponse` (бэк отдаёт объект, не массив).
- **`AdminPayouts.tsx` orphan screen** — теперь подключён к роутингу.
- **Семантическое разделение `rejected` vs `cancelled`** — отклонение админом теперь ставит `rejected` (ранее `reject_payout` ошибочно ставил `cancelled`, что смешивалось с отменой пользователем).

#### Known follow-ups (Stage 2 scope)
- Type drift: `AdminPayout.reject_reason` vs backend `rejection_reason`; `ReputationHistoryItem.reason` vs backend `comment`; `PlacementRequest` ↔ `CampaignResponse` в start/cancel/duplicate. Будет устранено в `fix/s-43-contract-alignment`.

### Diagnostic: Deep audit web_portal ↔ backend (2026-04-19)

#### Added
- **Углублённый аудит web_portal ↔ backend** — `reports/20260419_diagnostics/web_portal_vs_backend_deep.md`. Перепроверяет предыдущую поверхностную диагностику и фиксирует: 8 phantom-calls (фронт дёргает несуществующие URL), 7 групп контрактного дрейфа (Payout × 3 определения, Contract.status, LegalProfile паспортные поля, PlacementResponse.advertiser_counter_*, User.referral_code, Channel.category, Dispute legacy дубль-тип), ~40 orphan-эндпоинтов, 2 мёртвых сервиса (`link_tracking_service`, `invoice_service`), 1 orphan screen (`AdminPayouts.tsx`), 22 прямых `api.*`-вызова в обход хуков. Код не менялся — это диагностический документ с P0/P1/P2 action-листом.
- **План устранения проблем аудита** — 6 этапных файлов в `reports/20260419_diagnostics/FIX_PLAN_*.md` + `FIX_PLAN_00_index.md`. Каждый этап содержит feature-ветку, задачи с file:line ссылками, критерии Definition of Done и оценку трудозатрат (всего 46–62 ч). Этапы: 1) Phantom calls (P0), 2) Contract drift (P0), 3) Missing integration (P1), 4) Backend cleanup (P1), 5) Arch debt (P2), 6) Tests + guards (P2).

### S-38 follow-up: ORD Yandex provider skeleton + auto-init (April 2026)

#### Added
- **`YandexOrdProvider` skeleton** — `src/core/services/ord_yandex_provider.py`, class implementing `OrdProvider` protocol; all methods raise `NotImplementedError("Yandex ORD integration required")`. Placeholder for Яндекс ОРД API v7 contract.
- **`.env.ord.sample`** — reference env file documenting `ORD_PROVIDER`, `ORD_API_KEY`, `ORD_API_URL`, `ORD_BLOCK_WITHOUT_ERID`, `ORD_REKHARBOR_ORG_ID`, `ORD_REKHARBOR_INN` for production setup.

#### Changed
- **ORD provider auto-init from settings** — `ord_service.py` now selects provider at import time via `_init_ord_provider_from_settings()`: `ORD_PROVIDER=yandex` returns `YandexOrdProvider` (fails fast if `ORD_API_KEY`/`ORD_API_URL` missing); otherwise `StubOrdProvider`. Deployments no longer require code changes to switch providers.
- **CLAUDE.md — Pre-Launch Blockers** — step 4 reworded: "Real provider is auto-selected by `ORD_PROVIDER` in settings (no code change needed)".
- **`OrdService.report_publication` signature** — unused `channel_id` and `post_url` params commented out (half-step; call-site cleanup deferred).

### S-41: Web Portal Fixes (April 2026)

#### Fixed
- **ORD message** — Fixed incorrect text "после публикации" → "до публикации рекламы" in OrdStatus screen (`web_portal/src/screens/advertiser/OrdStatus.tsx`)
- **Tariff payment** — Fixed API endpoint from `billing/purchase-plan` to `billing/plan` (`web_portal/src/api/billing.ts`)
- **Disputes navigation** — Added "Споры" menu item for regular users and breadcrumb entries (`web_portal/src/components/layout/PortalShell.tsx`)

### S-40: Tech Debt Cleanup (April 2026)

#### Fixed
- **D-10 async Redis (P0)** — `_check_dedup` was a sync function using `redis_sync_client` inside async Celery tasks, blocking the event loop on every placement SLA check. Replaced with `_check_dedup_async` using the existing async `redis_client`; all 6 call sites updated to `await` (`src/tasks/placement_tasks.py`)

#### Removed
- **D-06: Dead `check_pending_invoices` task** — DEPRECATED no-op task and its helper `_check_pending_invoices` removed from `billing_tasks.py`; never called anywhere in the codebase (`src/tasks/billing_tasks.py`)

#### Added
- **D-20: `.gitkeep` for `reports/monitoring/payloads/`** — empty directory now tracked by git (`reports/monitoring/payloads/.gitkeep`)
- **Pre-Launch Blockers section in CLAUDE.md** — documents ORD stub (legal blocker under ФЗ-38) and FNS validation stub as required actions before production launch with real payments

---

### S-39a: Backend Schema Completeness (April 2026)

#### Added
- **Canonical `UserResponse` schema** — `src/api/schemas/user.py` is now single source of truth with 19 fields (XP, referral, credits, plan_expires_at, ai_generations_used, legal fields). Replaces two divergent inline classes in `auth.py` (13 fields) and `users.py` (15 fields) (`src/api/schemas/user.py`, `src/api/routers/auth.py`, `src/api/routers/users.py`)
- **`PlacementResponse` +11 fields** — owner_id, final_schedule, rejection_reason, scheduled_delete_at, deleted_at, clicks_count, published_reach, tracking_short_code, has_dispute, dispute_status, erid. `has_dispute` / `dispute_status` populated via ORM properties that safely check eager-loaded `disputes` relationship (`src/api/routers/placements.py`, `src/db/models/placement_request.py`)
- **`ChannelResponse.is_test`** — test flag now surfaced in all 4 channel endpoints (list, create, activate, update_category) (`src/api/schemas/channel.py`, `src/api/routers/channels.py`)
- **`User.ai_generations_used`** in mini_app `types.ts` — symmetry with canonical backend UserResponse (`mini_app/src/lib/types.ts`)

#### Fixed
- **`counter_schedule` type** — was `Decimal | None` (bug), corrected to `datetime | None` in `PlacementResponse` (`src/api/routers/placements.py`)
- **`OwnPayouts.tsx` field names** — aligned with S-32 backend rename: `gross_amount`, `fee_amount`, `requisites` (`mini_app/src/screens/owner/OwnPayouts.tsx`)

#### Removed
- **Dead `UserRole` type and `current_role` field** from mini_app `types.ts` — backend never returned `current_role`; was TypeScript-silent `undefined` at runtime (`mini_app/src/lib/types.ts`)

---

### S-38: Escrow Recovery — 4 P0 Fixes + Idempotency (April 2026)

#### Fixed
- **P0-1: `publish_placement` freezes escrow on failure** — On any publish exception, `BillingService.refund_escrow(..., scenario="after_escrow_before_confirmation")` is called in a separate session; status set to `failed`; advertiser notified with refund amount (`src/tasks/placement_tasks.py`)
- **P0-2: `check_escrow_sla` bypasses BillingService** — Replaced `advertiser.balance_rub +=` direct mutation with `BillingService.refund_escrow()`; per-item commit with rollback on error; `platform_account.escrow_reserved` now stays consistent (`src/tasks/placement_tasks.py`)
- **P0-3: `check_escrow_stuck` was a silent no-op** — Group A (message posted): dispatches `delete_published_post.apply_async`; Group B (pre-post): calls `BillingService.refund_escrow`; per-item commit; admin alert sent; `meta_json["escrow_stuck_detected"]` set for auditability (`src/tasks/placement_tasks.py`)
- **P0-4: `delete_published_post` fails silently** — Added `autoretry_for=(Exception,)`, `max_retries=5`, `retry_backoff=True`, `retry_backoff_max=600`; async helper now raises on error for Celery retry (`src/tasks/placement_tasks.py`)
- **nginx Docker build failure** — Created missing TypeScript type files (`timeline.types.ts`, `lib/types/billing.ts`, `api/acts.ts`) that `timeline.ts` imports; fixed type predicate error in `deriveActTimelineEvents` (`web_portal/src/lib/`)

#### Added
- **Idempotency guard on `refund_escrow`** — Before opening a transaction, SELECT checks for existing `Transaction` with matching `placement_request_id + type=refund_full + user_id`; if found → log and return. `Transaction.placement_request_id` now populated on refund rows as the FK anchor (`src/core/services/billing_service.py`)
- **Admin payout API functions** — `getAdminPayouts`, `approveAdminPayout`, `rejectAdminPayout` in `web_portal/src/api/admin.ts`; corresponding hooks in `useAdminQueries.ts`
- **36 regression tests** — Source-inspection + mock-based tests for all 4 P0 fixes and idempotency guard (`tests/tasks/test_placement_escrow.py`, `tests/test_billing_service_idempotency.py`)

---

### S-37: Notification Infrastructure Fixes (April 2026)

#### Fixed
- **task_routes dot/colon mismatch** — All 13 Celery `task_routes` patterns changed from `prefix.*` to `prefix:*`; `fnmatch` requires colon-patterns to match colon-prefixed task names. `mailing:check_low_balance` and `mailing:notify_user` now route correctly to `mailing` queue (`src/tasks/celery_app.py`)
- **18 per-call `Bot()` instantiations** — Replaced every `Bot(token=...)` in tasks with `get_bot()` singleton from `_bot_factory.py`; one `aiohttp.ClientSession` per worker process (`src/tasks/notification_tasks.py`, `placement_tasks.py`, `integrity_tasks.py`, `gamification_tasks.py`)
- **12 tasks skipped `notifications_enabled`** — All user-facing notification tasks now check `user.notifications_enabled` via `_notify_user_checked()` helper before sending (`src/tasks/notification_tasks.py`, `placement_tasks.py`)
- **`yookassa_service` layering violation** — `core/services/yookassa_service.py` no longer creates `Bot()` directly; payment success notification delegated to `notify_payment_success.delay()` Celery task (`src/core/services/yookassa_service.py`)

#### Added
- **`src/tasks/_bot_factory.py`** — Per-process Bot singleton: `init_bot()`, `get_bot()`, `close_bot()`; wired to `worker_process_init` / `worker_process_shutdown` signals in `celery_app.py`
- **`_notify_user_checked(user_id, msg, ...) → bool`** — DB-aware notification helper: looks up by `user.id`, checks `notifications_enabled`, handles `TelegramForbiddenError`
- **`notifications:notify_payment_success`** — New Celery task on `notifications` queue for YooKassa payment success notifications
- **11 regression tests** — `tests/tasks/test_bot_factory.py` (4 tests), `tests/tasks/test_notifications_enabled.py` (7 tests)

---

### S-35: API Contract Alignment — Legal Flow + Compare Endpoint (April 2026)

#### Fixed
- **P0 N-08: acceptRules always 422** — `web_portal/src/api/legal.ts` now sends `{accept_platform_rules: true, accept_privacy_policy: true}` body required by `AcceptRulesRequest` (`web_portal/src/api/legal.ts`)
- **P0 Extra-1: signContract always 422** — `web_portal/src/api/legal.ts` sends `{signature_method}` instead of `{method}` matching `ContractSignRequest` (`web_portal/src/api/legal.ts`)
- **P0 Extra-2: requestKep always 404** — corrected path `contracts/${id}/request-kep → contracts/request-kep` and body `{email} → {contract_id, email}` in `legal.ts` and `KepWarning.tsx` (`web_portal/src/api/legal.ts`, `web_portal/src/components/contracts/KepWarning.tsx`)
- **N-05: ComparisonChannelItem field mismatch** — renamed `member_count→subscribers`, `er→last_er`; added `topic`, `rating` to backend schema and service output (`src/api/routers/channels.py`, `src/core/services/comparison_service.py`)
- **ComparisonService AttributeError** — fixed broken attribute access (`last_avg_views→avg_views`), added `selectinload(channel_settings)` for `price_per_post`, fixed `channel_id→id` key (`src/core/services/comparison_service.py`)

#### Removed
- **Extra-3: Stale docstring** — removed non-existent `GET /api/billing/invoice/{id}` reference from billing router module docstring (`src/api/routers/billing.py`)

#### Added
- **12 regression tests** — cover N-08/Extra-1 body schemas, N-05 schema field names, ComparisonService metric keys (`tests/unit/test_s35_api_contract_regression.py`)

---

### S-34: Pydantic Schema ↔ SQLAlchemy Model Mismatches (April 2026)

#### Fixed
- **STOP-1: CampaignResponse crash** — rewrote schema to match `PlacementRequest` fields: deleted ghost `title`, renamed `text → ad_text`, `filters_json → meta_json`, `scheduled_at → proposed_schedule`; changed `created_at`/`updated_at` from `str` to `datetime`. Fixes 100% crash rate on POST/GET/PATCH `/api/campaigns` (`campaigns.py`)
- **STOP-1: Silent meta_json data loss** — `CampaignUpdate` renamed `filters_json → meta_json`; `model_dump()` now returns keys matching `PlacementRequest` attrs, so `repo.update()` correctly persists changes (`campaigns.py`)
- **STOP-2: activate_channel crash** — added missing `owner_id=channel.owner_id` and `created_at=channel.created_at.isoformat()` to `ChannelResponse(...)` constructor (`channels.py:558`)
- **STOP-2 expanded: add_channel crash** — added missing `created_at` to `ChannelResponse(...)` constructor in `add_channel` endpoint (`channels.py:431`)
- **STOP-2 expanded: update_channel_category crash** — added missing `created_at` to `ChannelResponse(...)` constructor in `update_channel_category` endpoint (`channels.py:601`)
- **UserResponse.first_name misleading contract** — tightened `str | None → str`; `User.first_name` is `NOT NULL` in DB (`users.py`)

#### Changed
- **DuplicateResponse** — `title → ad_text`; fixed docstring listing copied fields (`campaigns.py`)
- **PlacementCreateRequest.proposed_price** — `int → Decimal`; removed manual `Decimal(str(...))` cast at call site (`placements.py`)
- **ChannelSettingsUpdateRequest.price_per_post** — `int → Decimal`; removed manual `Decimal(str(...))` cast in `_build_update_data` (`channel_settings.py`)

#### Removed
- **ChannelSettingsResponse.from_attributes=True** — schema is always constructed manually, never via `model_validate(orm_obj)`; flag was a future-crash trap (`channel_settings.py`)

#### Added
- **19 schema regression tests** — verify STOP-1/STOP-2 field names, types, required fields, ORM round-trip; no DB required (`tests/unit/test_s34_schema_regression.py`)

#### P2.2 (ActResponse) — Skipped
- Research referenced `schemas/act.py:22` (ActResponse Pydantic class) — does not exist. `acts.py` uses `_act_to_dict()` plain dict. No action required.

---

### S-33: Migration Drift Fix — 0001 schema snapshot (April 2026)

#### Fixed
- **5 enum drift** — added 20 missing values across `placementstatus` (+completed, +ord_blocked), `transactiontype` (+storno, +admin_credit, +gamification_bonus), `disputereason` (+5 frontend values), `disputestatus` (+closed), `disputeresolution` (+4 frontend values) (`0001_initial_schema.py`)
- **channel_mediakits columns** — added `owner_user_id` (FK→users), `logo_file_id`, `theme_color` missing from migration (`0001_initial_schema.py`)
- **reviews unique constraint name** — `uq_reviews_…` → `uq_review_…` matching model definition (`0001_initial_schema.py`)
- **self-referencing FK cascade** — added `ON DELETE SET NULL` to `users.referred_by_id` and `transactions.reverses_transaction_id` (`0001_initial_schema.py`)
- **FK ondelete alignment** — added `ondelete="SET NULL"` to `acts.contract_id`, `invoices.placement_request_id/contract_id`, `transactions.act_id/invoice_id` in ORM models (`act.py`, `invoice.py`, `transaction.py`)
- **acts.act_number** — removed duplicate `UniqueConstraint` from ORM (uniqueness already enforced by named `Index` in `__table_args__`) (`act.py`)
- **alembic check noise** — suppressed `EncryptedString`/`HashableEncryptedString` type drift and column-comment drift via `env.py` (`env.py`)

#### Added
- **extracted_ogrnip** to `DocumentUpload` ORM model — syncs model with pre-existing DB column (`document_upload.py`)
- **6 FK indexes** — `placement_disputes.(advertiser_id, owner_id, admin_id)`, `reputation_history.placement_request_id`, `user_badges.badge_id`, `badge_achievements.badge_id` — eliminates full-table scans (`0001_initial_schema.py`, `dispute.py`, `badge.py`, `reputation_history.py`)

#### Removed
- **0002_add_advertiser_counter_fields.py** — absorbed `advertiser_counter_price/schedule/comment` columns into 0001 snapshot; file deleted

#### Migration Notes
- `alembic check` → `No new upgrade operations detected.` (zero drift)
- Single revision `0001_initial_schema (head)` — 0002 removed
- DB reset required on pre-production instances: `DROP DATABASE / CREATE DATABASE / alembic upgrade head`

### S-29: Mobile UX & Channel Management (v4.6 — April 2026)

#### Fixed
- **Empty categories table** — seeded 11 categories from `categories_seed.py`, added `op.bulk_insert()` to `0001_initial_schema.py` so categories auto-populate on fresh deploys
- **Category grid chicken-and-egg (web_portal)** — `canAdd` required `selectedCategory` but `CategoryGrid` only rendered when `canAdd` was true. Split into `showCategoryGrid` (visibility) and `canAdd` (submit guard)
- **Channel delete silently fails** — backend returns `204 No Content` but frontend called `.json<void>()` which throws on empty body. Changed to `.text()` in both `mini_app` and `web_portal` API clients
- **Hard-delete inconsistency** — API used `session.delete()` losing channel history. Changed to `channel.is_active = False` (soft-delete) matching bot behavior, with active placements check

#### Changed
- **Auto-navigate after channel add** — `useEffect` on `addMutation.isSuccess` → `navigate('/own/channels', { replace: true })` in both mini_app and web_portal
- **Mobile icon-only buttons** — replaced text buttons with emoji-only icon buttons (`min-h-[44px] min-w-[44px]`) across OwnChannels, MyCampaigns, OwnRequests. Eliminates horizontal overflow on 375px screens
- **Button component** — added `icon` prop for square buttons, fixed `min-h-[36px]` → `min-h-[44px]` (WCAG/Apple HIG), added `relative` for spinner centering, added `title` prop for tooltips
- **ChannelCard 3-zone layout (mini_app)** — refactored from flat flex-row to Header/Body/Footer structure. Name upgraded to `text-base` display font, stats use value/label pairs, chevron footer for clickable cards. Zero inline-styles.
- **MobileCard shared component (web_portal)** — new shared component for mobile list screens. Replaces copy-pasted inline cards in OwnChannels, MyCampaigns, OwnRequests. 3-zone layout: Header (avatar + title + status) → Body (stats grid) → Footer (action buttons). Typography hierarchy: 16px title → 14px values → 10px labels.

#### Files
- `src/db/migrations/versions/0001_initial_schema.py` — category seed data
- `src/api/routers/channels.py` — soft-delete, active placements check
- `mini_app/src/api/channels.ts` — `.text()` for delete
- `mini_app/src/screens/owner/OwnAddChannel.tsx` — auto-navigate
- `web_portal/src/api/channels.ts` — `.text()` for delete
- `web_portal/src/screens/owner/OwnAddChannel.tsx` — category grid fix + auto-navigate
- `web_portal/src/shared/ui/Button.tsx` — icon prop, 44px min-height, spinner fix
- `web_portal/src/screens/owner/OwnChannels.tsx` — icon-only buttons
- `web_portal/src/screens/advertiser/MyCampaigns.tsx` — icon-only buttons
- `web_portal/src/screens/owner/OwnRequests.tsx` — icon-only buttons
- `mini_app/src/components/ui/ChannelCard.tsx` — 3-zone layout refactor
- `mini_app/src/components/ui/ChannelCard.module.css` — complete rewrite
- `web_portal/src/shared/ui/MobileCard.tsx` — new shared mobile card component
- `web_portal/src/screens/owner/OwnChannels.tsx` — uses MobileCard
- `web_portal/src/screens/advertiser/MyCampaigns.tsx` — uses MobileCard
- `web_portal/src/screens/owner/OwnRequests.tsx` — uses MobileCard

### S-29: Campaign Lifecycle Tracking (v4.6 — April 2026)

#### Added
- **Full lifecycle timeline** — 8-stage campaign tracking: created → waiting owner → payment → escrow → waiting placement → published → deletion countdown → completed
- **`completed` status** — new terminal `PlacementStatus` set after post deletion + escrow release (ESCROW-001 compliance)
- **ERID status display** — marketing token status (assigned/pending) shown directly in timeline
- **Deletion countdown** — real-time display of remaining time until auto-deletion based on `scheduled_delete_at`
- **`RequestCard` completed support** — new STATUS_PILL mapping for completed status with "Завершено" label

#### Changed
- **`publication_service.delete_published_post()`** — now sets `placement.status = PlacementStatus.completed` after `release_escrow()` (previously left status as `published`)
- **`CampaignWaiting.tsx`** — rewrote `buildTimelineEvents()` to show all 8 lifecycle stages with proper past/current/terminal state indicators
- **`MyCampaigns.tsx`** — added `'completed'` to `COMPLETED_STATUSES` so completed campaigns appear in "Завершённые" tab
- **`check_published_posts_health` Celery task** — now monitors both `published` and `completed` statuses for audit purposes

#### Database
- **Enum migration** — `ALTER TYPE placementstatus ADD VALUE 'completed'` (forward-only, cannot rollback)

#### Fixed
- **Missing state transition bug** — placements remained `published` after deletion, making it impossible to distinguish active vs completed campaigns
- **Timeline gap** — previously showed only 4 stages; now shows all 8 including waiting placement and escrow release
- **Legal profile "Кем выдан" field** — replaced single-line `<input>` with `<Textarea rows={3}>` to accommodate long issuing authority names (e.g. "ОУФМС России по г. Москве")

### S-29: Quality & Security Sprint (v4.6 — April 2026)

#### Security Fixes (P0)
- **XSS via dangerouslySetInnerHTML** — added DOMPurify sanitization in 4 files (mini_app + web_portal ContractList, AcceptRules) with strict allowlist (p, strong, em, ul, ol, li, h1-h3, br, a, b, i, u)
- **Stale auth closure** — `useAuth` now includes `initData` in deps array with abort controller, preventing permanent unauthenticated state when Telegram SDK initializes asynchronously
- **AuthGuard infinite loop** — added `useRef` to prevent re-verification after logout, eliminating flash-loading and redirect loops in web_portal
- **401 redirect race condition** — added singleton lock in API client to prevent multiple simultaneous redirects

#### Performance & Reliability (P1)
- **useMe staleTime** — changed from 0 to 5 min (saves ~15 redundant API calls per session)
- **Zustand reset()** — uses explicit clone instead of shared reference (prevents stale data across navigations)
- **Placements parallel** — `Promise.all` replaces sequential `for...of` (5x faster for 5 channels)
- **Modal accessibility** — Escape key handler, `aria-modal`, `role="dialog"`
- **Type safety** — eliminated all `any` types: `DisputeResponse`, `ContractData`, `ValidationFieldDetail`
- **StatusPill** — expanded type to include `info`/`neutral` statuses

#### UX & Polish (P2-P3)
- `formatCurrency` guards against NaN/Infinity
- `navigate(-1 as unknown as string)` → `window.history.back()`
- `useConsent` synchronous init (eliminates cookie banner flash)
- Removed `alert()` calls in MyCampaigns
- `TopUp` fee uses `Math.round()` instead of `toFixed(0)`

### S-29: Python 3.14 Runtime Upgrade (v4.5 — April 2026)

#### Changed
- **Python runtime** upgraded from 3.13.7 to **3.14.4** (deadsnakes PPA for host, `python:3.14-slim` for containers)
- **aiogram** upgraded to **3.27.0** (Python 3.14 + pydantic 2.12 support)
- **pydantic** upgraded to **2.12.5** with pydantic-core **2.41.5** (Python 3.14 PyO3 wheels)
- **asyncpg** upgraded to **0.31.0** (Python 3.14 wheel available)
- **pillow-heif** upgraded to **1.3.0** (prebuilt Python 3.14 wheels)
- **ruff** upgraded to **0.12.0**, **mypy** to **1.17.0**, **pytest-asyncio** to **0.26.0**

#### Fixed
- **`asyncio.DefaultEventLoopPolicy` removed** — eliminated deprecated call in `parser_tasks.py`; Linux default is already correct
- **Forward reference type annotations** — removed unnecessary quotes from 97+ type annotations (ruff UP037)
- **Callback null-safety** — added `assert callback.data is not None` and `hasattr` guards in `monitoring.py`
- **FNSValidationError** — converted to frozen dataclass (ruff B903, AAA-grade)
- **Docker C-extension build** — added gcc, python3-dev, libpq-dev, pkg-config to builder stages for asyncpg/cryptography compilation

#### Breaking
- `python >=3.14,<3.15` — Python 3.13 no longer supported
- aiogram pinned to 3.27.0 (caps at Python <3.15)

#### Migration Notes
- Recreate virtualenv: `poetry env use python3.14 && poetry install`
- Rebuild all Docker images: `docker compose build --no-cache nginx && docker compose up -d --build bot api worker_critical worker_background worker_game`

### S-29: Placement Counter-Offer Fix (v4.7 — April 2026)

#### Fixed
- **Counter-offer price not applied via API** — `advertiser_accept_counter()` now passes `final_price=placement.counter_price` to repository `accept()` method. API path now matches Telegram bot behavior. (`src/core/services/placement_request_service.py`)
- **Missing counter-offer fields in API response** — `PlacementResponse` schema now includes `counter_price`, `counter_schedule`, `counter_comment`, `advertiser_counter_price`, `advertiser_counter_schedule`, `advertiser_counter_comment`. Frontend can now display full negotiation data. (`src/api/routers/placements.py`)
- **Broken callback in counter-counter notification** — Owner notification button now uses correct `own:request:{id}` callback instead of non-existent `req:view:{id}`. (`src/bot/handlers/advertiser/campaigns.py`)
- **Data collision in counter-offer price field** — Added separate `advertiser_counter_price`, `advertiser_counter_schedule`, `advertiser_counter_comment` fields to prevent advertiser's counter-counter from overwriting owner's counter-offer. (`src/db/models/placement_request.py`)

#### Added
- **Database migration** — `0002_add_advertiser_counter_fields.py` adds 3 new columns for advertiser's counter-offers. (`src/db/migrations/versions/`)
- **Comprehensive test coverage** — 9 new tests covering counter-offer service logic, API responses, data integrity, and price resolution. (`tests/test_counter_offer_flow.py`)
- **TypeScript type updates** — `PlacementRequest` interface updated in both mini_app and web_portal with advertiser counter-offer fields. (`mini_app/src/lib/types.ts`, `web_portal/src/lib/types.ts`)

#### Migration Notes
- Run `alembic upgrade head` to apply new migration
- To rollback: `alembic downgrade -1`

### S-32: Role Unification (v4.7 — April 2026)

#### Removed
- **`User.current_role`** — DB column removed from `users` table; no more role switching between "advertiser" and "owner"
- **`role` field from API responses** — `GET /api/auth/me`, `GET /api/admin/users`, `PATCH /api/admin/users/{id}` no longer include `role`
- **`role` query param** — `GET /api/placements/` no longer accepts `role`; now returns UNION of advertiser + owner placements
- **Bot "Выбрать роль" button** — replaced with direct 📣 Рекламодатель / 📺 Владелец navigation buttons in main menu
- **Mini App `/role` route** — RoleSelect screen deleted
- **`UserResponse.role`** — removed from both Mini App and Web Portal auth types

#### Changed
- **Bot main menu** — direct navigation: [👤 Кабинет | 📣 Рекламодатель | 📺 Владелец | 💬 Помощь | ✉️ Обратная связь]
- **Bot cabinet** — always shows both topup and payout buttons (payout gated by `earned_rub >= 1000` only)
- **Bot middleware** — always checks BOTH advertiser and owner block status (no role gating)
- **Placements API** — `list_placements()` unions `get_by_advertiser()` + `get_by_owner()` with dedup, sorted by `created_at DESC`
- **Admin user table** — "Роль" column replaced with "Тариф"
- **`UserRoleService`** — rewritten as minimal stub; removed all `current_role` references

#### Added
- **Context-based navigation** — route determines context (`/adv/*` = advertiser, `/own/*` = owner), not stored field

#### Migration Notes
- `current_role` column removed from `0001_initial_schema.py` in-place (pre-production strategy)
- To apply: reset DB and run `alembic upgrade head`

### S-29E: Fix Channel Name Bug (v4.6 — April 2026)

#### Fixed
- **"@#1" on My Campaigns** — added `channel: ChannelRef | None` to `PlacementResponse` schema and `selectinload` in repository queries. Now channel username is returned by API. (`src/api/routers/placements.py`, `src/db/repositories/placement_request_repo.py`, `mini_app/src/lib/types.ts`)

### S-29D: Mini App Channels Layout Fix (v4.6 — April 2026)

#### Changed
- **OwnChannels screen** — wrapped all content in shared `.container` to align "Add" button, channel cards, and warning banners to the same width (`mini_app/src/screens/owner/OwnChannels.tsx`, `.module.css`)
- **ChannelCard layout** — extracted status pill + chevron into `.actions` container with `margin-left: auto`, preventing them from competing with channel name for space (`mini_app/src/components/ui/ChannelCard.tsx`, `.module.css`)

### S-29B: Sidebar Icon-Only Collapsed State (v4.6 — April 2026)

#### Added
- **3-state sidebar** (`open` / `collapsed` / `closed`) in web_portal — collapsed mode shows 64px icon rail with all navigation tool icons visible
- **Tooltips on collapsed nav buttons** — native `title` attribute shows label when sidebar is collapsed
- **Compact user footer** in collapsed mode — avatar + logout only, avatar shows tooltip with user info

#### Changed
- **`usePortalUiStore`** — replaced `sidebarOpen: boolean` with `sidebarMode: 'open' | 'collapsed' | 'closed'`, added `openSidebar()`, `collapseSidebar()`, `closeSidebar()`, `toggleSidebar(isDesktop)` (`web_portal/src/stores/portalUiStore.ts`)
- **`PortalShell.tsx`** — conditional rendering for 3 states: width transitions, label hide/show, icon centering, header button icon swap (`web_portal/src/components/layout/PortalShell.tsx`)
- **Desktop default** — sidebar now defaults to `collapsed` (icon rail) instead of fully open

### S-29C: DAL Cleanup + Referral + Platform Credit + Security (v4.6 — April 2026)

#### Added
- **Admin Platform Credit:** `POST /api/admin/credits/platform-credit` — deduct from `PlatformAccount.profit_accumulated`, credit to `user.balance_rub` with `TransactionType.admin_credit` (`src/api/routers/admin.py`, `src/core/services/billing_service.py`)
- **Admin Gamification Bonus:** `POST /api/admin/credits/gamification-bonus` — deduct from platform balance, credit `balance_rub` + `advertiser_xp` with `TransactionType.gamification_bonus`
- **Referral Topup Bonus:** one-time 10% bonus to referrer on invitee's first qualifying topup (≥500₽), idempotent via `Transaction.meta_json` (`src/constants/payments.py`, `src/core/services/billing_service.py`, `src/bot/handlers/shared/start.py`, `src/db/repositories/user_repo.py`)
- **ReputationHistoryRepository:** `get_by_user_id()`, `add_batch()` (`src/db/repositories/reputation_history_repo.py`)
- **ChannelMediakitRepo:** `get_by_channel_id()`, `update_metrics()` (`src/db/repositories/channel_mediakit_repo.py`)
- **YookassaPaymentRepository:** `get_by_payment_id()` — wired in billing webhook (`src/db/repositories/yookassa_payment_repo.py`)
- **New repository methods:** `UserRepository.count_referrals()`, `get_referrals()`, `count_active_referrals()`, `sum_referral_earnings()`, `has_successful_payment()`, `get_by_referral_code()`; `TransactionRepository.sum_by_user_and_type()`, `list_by_user_id()`; `PlacementRequestRepository.has_active_placements()`, `count_published_by_channel()`; `TelegramChatRepository.count_active_by_owner()`; `DisputeRepository.get_all_paginated()`; `FeedbackRepository.get_by_id_with_user()`, `list_all_paginated()`, `respond()`, `update_status_only()`

#### Changed
- **DAL boundary enforcement:** 43 `session.execute()` calls in handlers/routers replaced with repository wiring across 12 files (`src/bot/handlers/dispute/dispute.py`, `channel_owner.py`, `cabinet.py`, `contract_signing.py`, `src/api/routers/users.py`, `billing.py`, `acts.py`, `ord.py`, `feedback.py`, `disputes.py`, `document_validation.py`)
- **`mediakit_service.py`:** wired `ChannelMediakitRepo` for reads
- **Bot singleton:** module-level `bot: Bot | None` in `src/bot/main.py`; `get_bot()` singleton + `close_bot()` in `src/api/dependencies.py` (fixes 8 mypy errors)

#### Removed
- **6 dead repository files** (zero callers in src/mini_app/web_portal/tests): `badge_repo.py`, `campaign_repo.py`, `click_tracking_repo.py`, `mailing_log_repo.py`, `platform_revenue_repo.py`, `yookassa_payment_repo.py` (original)
- **`TransactionType` enum:** removed `admin_credit`/`gamification_bonus` duplicate placeholders (added properly in this release)

#### Fixed
- **B311:** `random.randint` → `secrets.randbelow()` in `/login` auth code generation (`src/bot/handlers/shared/login_code.py`)
- **B104:** `0.0.0.0` hardcoded bind → empty string + explicit IP validation in YooKassa webhook (`src/api/routers/billing.py`)
- **B101:** removed `assert` type guards → proper `User | None` annotations (`src/core/services/billing_service.py`)
- **mypy union-attr:** `isinstance(Message)` guards before `edit_reply_markup()` (`src/bot/handlers/admin/monitoring.py`)
- **mypy:** 31 → 0 errors (dead repos + type annotations + bot singleton)
- **bandit:** 7 → 0 issues identified

### S-29B: Telegram Proxy Hotfix (v4.5 — April 2026)

#### Fixed
- **Hotfix:** `/api/channels/check` 500 + bot crash-loop — Docker containers can't reach `api.telegram.org` (firewall). Configured SOCKS5 proxy (`socks5://172.18.0.1:1080`) via xray + socat relay for both aiogram bot and python-telegram-bot API client
- **Bot:** `RuntimeError: no running event loop` — deferred `Bot` creation to async `_create_bot()` in `main()`; `AiohttpSession(proxy=...)` now configured inside event loop
- **API:** `get_bot()` singleton uses `HTTPXRequest(proxy=...)` (verified working)
- **Dependency:** `httpx` → `httpx[socks]` (adds `socksio` for SOCKS5 support)

### S-29A: Hotfixes (v4.5 — April 2026)

#### Fixed
- **Hotfix:** `GET /api/channels` 500 — added missing `last_avg_views`, `last_post_frequency`, `price_per_post` columns to `telegram_chats` DB table; patched `0001_initial_schema.py` (`src/db/migrations/versions/0001_initial_schema.py`)
- **D-02 (CRITICAL):** `PLAN_PRICES` key `'agency'` → `'business'` — prevents `KeyError` when accessing by `UserPlan.BUSINESS.value` (`src/constants/payments.py`)
- **D-08:** `ai_included` in `/api/billing/balance` now uses `PLAN_LIMITS` — Pro: 5→20 AI/month, Business: 20→-1 (unlimited) (`src/api/routers/billing.py`)
- **D-07:** Removed dead `GET /api/billing/invoice/{invoice_id}` endpoint (always returned 404) + `InvoiceStatusResponse` model (`src/api/routers/billing.py`)
- **D-09:** Export `LegalProfileStates`, `ContractSigningStates`, `AdminFeedbackStates` from `src/bot/states/__init__.py`
- **D-11:** Added `'background'` queue to `TASK_ROUTES` and `QUEUE_CONFIG` for ORD task routing (`src/tasks/celery_config.py`)
- **D-06:** Removed `check_pending_invoices` from Celery Beat schedule, marked task as deprecated (`src/tasks/celery_app.py`, `src/tasks/billing_tasks.py`)

#### Removed
- **D-15:** `STARS_ENABLED=true` from `.env.example` (Telegram Stars removed in v4.2)
- **D-16:** Legacy constants: `CURRENCIES`, `CRYPTO_CURRENCIES`, `PAYMENT_METHODS`, `YOOKASSA_PACKAGES` from `src/constants/payments.py` and re-exports from `src/constants/__init__.py`
- Duplicate `CURRENCIES` constant from `src/api/routers/billing.py`

#### Docs
- Added `docs/AAA-11_PRODUCTION_FIX_PLAN.md` — deep-dive investigation of 22 discrepancies + 4-sprint fix plan

### Added
- **GlitchTip → Qwen → Telegram pipeline:** Automated error analysis — GlitchTip webhooks trigger Celery task → Qwen Code CLI subprocess analysis → formatted Telegram notification to admin with inline buttons (traceback/ack/ignore). Replaces file-based `/tmp/glitchtip_queue/` + `analyze_error.sh` cron (`src/api/routers/webhooks.py`, `src/core/services/qwen_service.py`, `src/tasks/monitoring_tasks.py`, `src/bot/handlers/admin/monitoring.py`)
- `src/core/services/qwen_service.py`: Qwen Code error analysis service — async subprocess (`echo <prompt> | qwen`), structured response parsing (ROOT_CAUSE, SEVERITY, AFFECTED_FILES, FIX), 120s timeout, graceful degradation
- `src/tasks/monitoring_tasks.py`: Celery task `monitoring:analyze_glitchtip_error` (queue: `worker_critical`, max_retries=2) — traceback extraction from GlitchTip JSON, Qwen analysis, `/tmp/gt_cache/` persistence, Telegram bot notification
- `src/bot/handlers/admin/monitoring.py`: aiogram callback handlers — `gt:traceback:{id}`, `gt:ack:{id}`, `gt:ignore:{id}`
- Discovery report: `reports/docs-architect/discovery/CHANGES_2026-04-10_glitchtip-qwen-telegram.md`

### S-29B: Medium Priority (v4.5 — April 2026)

#### Fixed
- **D-12:** Implemented `COOLDOWN_HOURS` (24h) enforcement in `PayoutService.create_payout()` — prevents rapid payout abuse (`src/core/services/payout_service.py`)
- **D-12:** Added `PayoutRepository.get_last_completed_for_owner()` — queries last `paid` payout for cooldown check (`src/db/repositories/payout_repo.py`)
- **D-03:** Added `placement:check_escrow_stuck` Celery task — detects escrow placements with `scheduled_delete_at` >48h past, marks `meta_json` for admin alert (`src/tasks/placement_tasks.py`)
- **D-03:** Added Beat schedule entry `placement-check-escrow-stuck` (every 30min) (`src/tasks/celery_config.py`)
- **D-10:** Added async Redis client (`redis.asyncio.Redis`) in `placement_tasks.py` — sync client retained only for Celery dedup (runs in sync context)

#### Docs
- Updated `docs/AAA-11_PRODUCTION_FIX_PLAN.md` — verified D-06, D-07 existence, corrected severity assessments

### S-29C: Quality Sprint (v4.5 — April 2026)

#### Changed
- **BREAKING:** `POST /webhooks/glitchtip-alert` response changed from `{"ok": true}` to `{"status": "queued"}` — file-based queue replaced by Celery `.delay()` (`src/api/routers/webhooks.py`)
- **D-05:** Added explicit `queue=QUEUE_WORKER_CRITICAL` to all 10 placement task decorators — defense-in-depth beyond TASK_ROUTES (`src/tasks/placement_tasks.py`)
- **D-22:** Updated QWEN.md admin endpoint count 9 → 11 (documentation accuracy)

#### Verified
- **TD-04/D-21:** Both `mini_app` and `web_portal` already on TypeScript 6.0.2 — no action needed

### S-29D: Deferred Items (v4.5 — April 2026)

#### Fixed
- **D-01:** Fixed `legal_profiles.user_id` type `BigInteger` → `Integer` + migration `d01fix_user_id`
- **D-14:** Created 8 missing repository classes: `CampaignRepository`, `BadgeRepository`, `YookassaPaymentRepository`, `ClickTrackingRepository`, `KudirRecordRepository`, `DocumentUploadRepository`, `MailingLogRepository`, `PlatformQuarterlyRevenueRepository`
- **D-18:** Added `ON DELETE SET NULL` to self-referencing FKs (`users.referred_by_id`, `transactions.reverses_transaction_id`) + migration `d18cascade_selfref`

### AAA P4-P5: Code Quality + Security (v4.5 — April 2026)

#### Changed
- **P4:** Fixed 10 nested ternary expressions across 9 TSX files — extracted lookup maps and helper functions
- **P4:** Changed 3 `any` types to `unknown` in analytics components
- **P5:** Added security headers middleware to FastAPI (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `HSTS`, `Cache-Control: no-store`)

### Fixed
- **CRITICAL:** Aligned worker queues with TASK_ROUTES — `worker_critical` now listens to `worker_critical` and `placement` queues, `worker_background` listens to `background` queue. Previously placement and ORD tasks had routing mismatches (`docker-compose.yml`)
- **CRITICAL:** Bot startup now retries with exponential backoff (3→6→12→24→48s, max 5 attempts) instead of crashing on Telegram API timeout. Added explicit `bot.session.close()` in finally block to prevent aiohttp session leak (`src/bot/main.py`)
- **CRITICAL:** Nginx no longer fails with `host not found in upstream "flower:5555"` during startup — added `flower` to nginx `depends_on` list (`docker-compose.yml`)
- **HIGH:** Sentry SDK now has `shutdown_timeout=2` and `debug=False` — prevents blocking exit and verbose retry logging (`src/bot/main.py`)
- **MEDIUM:** Changed bot `ParseMode.MARKDOWN` → `ParseMode.HTML` (per QWEN.md axioms)
- **HIGH:** Added `placement:check_escrow_sla` Celery Beat task — detects and auto-refunds placements stuck in escrow past scheduled time (`src/tasks/placement_tasks.py`, `src/tasks/celery_config.py`)
- **HIGH:** Channel owner now receives notification when placement is paid and scheduled (`src/bot/handlers/placement/placement.py`)
- `placement:schedule_placement_publication` now handles NULL `scheduled_iso` parameter (defaults to now + 5 min)

### Changed
- Consolidated `src/tasks/publication_tasks.py` into `src/tasks/placement_tasks.py` — single source of truth for all placement Celery tasks
- Task prefix renamed: `publication:*` → `placement:*` (delete_published_post, check_scheduled_deletions)
- Celery Beat schedule updated: `placement-check-scheduled-deletions` added, legacy `publication:check_scheduled_deletions` removed
- `src/tasks/celery_app.py`: Beat registration updated to use `placement:` prefix

### Removed
- File-based GlitchTip queue (`/tmp/glitchtip_queue/`) — replaced by Celery `analyze_glitchtip_error.delay()` (`src/api/routers/webhooks.py`)
- Unused imports from webhooks.py: `json`, `pathlib`, `aiofiles`
- `src/tasks/publication_tasks.py` — merged into `placement_tasks.py`, no external imports existed

### Added
- chore: track `reports/docs-architect/discovery/` in remote repo — reworked `.gitignore` negation chain so all `CHANGES_*.md` discovery files are versioned and shareable (`.gitignore`)
- chore: add `CLAUDE.md` to version control — no secrets present, enables repo-level AI assistant config for all contributors (`CLAUDE.md`, `.gitignore`)
- `landing/src/context/ThemeContext.tsx`: ThemeProvider + useTheme hook — dark mode toggle with localStorage persistence
- Dark mode for landing page: full `dark:` variant support across all components (Hero, Features, HowItWorks, Tariffs, Compliance, FAQ, Header, Footer)
- `landing/public/favicon.svg`: SVG-логотип RH (32×32, brand-blue #1456f0)
- `landing/public/assets/og-cover.png`: OG-обложка 1200×630px, генерируется скриптом `scripts/generate-og.ts` через ImageMagick
- ~~`landing/public/load-fonts.js`~~: удалён — заменён прямым `<link rel="stylesheet">` в index.html
- `landing/scripts/generate-og.ts`: скрипт генерации OG-обложки (SVG + ImageMagick → PNG, graceful fallback)
- `@lhci/cli` в prodакшне: Lighthouse CI проходит (Perf ≥90 opt, A11y 96, BP 100, SEO 100)
- `landing/lighthouserc.cjs`: переименован из `.js` для совместимости с `"type": "module"`

### Changed
- `src/constants/payments.py`: Removed `CREDIT_PACKAGES`, `CREDIT_PACKAGE_STANDARD`, `CREDIT_PACKAGE_BUSINESS`
- `src/constants/tariffs.py`: Removed `TARIFF_CREDIT_COST`
- `src/constants/__init__.py`: Removed all credit-related re-exports
- `src/config/settings.py`: Removed `credits_per_rub_for_plan`
- `src/db/migrations/versions/s33a001_merge_credits_to_balance_rub.py`: NEW — merge credits→balance_rub, DROP COLUMN credits
- `tests/conftest.py`: Fixtures `credits`→`balance_rub`
- `tests/unit/test_start_and_role.py`: Mock fixtures updated
- `tests/unit/test_review_service.py`: DB fixtures `credits`→`balance_rub`
- `tests/unit/test_escrow_payouts.py`: All credits references updated
- `tests/mocks/yookassa_mock.py`: Metadata `credits`→`amount_rub`
- `tests/smoke_yookassa.py`: All credit assertions removed/updated
- `mini_app/src/api/billing.ts`: Removed `TopupPackage`, `packages`, `credits_buy`; `BuyCreditsResponse` simplified
- `mini_app/src/api/analytics.ts`: `AnalyticsSummary.credits`→`balance_rub`
- `mini_app/src/screens/common/Cabinet.tsx`: Removed credits converter UI
- `mini_app/src/screens/common/Plans.tsx`: `user.credits`→`user.balance_rub`
- `mini_app/src/screens/common/Referral.tsx`: `total_earned_credits`→`total_earned_rub`
- `mini_app/src/screens/common/TransactionHistory.tsx`: Removed `credits_buy` entry
- `mini_app/src/screens/admin/AdminUserDetail.tsx`: "Кредиты"→"Баланс ₽"
- `mini_app/src/hooks/queries/useBillingQueries.ts`: Toast text updated
- `web_portal/src/api/billing.ts`: `getBalance()` removed `credits`
- `web_portal/src/stores/authStore.ts`: `User` type removed `credits`
- `web_portal/src/screens/common/Cabinet.tsx`: Removed credits converter UI
- `web_portal/src/screens/shared/Plans.tsx`: `user.credits`→`user.balance_rub`
- `web_portal/src/screens/common/Referral.tsx`: `total_earned_credits`→`total_earned_rub`
- `web_portal/src/screens/common/TransactionHistory.tsx`: Removed `credits_buy` entry
- `web_portal/src/screens/admin/AdminUserDetail.tsx`: "Кредиты"→"Баланс ₽"
- `src/bot/handlers/billing/billing.py`: Removed `credits` param from `yookassa_service.create_payment()`
- `src/bot/handlers/shared/notifications.py`: `format_yookassa_payment_success` simplified — text "Зачислено кредитов" → "Баланс: N ₽"
- `src/api/routers/billing.py`: Removed `CREDIT_PACKAGES`; `BalanceResponse.credits`→`balance_rub`; `/credits` simplified; `change_plan` uses `update_balance_rub`
- `src/api/routers/auth.py`: Removed `credits` from `AuthResponse` schema
- `src/api/routers/users.py`: Removed `credits` from `UserProfile`; `total_earned_credits`→`total_earned_rub` (Decimal)
- `src/api/routers/admin.py`: Removed `credits` from all user response constructions
- `src/api/routers/analytics.py`: `SummaryResponse.credits`→`balance_rub`
- `src/api/routers/placements.py`: Balance check uses `balance_rub`, error "Insufficient credits"→"Insufficient balance"
- `src/api/routers/auth_login_code.py`, `auth_login_widget.py`: Response `"credits"`→`"balance_rub"`
- `src/api/schemas/admin.py`: `UserAdminResponse.credits` removed
- `src/tasks/billing_tasks.py`: Plan renewal uses `balance_rub` instead of `credits`; `_PLAN_COSTS` from settings
- `src/tasks/notification_tasks.py`: `_notify_low_balance` uses `balance_rub: Decimal`, text "N кр" → "N ₽"
- `src/tasks/gamification_tasks.py`: `update_credits()` → `update_balance_rub(Decimal("50"))`
- `src/db/repositories/user_repo.py`: `update_credits()` → `update_balance_rub()` (Decimal)
- `src/core/services/billing_service.py`: 6 methods converted from `credits` → `balance_rub` (plan activation, escrow freeze/refund, campaign funds, deduct, referral bonus, payment crediting)
- `src/core/services/yookassa_service.py`: `create_payment()` removed `credits` param; `_credit_user()` uses `balance_rub`
- `src/core/services/badge_service.py`: Badge reward `credits` → `balance_rub` (Decimal)
- `src/core/services/xp_service.py`: Streak bonuses `credits` → `balance_rub` (Decimal)
- `landing/package.json` prebuild: добавлен `tsx scripts/generate-og.ts` — sitemap + og-cover генерируются при каждой сборке
- `landing/src/lib/constants.ts`: TARIFFS prices corrected 299→490, 990→1490, 2999→4990; removed `priceCredits` and `CREDITS_PER_RUB` (single currency: ₽)
- `landing/src/components/Tariffs.tsx`: text changed from "1 кредит = 1 ₽" to "Оплата в рублях"
- `src/tasks/notification_tasks.py`: `_RENEWAL_COSTS` corrected 299→490, 999→1490, 2999→4990; notification text uses ₽ instead of кр
- `src/bot/handlers/billing/billing.py`: `_PLAN_PRICES` now references `settings.tariff_cost_*` instead of hardcoded values
- `mini_app/src/screens/common/Plans.tsx`: low-balance threshold 299→500; "Кредиты" → "Баланс", "кр/мес" → "₽/мес"
- `web_portal/src/screens/shared/Plans.tsx`: low-balance threshold 299→500; "Кредиты" → "Баланс", "кредитов/мес" → "₽/мес"
- `landing/index.html`: Google Fonts через прямой `<link rel="stylesheet">` (удалён load-fonts.js + noscript обёртка)
- `landing/src/index.css`: добавлена `@source "./**/*.{ts,tsx}"` — явное указание Tailwind v4 сканировать src/
- `landing/src/index.css`: `--color-text-muted` #8e8e93 → #767676 (WCAG AA 4.54:1, было 3.19:1)
- `landing/src/components/FAQ.tsx`: кнопки аккордеона получили `min-h-[48px]` (target-size ≥48px)
- `nginx/conf.d/security_headers_landing.conf` CSP: добавлены `https://fonts.googleapis.com` в `style-src` и `connect-src`
- Production: Docker-nginx пересобран с builder-landing stage, задеплоен на `rekharbor.ru` и `portal.rekharbor.ru`

### Fixed
- `landing/src/components/FAQ.tsx`: outer container `max-w-3xl` → `max-w-7xl` — унифицирована ширина всех секций
- `landing/src/index.css`: удалён `*, *::before, *::after { margin: 0; padding: 0 }` — дублирующий сброс переопределял Tailwind utility-классы (`mx-auto`, `px-*`, `py-*`)
- `landing/src/components/Hero.tsx`, `Header.tsx`, `Footer.tsx`: переписаны на чистые Tailwind utility-классы — устранено смешивание `style={{}}` inline и Tailwind, вызывавшее потерю цветовых утилит (`bg-gray-*`, `text-blue-*`, `shadow-sm/md`) из собранного CSS
- `web_portal/src/lib/types.ts`: `DisputeStatus` исправлен (`owner_explained`/`closed` вместо `rejected`/`pending`); `placement_request_id` вместо `placement_id`
- `web_portal/src/hooks/useDisputeQueries.ts`: удалён неиспользуемый импорт `getMyDisputes` (TS6133)
- `web_portal/src/screens/owner/DisputeResponse.tsx`: StatusPill variant `'info'`→`'warning'`, `'neutral'`→`'default'`
- `web_portal/src/screens/shared/MyDisputes.tsx`: `DISPUTE_REASON_LABELS` инлайн; `owner_explanation`→`owner_comment`
- `web_portal/src/screens/shared/DisputeDetail.tsx`: `placement_id`→`placement_request_id`
- `mini_app/src/hooks/queries/useDisputeQueries.ts`: `getMyDisputes().then(r=>r.items)` → `getMyDisputes()` (API возвращает `Dispute[]` напрямую)
- `mini_app/src/screens/advertiser/disputes/DisputeDetail.tsx`: `RESOLUTION_PILL` дополнен `owner_fault`, `advertiser_fault`, `technical`, `partial`
- `mini_app/src/screens/shared/MyDisputes.tsx`: удалены неиспользуемые импорты, `haptic.light()`→`haptic.tap()`, убраны несуществующие props `title` и `clickable`

- ESLint 9 flat config (`landing/eslint.config.js`): TypeScript + React + jsx-a11y rules, 0 errors
- `landing/Features`: 6 карточек фич платформы (эскроу, ОРД/erid, AI-генерация, репутация, мониторинг, торг) с stagger-анимацией при входе в viewport
- `landing/HowItWorks`: двухрежимный флоу (Рекламодатель / Владелец канала) с pill-переключателем и AnimatePresence
- `landing/Tariffs`: 4 тарифных карточки из `constants.ts`, карточка Pro выделена, комиссия рендерится динамически
- `landing/Compliance`: 4 блока (ОРД/erid, 152-ФЗ, эскроу-схема, система репутации) на реальных данных платформы
- `landing/FAQ`: аккордеон (один открытый за раз) + динамический FAQPage JSON-LD в `<head>` через useEffect
- `landing/Privacy`: полная страница 152-ФЗ с реквизитами ООО «АЛГОРИТМИК АРТС», правами пользователя, cookie, третьими лицами (ОРД/YooKassa)
- `nginx/conf.d/security_headers_landing.conf`: строгий CSP для лендинга (no unsafe-inline/eval)
- `docker/Dockerfile.nginx`: Этап 3 builder-landing + baked-in SSL certs через `ssl_certs/`
- `portal.rekharbor.ru`: новый server block, портал с API/Flower/webhooks
- `ssl_certs/`: директория для baked-in SSL сертификатов (обновляется при certbot renew)
- INSTRUCTIONS.md — developer instructions with critical documentation rule, agent routing, skills system
- Documentation cross-reference system: QWEN.md ↔ INSTRUCTIONS.md ↔ CHANGELOG.md ↔ README.md
- `landing/Header`: sticky с backdrop-blur, ScrollSpy nav pills, mobile hamburger drawer (motion/react)
- `landing/Hero`: H1 Outfit clamp(2.5rem,6vw,5rem), motion stagger-анимация, stats-плитки, prefers-reduced-motion
- `landing/Footer`: multi-column тёмный, реквизиты ООО «АЛГОРИТМИК АРТС», 152-ФЗ ссылки /privacy
- `landing/CookieBanner`: 152-ФЗ consent banner, localStorage persistence, AnimatePresence
- `landing/useScrollSpy`: хук активной секции по scroll event
- `landing/useConsent`: хук управления cookie-согласием (pending/accepted/declined)
- Landing page scaffold at `landing/` (Phase 1): React 19, TS 6.0.2, Vite 8, Tailwind 4.1
- `landing/src/lib/constants.ts`: tariff constants synced with backend (`tariffs.py`)
- `landing/index.html`: full SEO setup (5 JSON-LD types: WebSite/Organization/Service/BreadcrumbList + FAQPage, OG, Twitter Card)
- `landing/scripts/generate-sitemap.ts`: prebuild sitemap generator → `public/sitemap.xml`
- `landing/lighthouserc.js`: Lighthouse CI gates (Performance ≥90, SEO 100, A11y ≥95)
- `landing/Dockerfile`: multi-stage nginx build (node:22-alpine builder + nginx:1.27-alpine serve)
- `landing/nginx.conf`: gzip, immutable cache headers, SPA fallback
- Claude Code self-configuration: `.claude/settings.json` hooks (PostToolUse ESLint, Stop warning, PreToolUse force-push guard)

### Changed
- `rekharbor.ru`: переключён с web portal на лендинг (статика /usr/share/nginx/html/landing)
- `portal.rekharbor.ru`: web portal перенесён с rekharbor.ru
- `/etc/nginx/sites-enabled/rekharbor.ru` (host-level): добавлен portal.rekharbor.ru в server_name
- `docker-compose.yml`: убран /etc/letsencrypt bind mount из nginx (certs baked into image)
- README.md: restructured from 1242 → 373 lines (70% reduction), removed duplicate sections, file trees, DB schemas

### Fixed
- Redis AOF corruption after `systemctl restart docker`: removed corrupt .incr.aof, rebuilt manifest
- Docker bind-mount SSL caching: certs now baked into image instead of bind mount
- ` @vitejs/plugin-react` bumped ^4→^6 (v4 lacks Vite 8 peer dep support)
- `vite.config.ts` manualChunks converted Object→Function (rolldown/Vite 8 requirement)
- `landing/src/vite-env.d.ts` added (TS 6.0.2 requires vite/client ref for CSS side-effect imports)

### mini_app — TypeScript 6.0 + TailwindCSS 4.1 Alignment
- TypeScript: ^5.9.3 → ^6.0.2 (aligned with web_portal)
- Added TailwindCSS ^4.1.0 + @tailwindcss/vite ^4.1.0 (greenfield integration, not migration)
- typescript-eslint: ^8.56.1 → ^8.58.0 (TS 6.0 peer dependency compatibility)
- tsconfig.app.json: target ES2023 → ES2025 (aligned with TS 6.0 default + web_portal)
- tsconfig.node.json: added `rootDir: "./"` (TS 6.0 rootDir default shift safeguard)
- vite.config.ts: added @tailwindcss/vite plugin integration
- src/styles/globals.css: added ` @import 'tailwindcss';` directive
- Verified: 0 tsc errors, 0 build warnings, 0 eslint warnings

### Removed
- `landing/Dockerfile`: удалён — лендинг не является отдельным Docker-сервисом
- `landing/nginx.conf`: удалён — nginx конфиг лендинга встроен в проектный Dockerfile.nginx

### Breaking
- YooKassa webhook: обновить URL в ЛК YooKassa: `portal.rekharbor.ru/webhooks/yookassa`
- FastAPI ALLOWED_ORIGINS: добавить `https://portal.rekharbor.ru`
- Bot ссылки: обновить `rekharbor.ru` → `portal.rekharbor.ru` для web portal

## [v4.4] - 2026-04-08

### Added
- Rate limiting (10/hour) to `/api/auth/login-code` — brute-force protection
- Shared `RedisClient` dependency with connection pooling in `dependencies.py`
- CORS restrict methods/headers configuration
- `# noqa: S1172` to 6 stub methods in `stub_ord_provider.py` (protocol implementation)
- `# noqa: F401,F403,S2208` to Alembic `env.py` wildcard import (standard pattern)
- SonarQube config expanded: src + mini_app + web_portal (580 files scanned)
- Migration `t1u2v3w4x5y6` — added missing `language_code` column to `users` table

### Changed
- Billing prices: 299/999/2999 → 490/1490/4990 (from settings, not hardcoded)
- Redis connection: per-request pool → shared pool in dependencies.py
- Webhook error handling: bare except Exception → specific exceptions + retry
- SonarQube config: mini_app only → src + mini_app + web_portal

### Fixed
- Telegram widget 500 error: column language_code missing (migration t1u2v3w4x5y6)
- **billing.py** hardcoded prices (299/999/2999 → 490/1490/4990 from settings)
- Redis connection leak in login-code (per-request `aclose()` → shared connection pool)
- **is_active** check added to Login Widget auth — banned users cannot obtain JWT
- **AdminDashboard.tsx** — table missing `<thead>`/`<th scope="row">` for accessibility (S5256)
- 9× keyboard listener issues (S1082) — added `onKeyDown`, `tabIndex`, `role="button"`:
  - `Modal.tsx`, `Checkbox.tsx`, `ChannelCard.tsx`, `OwnChannels.tsx`, `ContractList.tsx`,
    `DocumentUpload.tsx`, `AdminDisputesList.tsx`, `PortalShell.tsx`
- **LegalProfileSetup.tsx** redundant ternary (S3923) — simplified 4-branch to 3-branch
- 6× unused parameters in notification wrappers — prefixed with `_` (S1172)
- 4× commented-out dead code (S125) removed from payout_service.py, billing_service.py, audit_log.py

### Code Quality
- Backend: ~70 issues fixed (unused params, dead code, noqa annotations)
- Frontend: 204 SonarQube issues identified, 11 BUG issues fixed
- Identified remaining: 75× nested ternary (S3358), 40× missing form labels (S6853), 75× `<div onClick>` → `<button>` (S7773)

### Migration Notes
```bash
alembic upgrade head
ruff check src/ --fix && ruff format src/
mypy src/ --ignore-missing-imports
```

## [v4.3.1] - 2026-04-02

### Documentation
- Updated README.md with v4.3 features (legal profiles, ORD, audit, referrals)
- Updated QWEN.md with new database models and environment variables
- Added "Что нового в v4.3" section to README.md
- Updated Tech Stack section (GlitchTip, SonarQube, Gitleaks)
- Updated Project Structure (20+ new models, services, routers)

## [v4.3] - 2026-03-14

### Added
- Feedback system: full user → admin → response flow
- Admin panel Mini App: 7 screens, 9 endpoints
- Legal profiles: LegalProfile + Contract models
- ORD registration: OrdRegistration for advertising compliance
- Audit log: AuditLog + Audit Middleware for security tracking
- Field encryption: PII encryption for sensitive data
- Referral program: ReferralStats tracking
- Video support: VideoUploader in campaigns
- Link tracking: ClickTracking for campaign links
- GlitchTip + SonarQube + Gitleaks integration
- 101 tests (all passing)
- 20+ documentation reports

### Changed
- Payouts: CryptoBot API → manual via admin panel
- B2B packages: removed
- ESCROW-001: release_escrow() ONLY after post deletion (not on publication)
- FSM States: 5 files + 2 middleware completed
- Ruff SIM102/SIM103: fixed
- is_banned: replaced with is_active
- Admin panel 404: added is_admin check in dependencies.py

### Removed
- CryptoBot service (manual payouts only)
- B2B button in main_menu
- NPD_TAX_RATE (replaced with PLATFORM_TAX_RATE)
- Bonus packages

### Breaking
- Payout workflow now manual (no CryptoBot automation)
- ESCROW release timing changed (after deletion, not publication)

### Migration Notes
```bash
alembic upgrade head
ruff check src/ --fix && ruff format src/
pytest tests/ -v
```

## [v4.2] - 2026-03-18

### Changed
- PLATFORM_COMMISSION: 0.20 → 0.15
- OWNER_SHARE: 0.80 → 0.85
- Tariff prices: 299/999/2999 → 490/1490/4990
- MIN_TOPUP: 100 → 500
- MIN_PRICE_PER_POST: 100 → 1000
- MIN_PAYOUT: 500 → 1000
- Added MIN_CAMPAIGN_BUDGET: 2000

### Added
- 5 publication formats with multipliers
- Self-dealing prevention in placement requests
- Velocity check for payouts (MVP)
- PayoutRequest: gross/fee/net breakdown
- Platform tax rate: 6% (USN)
- Payout fee rate: 1.5%

### Removed
- NPD_TAX_RATE (replaced with PLATFORM_TAX_RATE)
- Bonus packages

### Migration Notes
```bash
alembic upgrade head
ruff check src/ --fix && ruff format src/
```
