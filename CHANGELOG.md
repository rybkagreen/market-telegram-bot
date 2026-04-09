# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### S-29A: Hotfixes (v4.5 — April 2026)

#### Fixed
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
- **D-05:** Added explicit `queue=QUEUE_WORKER_CRITICAL` to all 10 placement task decorators — defense-in-depth beyond TASK_ROUTES (`src/tasks/placement_tasks.py`)
- **D-22:** Updated QWEN.md admin endpoint count 9 → 11 (documentation accuracy)

#### Verified
- **TD-04/D-21:** Both `mini_app` and `web_portal` already on TypeScript 6.0.2 — no action needed

### Fixed
- **CRITICAL:** `camp_pay_balance` handler now schedules Celery publication task after payment — fixes stalled escrow placements that never got published (`src/bot/handlers/placement/placement.py`)
- **HIGH:** Added `placement:check_escrow_sla` Celery Beat task — detects and auto-refunds placements stuck in escrow past scheduled time (`src/tasks/placement_tasks.py`, `src/tasks/celery_config.py`)
- **HIGH:** Channel owner now receives notification when placement is paid and scheduled (`src/bot/handlers/placement/placement.py`)
- `placement:schedule_placement_publication` now handles NULL `scheduled_iso` parameter (defaults to now + 5 min)

### Changed
- Consolidated `src/tasks/publication_tasks.py` into `src/tasks/placement_tasks.py` — single source of truth for all placement Celery tasks
- Task prefix renamed: `publication:*` → `placement:*` (delete_published_post, check_scheduled_deletions)
- Celery Beat schedule updated: `placement-check-scheduled-deletions` added, legacy `publication:check_scheduled_deletions` removed
- `src/tasks/celery_app.py`: Beat registration updated to use `placement:` prefix

### Removed
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
