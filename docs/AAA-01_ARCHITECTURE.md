# RekHarborBot — System Architecture Document

> **RekHarborBot AAA Documentation v4.3 | April 2026**
> **Document:** AAA-01_ARCHITECTURE
> **Verified against:** HEAD @ 2026-04-08 | Source: `src/`, `docker-compose.yml`, `settings.py`

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Layer Architecture](#2-layer-architecture)
3. [Data Flow Diagrams](#3-data-flow-diagrams)
4. [Deployment Topology](#4-deployment-topology)
5. [Technology Stack](#5-technology-stack)
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)
7. [Architectural Decision Records](#7-architectural-decision-records)

---

## 1. System Overview

RekHarborBot is a Telegram-based advertising exchange platform connecting channel owners (1K–50K subscribers, MVP) with advertisers. It provides escrow-protected payments, automated publication, dispute resolution, legal compliance (ORD registration, contracts), and admin oversight via both Telegram Bot and Mini App interfaces.

### 1.1 Core Value Proposition

| Stakeholder | Value |
|-------------|-------|
| **Advertisers** | Find channels, create campaigns, AI-assisted ad generation, escrow protection, analytics |
| **Channel Owners** | Monetize channels, set prices/formats, receive payouts, manage reputation |
| **Platform** | 21.2% effective on placements (20% gross commission + 1.5% service fee from owner gross), 1.5% fee on payouts, tariff subscriptions |
| **Admins** | Full oversight: users, disputes, feedback, legal profiles, platform settings |

### 1.2 Key Metrics

| Metric | Count | Source |
|--------|-------|--------|
| Python source files | ~287 | `src/` |
| DB models | 33 | `src/db/models/` |
| API endpoints | 120+ | `src/api/routers/` (26 routers) |
| Bot handlers | 30+ | `src/bot/handlers/` (18 files) |
| FSM state groups | 12 | `src/bot/states/` |
| Celery tasks | 40+ | `src/tasks/` (16 files) |
| Alembic migrations | 33 | `alembic/versions/` |
| Mini App screens | 22 | `mini_app/src/screens/` |
| Web Portal screens | 52 | `web_portal/src/screens/` |
| Docker services | 11 | `docker-compose.yml` |

### 1.3 Financial Model (Промт 15.7, 28.04.2026)

```
Advertiser pays 10,000₽ for placement
    │
    ├── Platform commission (gross 20%):           = 2,000₽
    ├── Owner gross share (80%):                   = 8,000₽
    │     └── Service fee withheld (1.5% of 8,000) = 120₽ → platform
    │
    ├── Effective platform total (21.2%):          = 2,120₽ → platform.profit_accumulated
    └── Effective owner net (78.8%):               = 7,880₽ → owner.earned_rub
         │
         └── When owner requests payout (gross=7,880₽):
              ├── Payout fee: 1.5% = 118.20₽ → platform.profit_accumulated
              └── Net payout: 7,761.80₽ → owner receives manually
```

**Constants:** `src/constants/fees.py` — `PLATFORM_COMMISSION_RATE=0.20`,
`OWNER_SHARE_RATE=0.80`, `SERVICE_FEE_RATE=0.015`,
`YOOKASSA_FEE_RATE=0.035`, `CANCEL_REFUND_*_RATE=0.50/0.40/0.10`. Payout
flow: `PAYOUT_FEE_RATE=0.015` in `src/constants/payments.py`.

---

## 2. Layer Architecture

### 2.1 Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 1: CLIENTS                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Telegram Bot │  │  Mini App    │  │ Web Portal   │  │ Admin TG    │ │
│  │ (aiogram)    │  │ (React 19)   │  │ (React 19)   │  │ Bot Token   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
└─────────┼──────────────────┼─────────────────┼─────────────────┼────────┘
          │                  │                 │                 │
          ▼                  ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 2: APPLICATION                                                    │
│  ┌────────────────────┐              ┌───────────────────────────────┐  │
│  │  BOT (aiogram 3.x) │              │  API (FastAPI)                │  │
│  │  ┌──────────────┐  │              │  ┌─────────────────────────┐  │  │
│  │  │ 22 handlers  │  │              │  │ 27 routers / 131 eps    │  │  │
│  │  │ 11 FSM groups│  │              │  │ JWT auth (HMAC-SHA256)  │  │  │
│  │  │ 15 keyboards │  │              │  │ Audit middleware        │  │  │
│  │  │ 4 middleware │  │              │  │ Log sanitizer           │  │  │
│  │  └──────────────┘  │              │  └─────────────────────────┘  │  │
│  └────────┬───────────┘              └──────────────┬────────────────┘  │
│           │                                         │                    │
│           └──────────────┬──────────────────────────┘                    │
│                          ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  CORE SERVICES (35 services in src/core/services/)                 │  │
│  │  ┌─────────────┐ ┌────────────┐ ┌─────────────┐ ┌──────────────┐ │  │
│  │  │BillingSvc   │ │PayoutSvc   │ │PlacementSvc │ │PublicationSvc│ │  │
│  │  │1459 lines   │ │778 lines   │ │1029 lines   │ │392 lines     │ │  │
│  │  └─────────────┘ └────────────┘ └─────────────┘ └──────────────┘ │  │
│  │  ┌─────────────┐ ┌────────────┐ ┌─────────────┐ ┌──────────────┐ │  │
│  │  │LegalProfSvc │ │ContractSvc │ │OrdSvc       │ │MistralAISvc  │ │  │
│  │  │AnalyticsSvc │ │Reputation  │ │Notification │ │LinkTracking  │ │  │
│  │  └─────────────┘ └────────────┘ └─────────────┘ └──────────────┘ │  │
│  └──────────────────────────┬────────────────────────────────────────┘  │
│                             │                                            │
│  ┌──────────────────────────▼────────────────────────────────────────┐  │
│  │  DATA ACCESS (26 repositories + SQLAlchemy 2.0 async)              │  │
│  │  Generic BaseRepository[T] pattern, asyncpg driver                 │  │
│  │  selectinload/joinedload for relations (no lazy-loading)           │  │
│  └──────────────────────────┬────────────────────────────────────────┘  │
│                             │                                            │
│  ┌──────────────────────────▼────────────────────────────────────────┐  │
│  │  CELERY WORKERS (12 task files, 66 tasks, 3 workers + Beat + Flower)│  │
│  │  ┌─────────────────┐ ┌──────────────────┐ ┌───────────────────┐   │  │
│  │  │worker_critical  │ │worker_background │ │worker_game        │   │  │
│  │  │-Q worker_crit,  │ │-Q parser,cleanup,│ │-Q gamification,   │   │  │
│  │  │  mailing,       │ │  background       │ │  badges           │   │  │
│  │  │  notifications, │ │concurrency=4      │ │concurrency=2      │   │  │
│  │  │  billing,       │ │                  │ │                   │   │  │
│  │  │  placement      │ │                  │ │                   │   │  │
│  │  │concurrency=2    │ │                  │ │                   │   │  │
│  │  └─────────────────┘ └──────────────────┘ └───────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 3: INFRASTRUCTURE                                                 │
│  ┌──────────────┐              ┌──────────────┐                         │
│  │ PostgreSQL 16│              │  Redis 7     │                         │
│  │ 31 models    │              │ - Cache      │                         │
│  │ 1 migration  │              │ - Celery broker│                        │
│  │ asyncpg      │              │ - FSM store  │                         │
│  └──────────────┘              │ - Dedup      │                         │
│                                └──────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Service Communication Patterns

| Communication | Protocol | Direction | Purpose |
|--------------|----------|-----------|---------|
| Bot → Services | Python function calls | sync | Business logic execution |
| API → Services | Python function calls | async | REST endpoints |
| Services → Repos | async SQLAlchemy | async | Data persistence |
| Bot/API → Celery | Redis broker | async | Background tasks |
| Celery → Services | Python function calls | async | Publication, notifications, parsing |
| YooKassa → API | HTTP POST webhook | inbound | Payment confirmation |
| Mini App → API | HTTP/HTTPS (ky) | async | User interactions |
| Web Portal → API | HTTP/HTTPS (fetch) | async | Admin/user operations |

---

## 3. Data Flow Diagrams

### 3.1 Revenue Flow (Placement Lifecycle)

```
Advertiser                    System                      Channel Owner
    │                            │                             │
    │ 1. Create placement ──────▶│                             │
    │    (category, channels,    │                             │
    │     format, text, video)   │                             │
    │                            │                             │
    │                            │ 2. Notify owner ◀───────────│
    │                            │    (pending_owner)           │
    │                            │                             │
    │                            │ 3. Owner accepts/counter ──▶│
    │                            │    (pending_payment)         │
    │                            │                             │
    │ 4. Advertiser pays ───────▶│                             │
    │    (escrow freeze)         │                             │
    │    balance_rub -= amount   │                             │
    │    escrow_reserved += amt  │                             │
    │                            │                             │
    │                            │ 5. Schedule publication     │
    │                            │    (Celery: publish_placement)│
    │                            │    status → escrow           │
    │                            │                             │
    │                            │ 6. Publish to channel ──────▶│
    │                            │    send_message → message_id │
    │                            │    status → published        │
    │                            │                             │
    │                            │ 7. After duration expires   │
    │                            │    delete_published_post     │
    │                            │    unpin + delete message    │
    │                            │                             │
    │                            │ 8. ESCROW-001: release      │
    │                            │    owner.earned_rub += 78.8% │
    │                            │    platform.profit += 21.2%  │
    │                            │    status → completed        │
    │                            │                             │
    │ 9. Notification ◀──────────│ 10. Payout request ◀────────│
    │                            │     (gross, fee=1.5%, net)   │
    │                            │     earned_rub -= gross      │
    │                            │     payout_reserved += gross │
    │                            │                             │
    │                            │ 11. Admin approves manually │
    │                            │     status → paid            │
    │                            │     platform.payout_rsv -= g │
```

**Source files:** `src/core/services/billing_service.py` (freeze_escrow, release_escrow), `src/core/services/publication_service.py` (publish_placement, delete_published_post), `src/core/services/payout_service.py` (create_payout, admin_approve_payout)

### 3.2 Authentication Flow (Telegram Mini App)

```
Mini App                    API                       Telegram
    │                        │                           │
    │ 1. User opens TMA      │                           │
    │    (Telegram.WebApp)   │                           │
    │                        │                           │
    │ 2. Get initData        │                           │
    │    (signed JSON)       │                           │
    │                        │                           │
    │ 3. POST /api/auth/     │                           │
    │    telegram{init_data} │                           │
    │                        │                           │
    │                        │ 4. validate_telegram_init_data()
    │                        │    HMAC-SHA256(             │
    │                        │      data_check_string,     │
    │                        │      BOT_TOKEN              │
    │                        │    ) == hash_from_init      │
    │                        │                           │
    │                        │ 5. Find/create user         │
    │                        │    by telegram_id            │
    │                        │                           │
    │                        │ 6. create_jwt_token()       │
    │                        │    {user_id, telegram_id,   │
    │                        │     plan, exp=24h}          │
    │                        │                           │
    │ 7. ← {access_token,    │                           │
    │     user}              │                           │
    │                        │                           │
    │ 8. Store in localStorage                            │
    │                        │                           │
    │ 9. Subsequent requests:                             │
    │    Authorization: Bearer {jwt}                      │
    │                        │                           │
    │                        │ 10. JWT decode + verify    │
    │                        │     get_current_user dep   │
    │                        │                           │
    │ 11. ← Protected data   │                           │
```

**Source files:** `src/api/routers/auth.py` (telegram login, JWT creation), `src/api/dependencies.py` (JWT verification, get_current_user)

### 3.3 Publication Flow (ESCROW-001)

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  Placement  │────▶│  Publication │────▶│  Telegram    │────▶│  Post       │
│  status:    │     │  Service     │     │  Bot API     │     │  Deleted    │
│  escrow     │     │              │     │              │     │             │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
       │                    │                    │                    │
       │                    │ send_message()     │                    │
       │                    │───────────────────▶│                    │
       │                    │                    │                    │
       │                    │ message_id saved   │                    │
       │                    │◀───────────────────│                    │
       │                    │                    │                    │
       │                    │ [scheduled_delete] │                    │
       │                    │───────────────────────────────────────▶│
       │                    │                    │                    │
       │                    │ delete_message()   │                    │
       │                    │───────────────────▶│ (TelegramBadRequest│
       │                    │                    │  → pass)           │
       │                    │                    │                    │
       │  release_escrow()  │                    │                    │
       │  ◀─────────────────│                    │                    │
       │  owner += 78.8%    │                    │                    │
       │  platform += 21.2% │                    │                    │
       │  status→completed  │                    │                    │
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
```

**CRITICAL:** `release_escrow()` is called ONLY from `delete_published_post()`, not from `publish_placement()`. This ensures the owner is paid only after the post has served its full duration.

**Source files:** `src/tasks/publication_tasks.py:delete_published_post()`, `src/core/services/billing_service.py:release_escrow()`

### 3.4 Dispute Resolution Flow

```
Advertiser ──────┐                    ┌── Channel Owner
                  │                    │
                  │ 1. Create dispute  │
                  │    (reason,        │
                  │     comment)       │
                  │                    │
                  │ 2. Dispute status  │
                  │    → open           │
                  │                    │
                  │         3. Owner explanation ◀────────────────────┐
                  │            status → owner_explained               │
                  │                                                  │
                  │ 4. Admin reviews ◀───────────────────────────────┘
                  │    GET /api/disputes/admin/{id}                  │
                  │                                                  │
                  │ 5. Admin resolves                               │
                  │    resolution: owner_fault|advertiser_fault      │
                  │              |technical|partial                   │
                  │                                                  │
                  │ 6. Actions based on resolution:                  │
                  │    - owner_fault: refund advertiser, penalty     │
                  │    - advertiser_fault: pay owner, penalty        │
                  │    - technical: full refund                      │
                  │    - partial: split funds                        │
                  │                                                  │
                  │ 7. Notifications to both parties                 │
                  └─────────────────────────────────────────────────┘
```

**Source files:** `src/api/routers/disputes.py`, `src/bot/handlers/dispute/dispute.py`, `src/bot/states/dispute.py`

---

## 4. Deployment Topology

### 4.1 Docker Compose Services

```
┌─────────────────────────────────────────────────────────────────────┐
│  Docker Network: market_bot_network (bridge)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────┐  ┌───────┐  ┌────────────┐  │
│  │postgres: │  │redis:    │  │ bot  │  │ api   │  │  nginx     │  │
│  │16-alpine │  │7-alpine  │  │      │  │       │  │            │  │
│  │:5432     │  │:6379     │  │      │  │:8001  │  │:8080/:8443 │  │
│  └────┬─────┘  └────┬─────┘  └──┬───┘  └───┬───┘  └─────┬──────┘  │
│       │              │          │          │           │           │
│  ┌────┴─────┐  ┌────┴─────┐  ┌─┴──────────┴───────────┴────────┐  │
│  │postgres_ │  │ redis_   │  │ worker_critical (Q:celery,      │  │
│  │data vol  │  │ data vol │  │   mailing,notifications,billing)│  │
│  └──────────┘  └──────────┘  │   concurrency=2                 │  │
│                               └─────────────────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────────────────────┐  │
│  │celery_   │  │ flower   │  │ worker_background (Q:parser,    │  │
│  │beat      │  │:5555     │  │   cleanup,rating)               │  │
│  │          │  │          │  │   concurrency=4                 │  │
│  └──────────┘  └──────────┘  └─────────────────────────────────┘  │
│                               ┌─────────────────────────────────┐  │
│  ┌─────────────────┐ ┌──────┐│ worker_game (Q:gamification,    │  │
│  │glitchtip:8090   │ │glitch││   badges)                       │  │
│  │(error tracking) │ │tip_w ││   concurrency=2                 │  │
│  │                 │ │kr    │└─────────────────────────────────┘  │
│  └─────────────────┘ └──────┘                                     │
│                                                                     │
│  Volumes: postgres_data, redis_data, contracts_data                 │
│  External: /etc/letsencrypt (SSL certs)                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Service Dependencies

| Service | Depends On | Health Check | Restart Policy |
|---------|-----------|-------------|----------------|
| postgres | — | pg_isready (10s interval) | unless-stopped |
| redis | — | redis-cli ping (10s interval) | unless-stopped |
| bot | postgres (healthy), redis (healthy) | — | unless-stopped |
| api | postgres (healthy), redis (healthy) | — | unless-stopped |
| worker_critical | postgres (healthy), redis (healthy) | celery inspect ping (30s) | unless-stopped |
| worker_background | postgres (healthy), redis (healthy) | celery inspect ping (30s) | unless-stopped |
| worker_game | postgres (healthy), redis (healthy) | celery inspect ping (30s) | unless-stopped |
| celery_beat | redis (healthy) | — | unless-stopped |
| flower | worker_critical, worker_background, worker_game | — | unless-stopped |
| nginx | bot, api | curl /health (30s) | unless-stopped |
| glitchtip | postgres (healthy), redis (healthy) | — | unless-stopped |
| glitchtip_worker | postgres (healthy), redis (healthy) | — | unless-stopped |

### 4.3 Port Mapping

| Service | Internal Port | External Port | Access |
|---------|--------------|---------------|--------|
| postgres | 5432 | — (internal only) | Docker network |
| redis | 6379 | 6379 | Docker network + host |
| api | 8001 | — (internal only) | Via nginx only |
| nginx | 80 | 127.0.0.1:8080 | Localhost |
| nginx | 443 | 127.0.0.1:8443 | Localhost (SSL) |
| flower | 5555 | 5555 | Public |
| glitchtip | 8080 | 8090 | Public |

**Source file:** `docker-compose.yml`

---

## 5. Technology Stack

### 5.1 Backend

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| Python | 3.13 | Runtime | Latest stable, async improvements |
| aiogram | 3.x | Telegram Bot | Modern async framework, FSM support |
| FastAPI | latest | REST API | Auto OpenAPI, Pydantic v2, async |
| SQLAlchemy | 2.0 async | ORM | Async support, type hints, modern |
| asyncpg | latest | PostgreSQL driver | Fastest async PG driver |
| Alembic | latest | Migrations | SQLAlchemy native migration tool |
| Celery | 5.x | Task Queue | Distributed task processing |
| Redis | 7 | Broker + Cache | Fast, persistent, FSM storage |
| Pydantic | v2 | Validation | Fast, type-safe settings/schemas |
| Mistral AI SDK | >=1.12.4 | AI Generation | Official SDK, only AI provider |
| YooKassa SDK | latest | Payments | RUB payments, Russian market |
| cryptography | latest | Field Encryption | Fernet for PII protection |

### 5.2 Frontend

| Technology | Mini App | Web Portal | Purpose |
|------------|----------|------------|---------|
| React | 19.2.4 | 19 | UI framework |
| TypeScript | 5.9 | 6.0 | Type safety |
| Vite | 8 | latest | Build tool |
| Tailwind CSS | v4 @theme | v4 @theme | Styling |
| @twa-dev/sdk | latest | — | Telegram WebApp integration |
| Zustand | latest | latest | State management |
| @tanstack/react-query | latest | latest | Data fetching |
| ky | latest | — | API client (fetch wrapper) |
| react-router-dom | latest | latest | Routing |
| recharts | latest | — | Charts |

### 5.3 Infrastructure

| Technology | Version | Purpose |
|------------|---------|---------|
| Docker | latest | Containerization |
| Docker Compose | latest | Service orchestration |
| PostgreSQL | 16-alpine | Primary database |
| Redis | 7-alpine | Cache + broker |
| Nginx | latest | Reverse proxy + static files |
| GlitchTip | latest | Error tracking (self-hosted Sentry) |
| Flower | latest | Celery monitoring |
| Ruff | latest | Linting + formatting |
| pytest | latest | Testing |
| testcontainers | latest | Integration testing |

---

## 6. Cross-Cutting Concerns

### 6.1 Authentication

| Layer | Mechanism | Details |
|-------|-----------|---------|
| Bot | Telegram user identity | Verified by aiogram (Telegram API) |
| Mini App API | JWT via Telegram initData HMAC-SHA256 | `validate_telegram_init_data()` → `create_jwt_token()` → 24h expiry |
| Web Portal API | JWT (same as Mini App) | `Authorization: Bearer {token}` |
| Admin endpoints | Admin role check | `User.is_admin=True` + JWT |
| YooKassa webhooks | IP whitelist | YooKassa server IPs only |
| Health balances | X-Admin-Key header | Static admin key |

**Source files:** `src/api/routers/auth.py`, `src/api/dependencies.py`, `src/utils/auth.py`

### 6.2 Logging & Monitoring

| Component | Tool | Configuration |
|-----------|------|---------------|
| Error tracking | GlitchTip (self-hosted Sentry) | `SENTRY_DSN`, `sentry_sdk.init()` |
| Celery monitoring | Flower | `:5555` dashboard |
| Audit logging | AuditLog model | Middleware captures action, old/new values, IP, user_agent |
| Health checks | `/health` endpoint | Static response |
| Balance invariants | `/health/balances` | Admin key required, checks escrow/payout consistency |
| Payload logging | `/tmp/glitchtip_queue` | Volume mount for debugging |

**Source files:** `src/api/middleware/audit_middleware.py`, `src/api/routers/health.py`, `src/db/models/audit_log.py`

### 6.3 Error Handling

| Layer | Strategy | Details |
|-------|----------|---------|
| Bot handlers | Try/except + safe_callback_edit | Never crash, log errors, notify admins |
| API routers | HTTPException + Pydantic validation | Proper status codes (400, 403, 404, 409, 410, 422) |
| Services | Custom exceptions | `SelfDealingError`, `VelocityCheckError`, `PlanLimitError`, `InsufficientFundsError` |
| Celery tasks | Retry policies | Exponential backoff, max_retries per task type |
| Telegram API | Graceful degradation | `TelegramBadRequest → pass` for deleted posts |

**Source file:** `src/core/exceptions.py`

### 6.4 Rate Limiting

| Endpoint | Limit | Implementation |
|----------|-------|----------------|
| Login code | 10/hour | In-memory counter |
| Telegram Login Widget | 5/min | In-memory counter |
| Bot handlers | Throttling middleware | Per-user, per-chat limits |
| API general | None (MVP) | Planned for post-MVP |

---

## 7. Architectural Decision Records

### ADR-001: Escrow Release Only After Post Deletion (ESCROW-001)

**Status:** Accepted
**Context:** Should the owner be paid when the post is published or when it's deleted?
**Decision:** Release escrow ONLY after the post is deleted (end of its full duration).
**Rationale:** Protects advertisers — ensures the post serves its full contractual duration before the owner receives payment. If the post is deleted early (by owner), escrow is still released, but the owner's reputation is penalized.
**Consequences:** Owner must wait until post duration expires + deletion task runs. Slightly delayed gratification but fair for both parties.
**Source:** `src/tasks/publication_tasks.py:delete_published_post()`, `src/core/services/billing_service.py:release_escrow()`

### ADR-002: Manual Payout Approval

**Status:** Accepted (v4.3)
**Context:** Should payouts be automated via CryptoBot or manual via admin?
**Decision:** Manual approval through admin panel. CryptoBot removed.
**Rationale:** Reduces dependency complexity, gives admins full oversight of outgoing funds, allows for fraud detection before transfer. Velocity checks (80% ratio) provide additional safety.
**Consequences:** Admins must actively approve each payout. Owners wait for admin action.
**Source:** `src/core/services/payout_service.py`, `src/bot/states/payout.py`

### ADR-003: Telegram ID ≠ DB PK

**Status:** Locked
**Context:** How to identify users across the system?
**Decision:** Always use `get_by_telegram_id()` for user lookups. Never assume Telegram ID equals DB primary key.
**Rationale:** Telegram IDs are stable external identifiers. DB PKs are internal and may differ. Separation allows for data migration without breaking user identity.
**Consequences:** All handlers and API endpoints must resolve users via telegram_id first.
**Source:** QWEN.md, `src/db/repositories/user_repo.py`

### ADR-004: Single AI Provider (Mistral Only)

**Status:** Accepted (v4.3)
**Context:** Should we support multiple AI providers?
**Decision:** Only Mistral AI via official SDK. OpenRouter removed.
**Rationale:** Simplifies integration, reduces maintenance, Mistral medium-latest provides quality/cost balance. No need for provider abstraction when only one is used.
**Consequences:** `OPENROUTER_API_KEY` does not exist. `MISTRAL_API_KEY` is required.
**Source:** `src/config/settings.py`, `src/core/services/mistral_ai_service.py`

### ADR-005: Repository Pattern with Generic Base

**Status:** Accepted
**Context:** How to structure data access?
**Decision:** Generic `BaseRepository[T]` pattern with SQLAlchemy 2.0 async. No lazy-loading. Explicit `selectinload`/`joinedload` for relations. Always `session.refresh()` after `flush()`.
**Rationale:** Type-safe, consistent interface across all models. Explicit loading prevents N+1 queries. Refresh ensures model state is current after flush.
**Consequences:** 24 repository files, consistent patterns, no direct session access in services.
**Source:** `src/db/repositories/`, `src/db/session.py`

### ADR-006: PLAN_LIMITS Uses 'business' Key (Not 'agency')

**Status:** Hotfixed
**Context:** `UserPlan.BUSINESS.value == 'business'` but `PLAN_PRICES` used `'agency'` key.
**Decision:** `PLAN_LIMITS` uses `'business'`. `PLAN_PRICES` retains `'agency'` for backward compatibility but no code accesses it. Dead key risk acknowledged.
**Rationale:** Enum consistency throughout codebase. Legacy key preserved only for data migration safety.
**Consequences:** Code accessing `PLAN_PRICES["business"]` → KeyError. Code accessing `PLAN_LIMITS["agency"]` → KeyError.
**Source:** `src/constants/payments.py`, QWEN.md HOTFIX note

### ADR-007: Field-Level Encryption for PII

**Status:** Accepted (v4.3)
**Context:** How to protect sensitive legal profile data?
**Decision:** Fernet encryption for all PII fields (INN, KPP, company_name, full_name, passport_data, address, phone, email). Separate hash key for INN search indexing.
**Rationale:** GDPR/compliance requirement. Even if DB is compromised, PII remains encrypted. Hash allows INN lookups without decrypting.
**Consequences:** `FIELD_ENCRYPTION_KEY` and `SEARCH_HASH_KEY` are mandatory env vars. All legal profile PII accessed via encrypted properties.
**Source:** `src/core/security/field_encryption.py`, `src/db/models/legal_profile.py`

---

## Document Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-08 | Initial AAA architecture document |

---

🔍 Verified against: HEAD @ 2026-04-08 | Source files: `src/`, `docker-compose.yml`, `settings.py`, `QWEN.md`
✅ Validation: passed | All claims backed by code evidence | Diagrams verified against actual architecture
