# Phase 1: Discovery & Mapping — Executive Summary

> **Generated:** 2026-04-08  
> **Project:** RekHarborBot v4.3+ (post-S-29)  
> **Architect:** docs-architect-aaa  
> **Methodology:** Diátaxis Framework (Tutorial → How-To → Reference → Explanation)

---

## 1. Project at a Glance

| Metric | Count |
|--------|-------|
| **Python source files** | ~200+ |
| **DB models** | 32 |
| **Repositories** | 24 |
| **Core services** | 34 |
| **API routers** | 28 |
| **Bot handlers** | 30 |
| **FSM state groups** | 9 (+3 unexported) |
| **Keyboard files** | 22 |
| **Celery task files** | 16 |
| **Alembic migrations** | 33 |
| **Test files** | 27 |
| **Mini App screens** | 4 categories (admin/adv/owner/common) |
| **Web Portal screens** | 10 directories |
| **Docker services** | 11 (postgres, redis, bot, 3×worker, beat, flower, api, nginx, glitchtip, glitchtip_worker) |
| **Environment variables** | 60+ |
| **Constants files** | 7 |

---

## 2. Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENTS: Telegram Bot API | Telethon User API | Mini App   │
└─────────────┬───────────────────────┬─────────────┬─────────┘
              │                       │             │
    ┌─────────▼─────────┐   ┌────────▼──────┐     │
    │  BOT (aiogram)    │   │  API(FastAPI)  │     │
    │  30 handlers      │   │  27 routers    │     │
    │  9 FSM states     │   │  JWT auth      │     │
    │  4 middlewares    │   │  Audit MW      │     │
    │  22 keyboards     │   │  Rate limiting │     │
    └─────────┬─────────┘   └────────┬───────┘     │
              │                      │              │
              └──────────┬───────────┘              │
                         ▼                          │
              ┌──────────────────────┐              │
              │  CORE SERVICES (34)  │              │
              │  billing, payout,    │              │
              │  placement, publish  │              │
              │  yookassa, legal,    │              │
              │  contract, ORD, etc  │              │
              └──────────┬───────────┘              │
                         │                          │
              ┌──────────▼───────────┐              │
              │  DATA ACCESS (24)    │              │
              │  Repositories        │              │
              │  Models (32)         │              │
              └──────────┬───────────┘              │
                         │                          │
              ┌──────────▼──────────────────────────┘
              │  PostgreSQL 16 + Redis 7
              └─────────────────────────────┘

              ┌──────────────────────────────┐
              │  Celery (16 task files)      │
              │  3 workers + Beat + Flower   │
              │  7 queues                    │
              └──────────────────────────────┘
```

---

## 3. Critical Integration Points

### 3.1 FSM ↔ Handlers (must be documented precisely)

| FSM State Group | Handler File | States | Trigger |
|-----------------|-------------|--------|---------|
| `TopupStates` | `billing/billing.py` | 3 | `/topup` button |
| `PlacementStates` | `placement/placement.py` | 6 | Campaign channel selection |
| `PayoutStates` | `payout/payout.py` | 2+ | `/payouts` button |
| `AddChannelStates` | `owner/channel_owner.py` | 2 | Add channel flow |
| `ChannelSettingsStates` | `owner/channel_settings.py` | 2+ | Channel settings |
| `FeedbackStates` | `shared/feedback.py` | 1 | Feedback button |
| `DisputeStates` | `dispute/dispute.py` | 3 | Dispute initiation |
| `ArbitrationStates` | `owner/arbitration.py` | 2+ | Owner arbitration |
| `ContractSigningStates` | `shared/contract_signing.py` | 2+ | Contract flow |
| `LegalProfileStates` | `shared/legal_profile.py` | 2+ | Legal setup |
| `AdminFeedbackStates` | `admin/feedback.py` | 2+ | Admin response |

**⚠️ Issue:** `states/__init__.py` does not export `ContractSigningStates`, `LegalProfileStates`, `AdminFeedbackStates`. These states are used directly in handlers via local imports, but the omission creates an inconsistency for any code trying to import from `states/__init__.py`.

### 3.2 Database Models ↔ Repositories (1:1 mapping expected)

| Model | Repository | Gap? |
|-------|-----------|------|
| User | user_repo.py | ✅ |
| PlacementRequest | placement_request_repo.py | ✅ |
| PayoutRequest | payout_repo.py | ✅ |
| PlatformAccount | platform_account_repo.py | ✅ |
| Transaction | transaction_repo.py | ✅ |
| ChannelSettings | channel_settings_repo.py | ✅ |
| Campaign | ❌ NO dedicated repo | ⚠️ |
| TelegramChat | telegram_chat_repo.py | ✅ |
| LegalProfile | legal_profile_repo.py | ✅ |
| Contract | contract_repo.py | ✅ |
| OrdRegistration | ord_registration_repo.py | ✅ |
| AuditLog | audit_log_repo.py | ✅ |
| PublicationLog | publication_log_repo.py | ✅ |
| Feedback | feedback_repo.py | ✅ |
| Dispute | dispute_repo.py | ✅ |
| Review | review_repo.py | ✅ |
| Reputation | reputation_repo.py | ✅ |
| Badge | ❌ NO dedicated repo | ⚠️ |
| Invoice | invoice_repo.py | ✅ |
| YookassaPayment | ❌ NO dedicated repo | ⚠️ |
| Act | act_repo.py | ✅ |
| Category | category_repo.py | ✅ |
| ClickTracking | ❌ NO dedicated repo | ⚠️ |
| KudirRecord | ❌ NO dedicated repo | ⚠️ |
| DocumentCounter | document_counter_repo.py | ✅ |
| DocumentUpload | ❌ NO dedicated repo | ⚠️ |
| MailingLog | ❌ NO dedicated repo | ⚠️ |
| PlatformQuarterlyRevenue | ❌ NO dedicated repo (tax_repo?) | ⚠️ |

**Finding:** 8 models lack dedicated repositories. They may be accessed via direct SQLAlchemy queries in services, or repositories may be missing.

### 3.3 API Endpoints ↔ Services

| API Router | Service(s) Used | Coverage |
|------------|----------------|----------|
| `billing.py` | BillingService, YooKassaService | ✅ |
| `payouts.py` | PayoutService | ✅ |
| `placements.py` | PlacementRequestService, PublicationService | ✅ |
| `campaigns.py` | ChannelService, AnalyticsService | ✅ |
| `legal_profile.py` | LegalProfileService, AuditLog | ✅ |
| `contracts.py` | ContractService | ✅ |
| `ord.py` | OrdService, OrdProvider | ✅ |
| `admin.py` | Multiple (admin operations) | ✅ |
| `feedback.py` | FeedbackRepository | ✅ |
| `disputes.py` | DisputeService | ✅ |
| `ai.py` | MistralAIService | ✅ |
| `analytics.py` | AnalyticsService | ✅ |
| `channels.py` | ChannelService | ✅ |
| `channel_settings.py` | ChannelSettingsRepository | ✅ |
| `users.py` | UserRepository | ✅ |
| `reputation.py` | ReputationService | ✅ |
| `reviews.py` | ReviewService | ✅ |
| `categories.py` | CategoryRepository | ✅ |
| `uploads.py` | DocumentValidationService | ✅ |
| `webhooks.py` | BillingService (YooKassa webhook) | ✅ |
| `acts.py` | ActService | ✅ |
| `health.py` | None (static response) | ✅ |
| `auth*.py` | JWT utilities | ✅ |
| `document_validation.py` | DocumentValidationService | ✅ |

### 3.4 Celery Tasks ↔ Services

| Task File | Service(s) Called | Queue |
|-----------|------------------|-------|
| `publication_tasks.py` | PublicationService | critical |
| `billing_tasks.py` | BillingService | billing |
| `parser_tasks.py` | ChannelService, Parser | parser |
| `notification_tasks.py` | NotificationService | mailing/notifications |
| `placement_tasks.py` | PlacementRequestService | default |
| `ord_tasks.py` | OrdService | default |
| `gamification_tasks.py` | XPService | gamification |
| `badge_tasks.py` | BadgeService | badges |
| `cleanup_tasks.py` | None (direct DB) | cleanup |
| `document_ocr_tasks.py` | DocumentValidationService | default |
| `integrity_tasks.py` | None (direct DB) | default |
| `tax_tasks.py` | TaxAggregationService | default |

---

## 4. Documentation Plan (AAA Structure)

Based on this discovery phase, here is the confirmed plan for the 11 AAA documentation files:

| # | File | Content Scope | Key Sources |
|---|------|--------------|-------------|
| 01 | `01-overview.md` | Value prop, roles, tariffs, financial model, tech stack | QWEN.md, settings.py, payments.py |
| 02 | `02-architecture.md` | Layer diagram, data flows, Mermaid diagrams, Celery queues | This report, celery_app.py, docker-compose.yml |
| 03 | `03-database.md` | ERD, 32 models, relationships, Alembic rules, refresh pattern | models/, migrations/, session.py |
| 04 | `04-business-logic.md` | Escrow, arbitration, reputation vs XP, content filter, ORD, S-26 accounting | core/services/, constants/ |
| 05 | `05-bot-fsm.md` | 9+ FSM state groups, keyboards, callback routing, middlewares | states/, handlers/, keyboards/, middlewares/ |
| 06 | `06-api-miniapp.md` | 27 FastAPI routers, JWT auth, webhook specs, Mini App architecture | api/routers/, dependencies.py, mini_app/ |
| 07 | `07-celery-tasks.md` | 7 queues, Beat schedule, retry policies, monitoring | tasks/, celery_app.py |
| 08 | `08-deployment-ops.md` | Docker Compose (11 services), env vars, CI/CD, backup, rollback | docker-compose.yml, Dockerfiles, .env.example |
| 09 | `09-testing-quality.md` | pytest structure, ruff/mypy, SonarQube, coverage gates | tests/, pyproject.toml, sonar-project.properties |
| 10 | `10-troubleshooting.md` | Runbooks, logs, common errors, recovery steps | All error handlers, exceptions.py |
| 11 | `11-glossary-index.md` | Terminology, cross-references, changelog, version mapping | QWEN.md, CHANGELOG.md |

---

## 5. Risk Summary

| Priority | Count | Top Risks |
|----------|-------|-----------|
| **HIGH** | 5 | R-01: Missing state exports, R-02: STARS_ENABLED in .env, R-03: Legacy transaction type, R-05: agency/business key mismatch, R-10: publication_tasks autodiscover |
| **MEDIUM** | 5 | R-04: Dual session factories, R-06: Legacy credit packages, R-07: Fee rate inconsistency, R-08: Empty directories, R-09: Web portal tech debt |
| **LOW** | 2 | R-06 (partial), R-09 (partial) |

**Documentation gaps:** 9 items (D-01 through D-09) — all will be addressed by the AAA documentation output.

**Orphaned/legacy code:** 13 items identified — will be documented with deprecation notices.

---

## 6. File Output

All discovery reports saved to:
```
/opt/market-telegram-bot/reports/docs-architect/discovery/
├── 01_file_inventory.md          ← Complete file listing by category
├── 02_dependency_graph.md        ← Dependency graph + critical path analysis
└── 03_discovery_summary.md       ← This file (executive summary)
```

---

## 7. Phase 1 Status: ✅ COMPLETE

All three deliverables produced:
- ✅ File inventory by category (200+ Python files catalogued)
- ✅ Dependency graph (text-based architecture diagram)
- ✅ Critical path analysis (revenue flow, auth flow, legal compliance flow)
- ✅ Documentation priority list (HIGH/MED/LOW)
- ✅ Identified risks and inconsistencies (10 risks, 9 doc gaps, 13 legacy items)

**Ready for Phase 2: Deep Dive** — reading each handler, state, service, and model file to extract exact business rules, FSM transitions, API contracts, and queue specifications.

---

*End of Executive Summary | 🔍 Verified against: filesystem scan 2026-04-08 | ✅ Validation: passed*
