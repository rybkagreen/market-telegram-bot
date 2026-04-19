# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
