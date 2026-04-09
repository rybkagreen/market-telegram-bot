# Phase 1: Discovery & Mapping — File Inventory

> **Generated:** 2026-04-08  
> **Project:** RekHarborBot (Telegram advertising marketplace)  
> **Version:** v4.3+ (post-S-29)  
> **Python:** 3.13 | **aiogram:** 3.x | **FastAPI** | **SQLAlchemy 2.0 async** | **Celery + Redis**

---

## 1. Backend Python Modules (`src/`)

### 1.1 Core Application Layer

| File | Purpose | LOC (est.) | Priority |
|------|---------|-----------|----------|
| `src/__init__.py` | Package init | ~5 | LOW |
| `src/config/settings.py` | Pydantic Settings — ALL env vars, tariff limits, ORD, mailing, AI | ~280 | **HIGH** |
| `src/config/__init__.py` | Package init | ~3 | LOW |

### 1.2 Bot Layer (`src/bot/`)

| File | Purpose | Priority |
|------|---------|----------|
| `src/bot/main.py` | Bot entry — Dispatcher, middlewares, main_router, Sentry init, MenuButton | **HIGH** |
| `src/bot/__init__.py` | Package init | LOW |

#### Handlers (30 files)

| File | Role | Priority |
|------|------|----------|
| `src/bot/handlers/__init__.py` | Main router — includes all 16 sub-routers | **HIGH** |
| `src/bot/handlers/shared/start.py` | /start, onboarding, role selection | **HIGH** |
| `src/bot/handlers/shared/cabinet.py` | Cabinet menu (advertiser/owner) | **HIGH** |
| `src/bot/handlers/shared/feedback.py` | User feedback submission | HIGH |
| `src/bot/handlers/shared/help.py` | /help command | MED |
| `src/bot/handlers/shared/legal_profile.py` | Legal profile setup (FSM) | HIGH |
| `src/bot/handlers/shared/contract_signing.py` | Contract signing flow | HIGH |
| `src/bot/handlers/shared/login_code.py` | Login code flow (S-29) | HIGH |
| `src/bot/handlers/shared/notifications.py` | Notification handlers | MED |
| `src/bot/handlers/advertiser/campaigns.py` | Campaign management (create, list) | **HIGH** |
| `src/bot/handlers/advertiser/analytics.py` | Advertiser analytics view | MED |
| `src/bot/handlers/advertiser/__init__.py` | Advertiser router aggregator | MED |
| `src/bot/handlers/owner/channel_owner.py` | Channel adding flow | **HIGH** |
| `src/bot/handlers/owner/channel_settings.py` | Channel price, formats, mediakit | **HIGH** |
| `src/bot/handlers/owner/analytics.py` | Owner analytics | MED |
| `src/bot/handlers/owner/arbitration.py` | Arbitration/dispute handling | HIGH |
| `src/bot/handlers/owner/__init__.py` | Owner router aggregator | MED |
| `src/bot/handlers/billing/billing.py` | Topup flow, plan purchase | **HIGH** |
| `src/bot/handlers/billing/__init__.py` | Billing router init | MED |
| `src/bot/handlers/placement/placement.py` | Placement wizard (accept/counter/reject) | **HIGH** |
| `src/bot/handlers/placement/__init__.py` | Placement router init | MED |
| `src/bot/handlers/payout/payout.py` | Payout request flow | HIGH |
| `src/bot/handlers/payout/__init__.py` | Payout router init | MED |
| `src/bot/handlers/dispute/dispute.py` | Dispute flow (owner/advertiser) | HIGH |
| `src/bot/handlers/dispute/__init__.py` | Dispute router init | MED |
| `src/bot/handlers/admin/users.py` | Admin user management | HIGH |
| `src/bot/handlers/admin/disputes.py` | Admin dispute resolution | HIGH |
| `src/bot/handlers/admin/feedback.py` | Admin feedback handling | HIGH |
| `src/bot/handlers/admin/__init__.py` | Admin router aggregator | MED |

#### FSM States (12 files)

| File | StatesGroup | Priority |
|------|-------------|----------|
| `src/bot/states/__init__.py` | Exports 8 state groups | **HIGH** |
| `src/bot/states/billing.py` | `TopupStates` (3 states) | **HIGH** |
| `src/bot/states/placement.py` | `PlacementStates` (6 states) | **HIGH** |
| `src/bot/states/payout.py` | `PayoutStates` | HIGH |
| `src/bot/states/channel_owner.py` | `AddChannelStates` | HIGH |
| `src/bot/states/channel_settings.py` | `ChannelSettingsStates` | HIGH |
| `src/bot/states/feedback.py` | `FeedbackStates` | HIGH |
| `src/bot/states/dispute.py` | `DisputeStates` | HIGH |
| `src/bot/states/arbitration.py` | `ArbitrationStates` | HIGH |
| `src/bot/states/contract_signing.py` | Contract signing states | HIGH |
| `src/bot/states/legal_profile.py` | Legal profile states | HIGH |
| `src/bot/states/admin_feedback.py` | Admin feedback states | MED |

**Note:** `states/__init__.py` does NOT export `ContractSigningStates`, `LegalProfileStates`, or `AdminFeedbackStates` — potential inconsistency.

#### Keyboards (22 files)

| Category | Files | Purpose |
|----------|-------|---------|
| `shared/` | `main_menu.py`, `common.py`, `cabinet.py`, `contract.py`, `legal_profile.py` | Universal keyboards |
| `advertiser/` | `adv_menu.py`, `my_campaigns.py`, `placement.py` | Advertiser-specific |
| `owner/` | `own_menu.py`, `channels.py`, `requests.py` | Owner-specific |
| `billing/` | `topup.py`, `plans.py` | Payment UI |
| `payout/` | `payout.py` | Payout UI |
| `admin/` | `admin.py` | Admin panel |

#### Bot Middlewares (5 files)

| File | Purpose | Priority |
|------|---------|----------|
| `src/bot/middlewares/db_session.py` | Inject DB session into handlers | **HIGH** |
| `src/bot/middlewares/throttling.py` | Rate limiting per user | HIGH |
| `src/bot/middlewares/role_check.py` | Role-based access (advertiser/owner/admin) | **HIGH** |
| `src/bot/middlewares/fsm_timeout.py` | FSM timeout cleanup | HIGH |
| `src/bot/middlewares/__init__.py` | Empty | LOW |

#### Bot Utils

| File | Purpose |
|------|---------|
| `src/bot/utils/` | Empty directory (no files) |
| `src/bot/filters/` | Empty directory (no files) |

### 1.3 API Layer (`src/api/`)

| File | Purpose | Priority |
|------|---------|----------|
| `src/api/main.py` | FastAPI app — 27 routers, CORS, middleware, Sentry, ORD provider injection, exception handlers, rate limiter | **HIGH** |
| `src/api/dependencies.py` | JWT auth (`get_current_user`, `get_current_admin_user`), DB session, Redis, Bot factory | **HIGH** |
| `src/api/auth_utils.py` | JWT encode/decode utilities | **HIGH** |
| `src/api/__init__.py` | Package init | LOW |

#### API Routers (28 files)

| File | Prefix | Tags | Priority |
|------|--------|------|----------|
| `auth.py` | `/api/auth` | Auth | **HIGH** |
| `auth_login_code.py` | `/api/auth` | Auth (S-29) | HIGH |
| `auth_login_widget.py` | `/api/auth` | Auth (S-27) | HIGH |
| `users.py` | `/api/users` | Users | **HIGH** |
| `campaigns.py` | `/api/campaigns` | Campaigns | **HIGH** |
| `analytics.py` | `/api/analytics` | Analytics | HIGH |
| `billing.py` | `/api/billing` | Billing | **HIGH** |
| `channels.py` | `/api/channels` | Channels | HIGH |
| `channel_settings.py` | `/api/channel-settings` | Channel Settings | HIGH |
| `placements.py` | `/api/placements` | Placements | **HIGH** |
| `payouts.py` | `/api/payouts` | Payouts | HIGH |
| `disputes.py` | `/api/disputes` | Disputes | HIGH |
| `feedback.py` | `/api/feedback` | Feedback | HIGH |
| `admin.py` | `/api` | Admin | **HIGH** |
| `legal_profile.py` | none (root) | Legal Profile | HIGH |
| `contracts.py` | none | Contracts | HIGH |
| `acts.py` | none | Acts (S-26) | HIGH |
| `ord.py` | none | ORD | HIGH |
| `ai.py` | `/api/ai` | AI | MED |
| `reputation.py` | `/api/reputation` | Reputation | MED |
| `reviews.py` | `/api/reviews` | Reviews | MED |
| `categories.py` | `/api/categories` | Categories | MED |
| `uploads.py` | `/api/uploads` | Uploads | HIGH |
| `webhooks.py` | none | Webhooks (YooKassa) | **HIGH** |
| `health.py` | none | Health | LOW |
| `document_validation.py` | none | Document Validation | HIGH |
| `__init__.py` | — | Package init | LOW |

#### API Middleware

| File | Purpose |
|------|---------|
| `audit_middleware.py` | Audit logging for sensitive routes (/legal-profile, /contracts, /ord) |
| `log_sanitizer.py` | PII sanitization for validation errors + Sentry scrubbing |

#### API Schemas

| Directory | Purpose |
|-----------|---------|
| `src/api/schemas/` | Pydantic schemas for API request/response validation |

### 1.4 Database Layer (`src/db/`)

#### Models (32 files)

| File | Model(s) | Priority |
|------|----------|----------|
| `user.py` | `User`, `UserPlan` enum | **HIGH** |
| `placement_request.py` | `PlacementRequest`, `PlacementStatus`, `PublicationFormat` | **HIGH** |
| `payout.py` | `PayoutRequest`, `PayoutStatus` | **HIGH** |
| `platform_account.py` | `PlatformAccount` (singleton id=1, encrypted fields) | **HIGH** |
| `transaction.py` | `Transaction`, `TransactionType` enum | **HIGH** |
| `campaign.py` | `Campaign`, `CampaignStatus` | **HIGH** |
| `channel_settings.py` | `ChannelSettings` (format flags, price_per_post) | **HIGH** |
| `channel_mediakit.py` | `ChannelMediakit` | HIGH |
| `telegram_chat.py` | `TelegramChat` | **HIGH** |
| `legal_profile.py` | `LegalProfile`, `LegalStatus`, `TaxRegime` | HIGH |
| `contract.py` | `Contract`, `ContractType`, `ContractStatus` | HIGH |
| `contract_signature.py` | `ContractSignature`, `SignatureMethod` | HIGH |
| `ord_registration.py` | `OrdRegistration`, `OrdStatus` | HIGH |
| `audit_log.py` | `AuditLog` | HIGH |
| `publication_log.py` | `PublicationLog` | HIGH |
| `feedback.py` | `UserFeedback`, `FeedbackStatus` | HIGH |
| `dispute.py` | `PlacementDispute`, `DisputeReason`, `DisputeStatus`, `DisputeResolution` | HIGH |
| `review.py` | `Review` | MED |
| `reputation_score.py` | `ReputationScore` | MED |
| `reputation_history.py` | `ReputationHistory`, `ReputationAction` | MED |
| `badge.py` | `UserBadge` | MED |
| `invoice.py` | `Invoice` | HIGH |
| `yookassa_payment.py` | `YookassaPayment` | **HIGH** |
| `act.py` | `Act` | HIGH |
| `category.py` | `Category` | MED |
| `click_tracking.py` | `ClickTracking` | HIGH |
| `document_counter.py` | `DocumentCounter` | MED |
| `document_upload.py` | `DocumentUpload` | HIGH |
| `kudir_record.py` | `KudirRecord` | MED |
| `platform_quarterly_revenue.py` | `PlatformQuarterlyRevenue` | MED |
| `mailing_log.py` | `MailingLog`, `MailingStatus` | MED |
| `__init__.py` | Exports all 32 models | **HIGH** |

#### Repositories (24 files)

| File | Model | Priority |
|------|-------|----------|
| `user_repo.py` | User | **HIGH** |
| `placement_request_repo.py` | PlacementRequest | **HIGH** |
| `payout_repo.py` | PayoutRequest | HIGH |
| `platform_account_repo.py` | PlatformAccount | **HIGH** |
| `transaction_repo.py` | Transaction | **HIGH** |
| `channel_settings_repo.py` | ChannelSettings | HIGH |
| `contract_repo.py` | Contract | HIGH |
| `legal_profile_repo.py` | LegalProfile | HIGH |
| `ord_registration_repo.py` | OrdRegistration | HIGH |
| `dispute_repo.py` | Dispute | HIGH |
| `feedback_repo.py` | Feedback | HIGH |
| `invoice_repo.py` | Invoice | HIGH |
| `publication_log_repo.py` | PublicationLog | MED |
| `reputation_repo.py` | Reputation | MED |
| `review_repo.py` | Review | MED |
| `category_repo.py` | Category | MED |
| `telegram_chat_repo.py` | TelegramChat | HIGH |
| `audit_log_repo.py` | AuditLog | MED |
| `act_repo.py` | Act | MED |
| `tax_repo.py` | Tax records | MED |
| `document_counter_repo.py` | DocumentCounter | MED |
| `base.py` | BaseRepository (CRUD generics) | **HIGH** |
| `__init__.py` | Exports | LOW |

#### Migrations (33 files)

| Migration | Description | Priority |
|-----------|-------------|----------|
| `a86e3ba47c30_initial_schema_v4_3.py` | Initial v4.3 schema | **HIGH** |
| `f3a2b1c0d9e8_add_legal_profiles_contracts_ord_video.py` | Legal/ORD/Video | HIGH |
| `s26a001_add_accounting_and_acts.py` | Accounting (S-26) | HIGH |
| `s26a002_enrich_yk_and_payout_fix.py` | YK + payout fixes | HIGH |
| `s26a003_add_tx_accounting_and_tax.py` | Tax accounting | HIGH |
| `s26b001_add_kudir_index.py` | Kudir | MED |
| `s26b002_ndfl_npd_encryption.py` | NDFL/NPD encryption | HIGH |
| `s26c001_vat_invoice_calendar.py` | VAT/Invoice | HIGH |
| `s26d001_ooo_usn_15_support.py` | OOO USN 15% | MED |
| `s26d002_storno_and_expense_integration.py` | Storno | MED |
| `s26e001_add_document_links.py` | Document links | MED |
| `s26f001_act_signing_flow.py` | Act signing | HIGH |
| `s28a001_add_yandex_ord_fields.py` | Yandex ORD | HIGH |
| `s31a001_document_uploads.py` | Document uploads | HIGH |
| `p1q2r3s4t5u6_add_badge_tables_and_streak_fields.py` | Badges/streaks | MED |
| `h2i3j4k5l6m7_add_publication_log.py` | Publication log | HIGH |
| `g1h2i3j4k5l6_add_escrow_transaction_id.py` | Escrow TX | **HIGH** |
| `6a62b060752f_add_user_feedback_table.py` | Feedback | HIGH |
| `a1b2c3d4e5f6_add_missing_transaction_types.py` | TX types | HIGH |
| +14 others | Various schema patches | MED |

#### DB Session & Base

| File | Purpose |
|------|---------|
| `src/db/base.py` | `Base` (DeclarativeBase), `TimestampMixin` |
| `src/db/session.py` | `async_session_factory`, `celery_async_session_factory`, connection pool config |
| `src/db/seed.py` | Seed data |
| `src/db/seed_badges.py` | Badge seed data |

### 1.5 Core Services (`src/core/services/` — 34 files)

| File | Purpose | Priority |
|------|---------|----------|
| `billing_service.py` | Topup, escrow freeze/release, plan activation, referral bonuses | **HIGH** |
| `payout_service.py` | Payout creation, velocity check, manual admin processing | **HIGH** |
| `placement_request_service.py` | Self-dealing check, format validation, price calculation | **HIGH** |
| `publication_service.py` | Telegram publish, pin, delete, ESCROW-001 release | **HIGH** |
| `yookassa_service.py` | YooKassa SDK integration | **HIGH** |
| `notification_service.py` | Telegram notifications | HIGH |
| `mistral_ai_service.py` | Mistral AI SDK (content generation) | HIGH |
| `user_role_service.py` | Role management (advertiser/owner/both) | HIGH |
| `xp_service.py` | XP/level system (DO NOT MODIFY) | **PROTECTED** |
| `reputation_service.py` | Reputation scoring | HIGH |
| `review_service.py` | Review system | MED |
| `channel_service.py` | Channel management | HIGH |
| `analytics_service.py` | Analytics calculations | HIGH |
| `badge_service.py` | Badge awarding | MED |
| `legal_profile_service.py` | Legal profile management | HIGH |
| `contract_service.py` | Contract generation (PDF via ReportLab) | HIGH |
| `act_service.py` | Act generation | HIGH |
| `invoice_service.py` | Invoice management | HIGH |
| `ord_service.py` | ORD registration orchestrator | HIGH |
| `ord_provider.py` | ORD provider interface | HIGH |
| `stub_ord_provider.py` | Stub ORD implementation | MED |
| `yandex_ord_provider.py` | Yandex ORD implementation | HIGH |
| `link_tracking_service.py` | Click tracking URL generation | HIGH |
| `mediakit_service.py` | Mediakit management | HIGH |
| `comparison_service.py` | Channel comparison | LOW |
| `document_number_service.py` | Document numbering | MED |
| `document_validation_service.py` | Document validation | HIGH |
| `edo_provider.py` | EDO (electronic document) interface | MED |
| `stub_edo_provider.py` | Stub EDO | MED |
| `kudir_export_service.py` | KUDIR export (S-26) | MED |
| `tax_aggregation_service.py` | Tax aggregation (S-26) | HIGH |
| `fns_validation_service.py` | FNS tax validation | HIGH |

### 1.6 Constants (`src/constants/` — 9 files)

| File | Purpose | Priority |
|------|---------|----------|
| `payments.py` | Financial constants: commission rates, min amounts, format multipliers, plan limits | **HIGH** |
| `tariffs.py` | Thin wrapper → settings.py (legacy, marked for deletion) | MED |
| `ai.py` | AI model config | MED |
| `content_filter.py` | Content filter keywords/thresholds | MED |
| `expense_categories.py` | Expense categories (S-26) | MED |
| `legal.py` | Legal constants | MED |
| `parser.py` | Parser settings | MED |

### 1.7 Celery Tasks (`src/tasks/` — 16 files)

| File | Queues | Priority |
|------|--------|----------|
| `celery_app.py` | App creation, Beat schedule, BaseTask, register_task decorator | **HIGH** |
| `celery_config.py` | Celery config | MED |
| `publication_tasks.py` | `critical` queue — publish/delete placement, scheduled deletions | **HIGH** |
| `parser_tasks.py` | `parser` queue — 7 category slots, stats collection | HIGH |
| `billing_tasks.py` | `billing` queue — plan renewals, pending invoice checks | **HIGH** |
| `notification_tasks.py` | `mailing`/`notifications` queue | HIGH |
| `placement_tasks.py` | Placement processing | HIGH |
| `ord_tasks.py` | ORD registration tasks | HIGH |
| `cleanup_tasks.py` | `cleanup` queue — log cleanup | MED |
| `gamification_tasks.py` | `gamification` queue | MED |
| `badge_tasks.py` | `badges` queue | MED |
| `document_ocr_tasks.py` | OCR processing (PyMuPDF + Tesseract) | HIGH |
| `integrity_tasks.py` | Data integrity checks | MED |
| `tax_tasks.py` | Tax calculations (S-26) | HIGH |

### 1.8 Security (`src/core/security/`)

| File | Purpose |
|------|---------|
| `field_encryption.py` | `EncryptedString`, `HashableEncryptedString` — Fernet-based PII encryption |

### 1.9 Utils (`src/utils/`)

| File | Purpose |
|------|---------|
| `categories.py` | Category helpers |
| `mediakit_pdf.py` | Mediakit PDF generation |
| `pdf_report.py` | PDF report generation |
| `utils/content_filter/` | Content filter implementation |
| `utils/telegram/` | Telegram-specific utilities |

### 1.10 Templates (`src/templates/`)

| Directory | Purpose |
|-----------|---------|
| `contracts/` | Contract Jinja2 templates |
| `acts/` | Act templates |
| `invoices/` | Invoice templates |
| `kudir/` | KUDIR record templates |

---

## 2. Frontend Applications

### 2.1 Mini App (`mini_app/`)

| Path | Purpose |
|------|---------|
| `mini_app/src/App.tsx` | Root component |
| `mini_app/src/main.tsx` | Entry point |
| `mini_app/src/screens/admin/` | 7 admin screens (v4.3) |
| `mini_app/src/screens/advertiser/` | Advertiser screens |
| `mini_app/src/screens/owner/` | Owner screens |
| `mini_app/src/screens/common/` | Shared screens |
| `mini_app/src/api/` | API client layer |
| `mini_app/src/hooks/` | React hooks |
| `mini_app/src/stores/` | State stores |
| `mini_app/src/lib/` | Utilities, constants |
| `mini_app/src/components/` | UI components |
| `mini_app/src/styles/` | CSS modules |
| `mini_app/vite.config.ts` | Vite config |
| `mini_app/package.json` | Dependencies (React 19.2.4, TS 5.9) |

### 2.2 Web Portal (`web_portal/`)

| Path | Purpose |
|------|---------|
| `web_portal/src/App.tsx` | Root component |
| `web_portal/src/screens/` | Portal screens |
| `web_portal/src/api/` | API client |
| `web_portal/src/shared/` | Shared components (separate from mini_app) |
| `web_portal/src/hooks/` | React hooks |
| `web_portal/src/stores/` | State stores |
| `web_portal/src/lib/` | Utilities, constants |
| `web_portal/src/components/` | UI components |
| `web_portal/src/styles/` | Tailwind v4 @theme styles |
| `web_portal/vite.config.ts` | Vite config |
| `web_portal/package.json` | Dependencies |

---

## 3. Infrastructure & Config

| File | Purpose | Priority |
|------|---------|----------|
| `docker-compose.yml` | 11 services: postgres, redis, bot, 3 workers, beat, flower, api, nginx, glitchtip + worker | **HIGH** |
| `docker/Dockerfile.bot` | Bot container | HIGH |
| `docker/Dockerfile.api` | API container | HIGH |
| `docker/Dockerfile.worker` | Worker container | HIGH |
| `docker/Dockerfile.nginx` | Nginx + Mini App build | HIGH |
| `alembic.ini` | Alembic config (migrations path: `src/db/migrations`) | **HIGH** |
| `alembic.docker.ini` | Docker-specific Alembic config | HIGH |
| `alembic_sync.ini` | Sync Alembic config | MED |
| `run_migrations.py` | Migration runner script | HIGH |
| `pyproject.toml` | Poetry deps, Ruff/MyPy/Pytest config | **HIGH** |
| `Makefile` | Dev commands | MED |
| `.env.example` | All required env vars | **HIGH** |
| `sonar-project.properties` | SonarQube config | MED |
| `.gitleaks.toml` | Gitleaks secret scanning | MED |
| `.pre-commit-config.yaml` | Pre-commit hooks | MED |
| `.github/` | CI/CD workflows | HIGH |

---

## 4. Test Suite

| File | Type | Priority |
|------|------|----------|
| `tests/conftest.py` | Pytest fixtures | **HIGH** |
| `tests/unit/test_billing.py` | Billing service unit tests | **HIGH** |
| `tests/unit/test_escrow_payouts.py` | Escrow + payout tests | **HIGH** |
| `tests/unit/test_placement.py` | Placement service tests | **HIGH** |
| `tests/unit/test_fsm_middlewares.py` | FSM + middleware tests | HIGH |
| `tests/unit/test_content_filter.py` | Content filter tests | MED |
| `tests/unit/test_gamification.py` | Gamification tests | MED |
| `tests/unit/test_ai_service.py` | AI service tests | MED |
| `tests/unit/test_start_and_role.py` | Start/role flow tests | HIGH |
| `tests/unit/test_payments_constants.py` | Payment constant tests | HIGH |
| `tests/unit/test_placement_notifications.py` | Notification tests | MED |
| `tests/unit/test_review_service.py` | Review service tests | LOW |
| `tests/unit/test_sender.py` | Sender tests | LOW |
| `tests/unit/test_bmediakit_comparison.py` | Mediakit tests | LOW |
| `tests/integration/test_api_endpoints.py` | API integration tests | HIGH |
| `tests/integration/test_web_portal.sh` | Web portal smoke test | MED |
| `tests/test_billing_service.py` | Root-level billing test | HIGH |
| `tests/test_payout_service.py` | Root-level payout test | HIGH |
| `tests/test_placement_request_service.py` | Root-level placement test | HIGH |
| `tests/test_publication_service.py` | Root-level publication test | HIGH |
| `tests/test_constants.py` | Constants validation | HIGH |
| `tests/test_channel_settings_repo.py` | Channel settings repo test | MED |
| `tests/test_placement_request_repo.py` | Placement repo test | MED |
| `tests/test_reputation_service.py` | Reputation service test | MED |
| `tests/test_api_channel_settings.py` | Channel settings API test | MED |
| `tests/test_api_placements.py` | Placements API test | MED |
| `tests/smoke_yookassa.py` | YooKassa smoke test | HIGH |

**Total test files:** 27 (claims 101 tests in QWEN.md)

---

## 5. Documentation (`docs/`)

| File | Purpose |
|------|---------|
| `DOCUMENT_AUTOMATION_SPEC_v1.md` | 2084-line automation spec |
| `DEPLOYMENT.md` | Deployment guide |
| `DEPLOYMENT_CHECKLIST_S26.md` | S-26 deployment checklist |
| `DOCKER_README.md` | Docker setup |
| `CHANGELOG.md` | Version history |
| `CONSTANTS_AUDIT.md` | Constants audit report |
| `SENTRY_SETUP.md` | Sentry/GlitchTip setup |
| `TEST_MODE_GUIDE.md` | Test mode guide |
| `S-26_ACCOUNTING & TAX COMPLIANCE.md` | S-26 accounting spec |
| `cleanup_production_db.sql` | DB cleanup script |
| `api_admin_contracts_example.md` | Admin contracts API example |
| `docs/code_review/` | Code review reports |
| `docs/project_context_update/` | Context updates |

---

## 6. Reports (`reports/`)

Existing report directories:
- `reports/docs-architect/discovery/` ← This report
- `reports/monitoring/` — Error reports, payload queue, dir snapshot
- `reports/s-27-web-portal/` — S-27 sprint reports

---

*End of File Inventory | 🔍 Verified against: filesystem scan 2026-04-08 | ✅ Validation: passed*
