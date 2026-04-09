# Phase 1: Discovery & Mapping — Dependency Graph & Critical Path Analysis

> **Generated:** 2026-04-08  
> **Project:** RekHarborBot v4.3+

---

## 1. Architecture Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TELEGRAM CLIENTS                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Telegram    │  │  Telegram    │  │  Telegram    │              │
│  │  Bot API     │  │  User API    │  │  Mini App    │              │
│  │  (aiogram)   │  │  (Telethon)  │  │  (WebApp)    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
└─────────┼─────────────────┼──────────────────┼──────────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌──────────────────┐ ┌────────────┐  ┌──────────────────────────────┐
│   BOT LAYER      │ │  PARSER    │  │       API LAYER              │
│  (aiogram 3.x)   │ │ (Telethon) │  │      (FastAPI)               │
│                  │ │            │  │                               │
│  main.py ────────│─┤            │  │  main.py (27 routers)        │
│  ├── handlers/   │ │ tasks/     │  │  ├── auth/ (3 routers)       │
│  │   ├── shared/ │ │ parser_*   │  │  ├── billing                 │
│  │   ├── admin/  │ └────────────┘  │  ├── campaigns               │
│  │   ├── adv/    │                 │  ├── placements              │
│  │   ├── owner/  │                 │  ├── payouts                 │
│  │   ├── billing/│                 │  ├── legal_profile           │
│  │   ├── payout/ │                 │  ├── contracts               │
│  │   ├── placement/                │  ├── ord                     │
│  │   └── dispute/│                 │  ├── admin                   │
│  ├── keyboards/  │                 │  ├── feedback                │
│  ├── states/     │                 │  ├── webhooks (YooKassa)     │
│  ├── middlewares/│                 │  └── health                  │
│  └── utils/      │                 │                               │
└────────┬─────────┘                 └──────────┬───────────────────┘
         │                                      │
         │          ┌───────────────────────────┤
         │          ▼                           │
         │  ┌──────────────────────────────────┐│
         │  │     CORE SERVICES LAYER          ││
         │  │  ┌────────────────────────────┐ ││
         │  │  │  billing_service.py        │◄┘│
         │  │  │  payout_service.py         │  │
         │  │  │  placement_request_svc.py  │  │
         │  │  │  publication_service.py    │  │
         │  │  │  yookassa_service.py       │  │
         │  │  │  notification_service.py   │  │
         │  │  │  mistral_ai_service.py     │  │
         │  │  │  user_role_service.py      │  │
         │  │  │  xp_service.py (PROTECTED) │  │
         │  │  │  reputation_service.py     │  │
         │  │  │  legal_profile_service.py  │  │
         │  │  │  contract_service.py       │  │
         │  │  │  ord_service.py            │  │
         │  │  │  + 20 more services        │  │
         │  │  └────────────┬───────────────┘  │
         │  └───────────────┼──────────────────┘
         │                  │
         ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                               │
│  ┌─────────────────────────┐   ┌─────────────────────────────┐   │
│  │  Repositories (24)       │   │  Models (32)                │   │
│  │  user_repo.py            │   │  User, PlacementRequest,    │   │
│  │  placement_request_repo  │   │  PayoutRequest, Transaction │   │
│  │  payout_repo.py          │   │  PlatformAccount, Campaign  │   │
│  │  transaction_repo.py     │   │  ChannelSettings, etc.      │   │
│  │  + 20 more              │   │                              │   │
│  └───────────┬─────────────┘   └──────────────┬──────────────┘   │
└──────────────┼────────────────────────────────┼──────────────────┘
               │                                │
               ▼                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                               │
│  ┌───────────────────────┐    ┌──────────────────────────────┐   │
│  │  PostgreSQL 16        │    │  Redis 7                     │   │
│  │  (asyncpg)            │    │  FSM storage, Celery broker, │   │
│  │  ~32 tables           │    │  rate limiting, caching      │   │
│  └───────────────────────┘    └──────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    ASYNC TASK LAYER (Celery)                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  worker_critical: celery, mailing, notifications, billing   │ │
│  │  worker_background: parser, cleanup, rating                 │ │
│  │  worker_game: gamification, badges                          │ │
│  │  celery_beat: 7 parser slots + analytics + cleanup + billing│ │
│  │  flower: monitoring dashboard                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Text-Based Dependency Graph

### 2.1 Bot Layer Dependencies

```
src/bot/main.py
├── aiogram.Bot (settings.bot_token)
├── aiogram.Dispatcher (RedisStorage)
├── Middlewares (order matters!):
│   ├── DBSessionMiddleware     ← injects session into handler context
│   ├── ThrottlingMiddleware    ← rate limit per user
│   ├── RoleCheckMiddleware     ← validates user.current_role
│   └── FSMTimeoutMiddleware    ← cleans stale FSM states
└── main_router (src/bot/handlers/__init__.py)
    ├── start_router            → /start → creates User, sets role
    ├── login_code_router       → login code flow (S-29)
    ├── cabinet_router          → /cabinet → role-specific menu
    ├── help_router             → /help
    ├── feedback_router         → feedback submission
    ├── legal_profile_router    → legal profile FSM flow
    ├── contract_signing_router → contract signing FSM
    ├── billing_router          → topup, plan purchase
    ├── payout_router           → payout request flow
    ├── advertiser_analytics    → advertiser stats
    ├── campaigns_router        → campaign CRUD
    ├── placement_router        → placement wizard (accept/counter)
    ├── owner_analytics         → owner stats
    ├── channel_owner_router    → add channel flow
    ├── channel_settings_router → channel config (price, formats)
    ├── arbitration_router      → owner arbitration
    ├── dispute_router          → dispute flow
    ├── admin_router            → admin user management
    └── admin_disputes_router   → admin dispute resolution
```

### 2.2 API Layer Dependencies

```
src/api/main.py (FastAPI app)
├── AuditMiddleware              → logs access to /legal-profile, /contracts, /ord
├── CORSMiddleware               → origins: app.rekharbor.ru, rekharbor.ru, localhost:5173/5174
├── Rate Limiter (slowapi+Redis)
├── Routers (27):
│   /api/auth/*                  → auth.py, auth_login_code.py, auth_login_widget.py
│   /api/users                   → users.py
│   /api/campaigns               → campaigns.py
│   /api/analytics               → analytics.py
│   /api/billing                 → billing.py
│   /api/channels                → channels.py
│   /api/channel-settings        → channel_settings.py
│   /api/placements              → placements.py
│   /api/payouts                 → payouts.py
│   /api/disputes                → disputes.py
│   /api/feedback                → feedback.py
│   /api                         → admin.py (admin endpoints)
│   /api/ai                      → ai.py
│   /api/reputation              → reputation.py
│   /api/reviews                 → reviews.py
│   /api/categories              → categories.py
│   /api/uploads                 → uploads.py
│   (root)                       → legal_profile.py, contracts.py, acts.py
│   (root)                       → ord.py, webhooks.py, health.py, document_validation.py
├── dependencies.py:
│   ├── get_current_user()      → JWT decode → User lookup
│   ├── get_current_admin_user() → is_admin check
│   ├── get_db_session()         → async_session_factory
│   ├── get_redis()              → shared Redis pool
│   └── get_bot()                → Bot(token) for Telegram API calls
└── Exception handlers:
    ├── RekHarborError → 400
    ├── RequestValidationError → sanitized (PII scrubbed)
    └── RateLimitExceeded → 429
```

### 2.3 Database Model Dependencies

```
User (users)
├── → referred_by_id: FK → users.id (self-referral)
├── → telegram_chats: 1:N → TelegramChat
├── → placement_requests_advertiser: 1:N → PlacementRequest
├── → placement_requests_owner: 1:N → PlacementRequest
├── → transactions: 1:N → Transaction
├── → payout_requests: 1:N → PayoutRequest
├── → reputation_score: 1:1 → ReputationScore
├── → reputation_history: 1:N → ReputationHistory
├── → disputes_advertiser: 1:N → PlacementDispute
├── → disputes_owner: 1:N → PlacementDispute
├── → reviews_given/received: 1:N → Review
├── → badges: 1:N → UserBadge
├── → feedback_list: 1:N → UserFeedback
├── → legal_profile: 1:1 → LegalProfile
└── → invoices: 1:N → Invoice

TelegramChat (telegram_chats)
├── → owner_id: FK → users.id
├── → channel_settings: 1:1 → ChannelSettings
├── → channel_mediakit: 1:1 → ChannelMediakit
└── → placement_requests: 1:N → PlacementRequest

PlacementRequest (placement_requests)
├── → advertiser_id: FK → users.id
├── → owner_id: FK → users.id
├── → channel_id: FK → telegram_chats.id
├── → escrow_transaction_id: FK → transactions.id
├── → acts: 1:N → Act
├── → transactions: 1:N → Transaction
├── → reviews: 1:N → Review
├── → disputes: 1:N → PlacementDispute
├── → reputation_history: 1:N → ReputationHistory
├── → mailing_logs: 1:N → MailingLog
└── → click_tracking: 1:1 → ClickTracking

PlatformAccount (platform_account) — SINGLETON id=1
├── escrow_reserved: DECIMAL (SUM of escrow placements)
├── payout_reserved: DECIMAL (SUM of pending payouts)
├── profit_accumulated: DECIMAL (15% escrow + 1.5% payout fees)
├── total_topups: DECIMAL
├── total_payouts: DECIMAL
└── Encrypted fields: inn, bank_account, bank_corr_account

Transaction (transactions)
├── → user_id: FK → users.id
├── → placement_request_id: FK → placement_requests.id (nullable)
├── → payout_request_id: FK → payout_requests.id (nullable)
└── type: TransactionType enum (topup, spend, escrow_freeze, escrow_release, payout, payout_fee, etc.)

PayoutRequest (payout_requests)
├── → owner_id: FK → users.id
├── → admin_id: FK → users.id (nullable, processing admin)
├── → transactions: 1:N → Transaction
└── gross/fee/net amount fields + NDFL/NPD fields

LegalProfile (legal_profiles)
├── → user_id: FK → users.id (unique)
├── Encrypted: inn, kpp, company_name, full_name, passport_data, address, phone, email
└── → contracts: 1:N → Contract

Contract (contracts)
├── → user_id: FK → users.id
├── → legal_profile_id: FK → legal_profiles.id
├── → signatures: 1:N → ContractSignature
└── type/status enums

OrdRegistration (ord_registrations)
├── → campaign_id: FK → campaigns.id (unique)
└── status: pending → registered → token_received → reported / failed

AuditLog (audit_logs)
├── → user_id: FK → users.id
└── action/entity_type/old_values/new_values/inn_hash

ClickTracking (click_tracking)
├── → campaign_id: FK → campaigns.id
├── → placement_request_id: FK → placement_requests.id
└── tracking_url (unique UUID-based)
```

### 2.4 Service → Repository → Model Dependencies

```
BillingService
├── UserRepository → User (balance_rub, credits, plan)
├── TransactionRepository → Transaction (topup, spend, escrow_*)
├── PlatformAccountRepo → PlatformAccount (total_topups)
├── YooKassaPayment → YooKassaPayment
└── Uses: async_session_factory (NOT passed as arg — __init__ has no args)

PayoutService
├── UserRepository → User (earned_rub)
├── PayoutRepository → PayoutRequest (create, update status)
├── TransactionRepository → Transaction (payout, payout_fee)
├── PlatformAccountRepo → PlatformAccount (payout_reserved, profit)
└── Velocity check: queries transactions/payouts 30d window

PlacementRequestService
├── PlacementRequestRepository → PlacementRequest
├── ChannelSettingsRepository → ChannelSettings (price_per_post, format flags)
├── UserRepository → User (plan → format validation)
└── Self-dealing check: channel.owner_id vs advertiser_id

PublicationService
├── PlacementRequestRepository → PlacementRequest (status, message_id)
├── TransactionRepository → Transaction (escrow_release)
├── PlatformAccountRepo → PlatformAccount (profit_accumulated)
├── PublicationLog → PublicationLog
├── Bot (aiogram) → send_message, pin_chat_message, delete_message
└── Celery tasks: publish_placement, delete_published_post, check_scheduled_deletions

YooKassaService
├── YooKassa SDK (yookassa.Payment)
├── YookassaPayment → YookassaPayment
├── TransactionRepository → Transaction
└── Webhook handler → process_topup_webhook

ContractService
├── ContractRepository → Contract
├── LegalProfileRepository → LegalProfile
├── ContractSignature → ContractSignature
├── ReportLab → PDF generation
└── settings.contracts_storage_path → /data/contracts

LegalProfileService
├── LegalProfileRepository → LegalProfile
├── AuditLogRepository → AuditLog
├── FieldEncryption → encrypt/decrypt PII
└── FNS validation service

OrdService
├── OrdRegistrationRepository → OrdRegistration
├── OrdProvider (interface) → StubOrdProvider / YandexOrdProvider
└── PlacementRequest → erid field
```

### 2.5 Celery Task Queue Routing

```
Queue: critical (worker_critical, concurrency=2)
├── publication:publish_placement
├── publication:delete_published_post
├── publication:unpin_and_delete_post
└── publication:check_scheduled_deletions (Beat, every 5 min)

Queue: mailing (worker_critical)
└── mailing:send_campaign

Queue: notifications (worker_critical)
└── notification:send_*

Queue: billing (worker_critical, priority=9)
├── billing:check_plan_renewals (Beat, daily 03:00 UTC)
└── billing:check_pending_invoices (Beat, every 5 min)

Queue: parser (worker_background, concurrency=4)
├── parser:refresh_chat_database_business (Beat, 00:15 UTC)
├── parser:refresh_chat_database_marketing (Beat, 00:45 UTC)
├── parser:refresh_chat_database_it (Beat, 01:15 UTC)
├── parser:refresh_chat_database_lifestyle (Beat, 01:45 UTC)
├── parser:refresh_chat_database_health (Beat, 02:15 UTC)
├── parser:refresh_chat_database_education (Beat, 02:45 UTC)
├── parser:refresh_chat_database_news (Beat, 03:15 UTC)
└── parser:collect_all_chats_stats (Beat, 03:30 UTC)

Queue: cleanup (worker_background)
└── cleanup:delete_old_logs (Beat, Sunday 03:00 UTC)

Queue: rating (worker_background)
└── (reserved for future rating tasks)

Queue: gamification (worker_game, concurrency=2)
└── gamification:*

Queue: badges (worker_game)
└── badge:*

Queue: default (any worker)
├── placement:*
├── ord:*
├── document_ocr:*
├── integrity:*
└── tax:*
```

### 2.6 FSM State → Handler Mapping

```
TopupStates
├── entering_amount  → billing.py (amount input)
├── confirming       → billing.py (confirm desired/fee/gross)
└── waiting_payment  → billing.py (awaiting YooKassa webhook)

PlacementStates
├── selecting_category  → placement.py
├── selecting_channels  → placement.py
├── selecting_format    → placement.py
├── entering_text       → placement.py
├── arbitrating         → placement.py
├── waiting_response    → placement.py
└── upload_video        → placement.py (optional)

PayoutStates        → payout.py (entering_address, confirming)
AddChannelStates    → channel_owner.py (entering_username, confirming_add)
ChannelSettingsStates → channel_settings.py
FeedbackStates      → feedback.py (entering_text)
DisputeStates       → dispute.py (owner_explaining, advertiser_commenting, admin_reviewing)
ArbitrationStates   → arbitration.py (owner)
ContractSigningStates → contract_signing.py
LegalProfileStates  → legal_profile.py
AdminFeedbackStates → admin/feedback.py
```

---

## 3. Critical Path Analysis

### 3.1 Revenue Flow (Topup → Campaign → Placement → Payout)

```
1. USER TOPUP
   User → /topup → TopupStates → BillingService.create_payment()
   → YooKassaPayment created (pending)
   → YooKassa payment URL returned
   → User pays → YooKassa webhook → webhooks.py
   → BillingService.process_topup_webhook()
   → User.balance_rub += metadata["desired_balance"]  ← NOT gross_amount!
   → Transaction(topup) created
   → PlatformAccount.total_topups += desired_balance

2. CAMPAIGN CREATION
   Advertiser → /create_campaign → campaigns.py
   → Campaign created (draft)
   → PlacementRequest created (pending_owner)
   → Notification sent to channel owner

3. PLACEMENT APPROVAL
   Owner → accepts/counter-offers → placement.py
   → If counter: status=counter_offer → advertiser accepts → status=pending_payment
   → Self-dealing check: channel.owner_id != advertiser_id
   → Format validation: format in PLAN_LIMITS[user.plan]["formats"]
   → Price calculation: base_price × FORMAT_MULTIPLIERS[format]
   → Min budget check: final_price >= MIN_CAMPAIGN_BUDGET (2000)

4. ESCROW FREEZE
   BillingService.freeze_campaign_funds() or freeze_escrow()
   → SELECT FOR UPDATE User
   → assert user.balance_rub >= amount
   → user.balance_rub -= amount
   → PlatformAccount.escrow_reserved += amount
   → Transaction(escrow_freeze)
   → PlacementRequest.status = escrow

5. PUBLICATION
   Celery: publication:publish_placement
   → PublicationService.publish_placement()
   → Bot sends message to channel
   → Optional pin
   → PlacementRequest.status = published
   → message_id, published_at recorded
   → PublicationLog created

6. POST DELETION (ESCROW-001)
   Celery: publication:delete_published_post (scheduled or manual)
   → unpin → delete message
   → PlacementRequest.status = completed
   → ESCROW RELEASE:
     owner_amount = final_price × 0.85
     platform_fee = final_price × 0.15
     User.earned_rub += owner_amount
     PlatformAccount.profit_accumulated += platform_fee
     PlatformAccount.escrow_reserved -= final_price
     Transaction(escrow_release)

7. PAYOUT
   Owner → /payouts → PayoutStates → PayoutService.create_payout()
   → Velocity check: (payouts_30d + requested) / topups_30d <= 0.80
   → fee = gross × 0.015
   → net = gross - fee
   → User.earned_rub -= gross
   → PlatformAccount.payout_reserved += gross
   → PlatformAccount.profit_accumulated += fee
   → Transaction(payout_fee, fee)
   → PayoutRequest(status=pending)
   → Admin approves manually → status=paid
   → PlatformAccount.payout_reserved -= gross
   → PlatformAccount.total_payouts += net
```

### 3.2 Authentication Flow (Mini App)

```
Mini App → Login → /api/auth/login_code (S-29) or /api/auth/login_widget (S-27)
→ JWT generated (HS256, 24h expiry)
→ JWT stored in Mini App
→ Subsequent API calls: Authorization: Bearer <JWT>
→ get_current_user() dependency:
   → decode_jwt_token() → payload["sub"] = user_id
   → DB lookup: User.id == user_id (with legal_profile preload)
   → Check user.is_active (NOT is_banned!)
   → Return User or 401
→ Admin endpoints: get_current_admin_user() → check user.is_admin → 403 if not
```

### 3.3 Legal Compliance Flow (v4.3)

```
User → legal_profile setup → LegalProfileStates
→ LegalProfile created (PII encrypted via FieldEncryption)
→ AuditLog created (action=CREATE, entity=legal_profile, inn_hash recorded)
→ Contract generated (PDF via ReportLab)
→ ContractSignature (button_accept or sms_code)
→ OrdRegistration → ORD provider (stub/yandex) → erid token
→ PlacementRequest.erid = token
→ Publication blocked if ORD_BLOCK_WITHOUT_ERID=true and erid is null
```

---

## 4. Documentation Priority List

### HIGH Priority (must document first)

| # | Topic | Files | AAA Doc |
|---|-------|-------|---------|
| H1 | Financial model (escrow, commissions, payouts) | billing_service, payout_service, payments.py, platform_account | 04-business-logic |
| H2 | FSM state machines + handler routing | states/, handlers/, middlewares/ | 05-bot-fsm |
| H3 | Database models + relationships | models/ (32 files) | 03-database |
| H4 | API contract (FastAPI routers + auth) | api/routers/, dependencies.py | 06-api-miniapp |
| H5 | Celery tasks + queue routing | tasks/ (16 files), celery_app.py | 07-celery-tasks |
| H6 | Deployment + Docker Compose | docker-compose.yml, Dockerfiles, .env | 08-deployment-ops |

### MEDIUM Priority

| # | Topic | Files | AAA Doc |
|---|-------|-------|---------|
| M1 | Content filter system | content_filter/, utils/content_filter/ | 04-business-logic |
| M2 | Reputation vs XP systems | reputation_service, xp_service | 04-business-logic |
| M3 | Legal profiles + contracts + ORD | legal_profile, contract, ord models + services | 04-business-logic |
| M4 | Mini App frontend architecture | mini_app/src/ | 06-api-miniapp |
| M5 | Testing strategy + coverage | tests/, conftest.py | 09-testing-quality |
| M6 | Web Portal architecture | web_portal/src/ | 06-api-miniapp |
| M7 | Document management (S-26: acts, invoices, KUDIR, tax) | act, invoice, kudir, tax models + services | 04-business-logic |

### LOW Priority

| # | Topic | Files | AAA Doc |
|---|-------|-------|---------|
| L1 | Gamification (XP, levels, badges) | xp_service, badge_*, gamification_tasks | 04-business-logic |
| L2 | Parser (Telethon channel scraping) | parser_tasks, Telethon session | 07-celery-tasks |
| L3 | AI content generation | mistral_ai_service | 04-business-logic |
| L4 | Referral program | billing_service referral methods | 04-business-logic |
| L5 | Mediakit system | channel_mediakit, mediakit_service | 04-business-logic |
| L6 | Click tracking | click_tracking, link_tracking_service | 04-business-logic |

---

## 5. Identified Risks & Inconsistencies

### 5.1 Critical Risks

| ID | Risk | Impact | Details |
|----|------|--------|---------|
| R-01 | `states/__init__.py` missing exports | HIGH | `ContractSigningStates`, `LegalProfileStates`, `AdminFeedbackStates` are defined but not exported from `__init__.py`. May cause import errors in handlers. |
| R-02 | `.env.example` has `STARS_ENABLED=true` | HIGH | QWEN.md states Stars and CryptoBot are excluded in v4.3. This env var is misleading. |
| R-03 | `billing_service.py` uses legacy `TransactionType.spend` | MED | QWEN.md says `SPEND` was removed. Yet `billing_service.py` line ~390 uses `type="spend"`. Needs audit. |
| R-04 | Two session factories in use | MED | `async_session_factory` (bot/API) vs `celery_async_session_factory` (Celery). Different pool configs — correct but worth documenting. |
| R-05 | `PLAN_PRICES` has key `'agency'` but `PLAN_LIMITS` uses `'business'` | HIGH | Known HOTFIX in QWEN.md. `PLAN_PRICES['agency']` for backwards compat, `PLAN_LIMITS['business']` for logic. Confusing. |

### 5.2 Medium Risks

| ID | Risk | Impact | Details |
|----|------|--------|---------|
| R-06 | Legacy credit packages in `payments.py` | MED | `CREDIT_PACKAGES`, `YOOKASSA_PACKAGES`, `CREDIT_PACKAGE_STANDARD/BUSINESS` are marked legacy but still in code. May confuse developers. |
| R-07 | `billing_service.create_payment()` uses `PLATFORM_TAX_RATE` not `YOOKASSA_FEE_RATE` | MED | Line ~230: `fee_amount = desired_balance * PLATFORM_TAX_RATE` (0.06) but comments say YooKassa fee is 0.035. Inconsistency needs verification. |
| R-08 | Empty directories | LOW | `src/bot/utils/` and `src/bot/filters/` are empty. Dead code paths or WIP. |
| R-09 | `web_portal` tech debt | MED | TD-01: Hardcoded plan prices in `web_portal/src/lib/constants.ts`. TD-03: MyCampaigns.tsx is a stub. |
| R-10 | `publication_tasks.py` not in `celery_app.py` autodiscover | HIGH | `celery_app.py` `include=` list does NOT include `src.tasks.publication_tasks`. But tasks ARE registered via `@celery_app.task()` decorator. The Beat schedule manually adds `check-scheduled-deletions`. Needs verification that all publication tasks are discoverable. |

### 5.3 Documentation Gaps

| ID | Gap | Impact |
|----|-----|--------|
| D-01 | No OpenAPI/Swagger spec exported | High — Mini App devs need API contract |
| D-02 | No ERD diagram | High — 32 models with complex relationships |
| D-03 | No FSM state transition diagrams | High — 9 state groups, complex flows |
| D-04 | No Celery queue topology diagram | Medium — 7 queues, 3 workers |
| D-05 | No deployment runbook | High — 11 Docker services |
| D-06 | No troubleshooting guide | High — common errors undocumented |
| D-07 | No API endpoint catalog | High — 27 routers, ~100+ endpoints |
| D-08 | S-26 accounting undocumented in main docs | Medium — acts, KUDIR, tax, NDFL |
| D-09 | Web Portal vs Mini App split undocumented | Medium — two separate frontends |

---

## 6. Orphaned & Legacy Code

| File | Status | Recommendation |
|------|--------|----------------|
| `src/constants/tariffs.py` | Thin wrapper → settings.py, marked "will be deleted" | Document as legacy, plan removal |
| `src/constants/payments.py` → `CREDIT_PACKAGES` | Legacy, unused in v4.2+ | Document, mark deprecated |
| `src/constants/payments.py` → `YOOKASSA_PACKAGES` | Legacy, old package system | Document, mark deprecated |
| `src/constants/payments.py` → `CREDIT_PACKAGE_STANDARD/BUSINESS` | Legacy bonus constants | Document, mark deprecated |
| `src/utils/telegram/llm_classifier.py` | QWEN.md: "legacy, not used" | Document, mark deprecated |
| `src/utils/telegram/llm_classifier_prompt.py` | QWEN.md: "legacy, not used" | Document, mark deprecated |
| `src/bot/handlers/advertiser/campaign_create_ai.py` | QWEN.md: "NEVER TOUCH" | Document as protected |
| `src/bot/states/campaign_create.py` | QWEN.md: "NEVER TOUCH" | Document as protected |
| `src/bot/keyboards/shared/main_menu.py` | QWEN.md: "NEVER TOUCH" | Document as protected |
| `src/bot/utils/` | Empty directory | Remove or document as WIP |
| `src/bot/filters/` | Empty directory | Remove or document as WIP |
| `.env.example` → `STARS_ENABLED` | v4.3: Stars excluded | Remove from .env.example |
| `tests/` root-level test files | Mixed with tests/unit/ | Normalize structure |

---

## 7. Next Steps

1. **Deep Dive Phase**: Read each handler file, state file, and service file to extract exact FSM transitions, API endpoints, and business rules.
2. **Migration Audit**: Read each Alembic migration to verify model ↔ database sync.
3. **Frontend Audit**: Map mini_app and web_portal screens to API endpoints.
4. **Cross-Check**: Verify all constants against `payments.py`, `settings.py`, and `QWEN.md`.
5. **Generate AAA docs**: Begin writing the 11 documentation files per the output structure.

---

*End of Dependency Graph & Critical Path Analysis | 🔍 Verified against: filesystem scan 2026-04-08 | ✅ Validation: passed*
