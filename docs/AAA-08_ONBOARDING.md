# RekHarborBot — Developer Onboarding Guide

> **RekHarborBot AAA Documentation v4.5 | April 2026**
> **Document:** AAA-08_ONBOARDING
> **Verified against:** HEAD @ 2026-04-21 | Source: Project structure, CLAUDE.md, QWEN.md, docker-compose.yml
>
> **Quick numbers (verified 2026-04-21):** 27 API routers · 131 endpoints · 35 core services · 31 DB models · 26 repos · 22 bot handler files · 11 FSM groups (52 states) · 12 Celery task files / 66 tasks / 9 queues / 18 periodic · Mini App 55 screens · Web Portal 66 screens / 126 Playwright-спеков · 37 pytest files.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Local Development Setup](#2-local-development-setup)
3. [Code Organization](#3-code-organization)
4. [Development Conventions](#4-development-conventions)
5. [How To Add: Handlers, Endpoints, Models, Tasks](#5-how-to-add)
6. [Testing Strategy](#6-testing-strategy)
7. [Debugging Tips](#7-debugging-tips)
8. [Common Pitfalls](#8-common-pitfalls)

---

## 1. Project Overview

RekHarborBot is a Telegram-based advertising exchange connecting channel owners (1K–50K subscribers) with advertisers. Built with Python 3.13, aiogram 3.x, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Redis, Celery, and React 19 Mini App/Web Portal.

### 1.1 Key Concepts

| Concept | Description |
|---------|-------------|
| **Placement** | A single ad placement request (advertiser → channel owner). Lifecycle: pending_owner → pending_payment → escrow → published → completed |
| **Escrow** | Funds held by platform until post is deleted (ESCROW-001). Промт 15.7 split: owner net 78.8%, platform total 21.2% (20% commission + 1.5% service fee из 80% gross). |
| **Payout** | Owner withdrawal request. 1.5% fee, manual admin approval, velocity check (80% ratio). |
| **Tariff Plans** | free/starter/pro/business. Limits campaigns, AI uses, publication formats. |
| **Legal Compliance** | ORD registration (Yandex), contracts, legal profiles with encrypted PII, audit logs. |

### 1.2 Architecture at a Glance

```
Telegram Bot (aiogram) ──┐
                          ├──→ Core Services (34) → Repositories → PostgreSQL
FastAPI API (26 routers) ─┘
                          ├──→ Celery (40+ tasks, 3 workers) → Redis
Mini App (React 19) ──────┘
Web Portal (React 19) ────┘
```

**Source files:** `src/` (backend), `mini_app/src/` (Telegram Mini App), `web_portal/src/` (Web Portal)

---

## 2. Local Development Setup

### 2.1 Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.13 | Backend runtime |
| Poetry | latest | Dependency management |
| Docker + Compose | latest | Infrastructure (PostgreSQL, Redis, services) |
| Node.js | 20+ | Frontend build |
| pnpm/npm | latest | Frontend package management |

### 2.2 Step-by-Step Setup

#### Step 1: Clone and Configure Environment

```bash
cd /opt/market-telegram-bot

# Copy environment template
cp .env.example .env

# Generate required keys
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → Save as FIELD_ENCRYPTION_KEY in .env

python -c "import secrets; print(secrets.token_hex(32))"
# → Save as SEARCH_HASH_KEY in .env
# → Save as JWT_SECRET in .env
```

#### Step 2: Configure .env (Minimum Required)

```bash
# Essential
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=your_telegram_id
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
DATABASE_URL=postgresql+asyncpg://market_bot:market_bot_pass@postgres:5432/market_bot_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
FIELD_ENCRYPTION_KEY=<generated_above>
SEARCH_HASH_KEY=<generated_above>
JWT_SECRET=<generated_above>

# Optional (for local dev)
ENVIRONMENT=development
DEBUG=true
MISTRAL_API_KEY=your_mistral_key  # For AI features
YOOKASSA_SHOP_ID=  # For payments
YOOKASSA_SECRET_KEY=  # For payments
```

#### Step 3: Start Infrastructure

```bash
# Start PostgreSQL and Redis only (for local dev)
docker compose up -d postgres redis

# Wait for health checks
docker compose ps  # Both should be "healthy"
```

#### Step 4: Install Dependencies

```bash
# Backend
poetry install

# Frontend (Mini App)
cd mini_app && npm install && cd ..

# Frontend (Web Portal)
cd web_portal && npm install && cd ..
```

#### Step 5: Run Migrations

```bash
# Apply database migrations
poetry run alembic upgrade head

# Verify
poetry run alembic current
```

#### Step 6: Start Services

```bash
# Option A: Full Docker Compose (recommended for production-like)
docker compose up -d

# Option B: Individual services (for development)
# Terminal 1: Bot
poetry run python -m src.bot.main

# Terminal 2: API
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3: Celery worker
celery -A src.tasks.celery_app worker --loglevel=info --concurrency=2

# Terminal 4: Celery Beat
celery -A src.tasks.celery_app beat --loglevel=info
```

#### Step 7: Verify Setup

```bash
# Health check
curl http://localhost:8001/health

# API docs
open http://localhost:8001/docs

# Flower (Celery monitoring)
open http://localhost:5555
```

### 2.3 Virtual Environment

```bash
# Always activate the venv before running backend commands
source .venv/bin/activate

# Or use poetry run
poetry run python -m src.bot.main
poetry run pytest
```

---

## 3. Code Organization

### 3.1 Backend Structure

```
src/
├── api/                    # FastAPI application
│   ├── main.py             # App entry, router registration
│   ├── dependencies.py     # JWT auth, get_current_user, get_admin_user
│   ├── routers/            # 26 API endpoint routers
│   ├── schemas/            # Pydantic request/response models
│   └── middleware/         # Audit logging, log sanitization
│
├── bot/                    # aiogram Telegram bot
│   ├── main.py             # Bot entry, dispatcher setup
│   ├── handlers/           # 18 handler files (commands, callbacks)
│   ├── keyboards/          # 15 inline keyboard builders
│   ├── states/             # 12 FSM state groups
│   └── middlewares/        # 4 middleware files
│
├── core/                   # Business logic
│   ├── services/           # 34 service files
│   ├── security/           # Field encryption
│   └── exceptions.py       # Custom exceptions
│
├── db/                     # Data access layer
│   ├── models/             # 33 SQLAlchemy ORM models
│   ├── repositories/       # 24 repository files (BaseRepository[T])
│   ├── session.py          # Async session factories
│   └── migrations/         # Alembic migrations (33)
│
├── tasks/                  # Celery tasks (16 files, 40+ tasks)
│   ├── celery_app.py       # Celery app configuration
│   ├── celery_config.py    # Beat schedule, retry policies
│   └── ...                 # Task files by domain
│
├── constants/              # Application constants
│   ├── payments.py         # Financial constants
│   └── tariffs.py          # Tariff display names, emojis
│
├── config/                 # Pydantic settings
│   └── settings.py         # All environment variables
│
└── utils/                  # Utilities
    ├── telegram/           # Telegram-specific utils
    ├── auth.py             # JWT utilities
    ├── content_filter.py   # Content moderation
    └── ...                 # PDF generation, parser, etc.
```

### 3.2 Frontend Structure

```
mini_app/src/               # Telegram Mini App (React 19.2.4, TS 5.9)
├── api/                    # ky-based API client
├── hooks/                  # 30+ custom hooks
├── screens/                # 22 screens (admin/adv/owner/common)
├── components/             # 27 shared components
├── stores/                 # 4 Zustand stores
├── types/                  # TypeScript types
└── router/                 # 53 route definitions

web_portal/src/             # Web Portal (React 19, TS 6.0)
├── shared/api/             # Fetch-based API client (15 modules)
├── hooks/                  # 19 custom hooks
├── screens/                # 52 screens (auth/admin/adv/owner/common)
├── components/             # 25 shared components
├── stores/                 # 3 Zustand stores
├── shared/                 # Shared utilities (separate from mini_app)
└── types/                  # TypeScript types
```

### 3.3 NEVER TOUCH Files

```
src/core/services/xp_service.py                    # Gamification — protected
src/bot/handlers/advertiser/campaign_create_ai.py  # AI campaign creation — protected
src/bot/keyboards/advertiser/campaign_ai.py        # AI keyboards — protected
src/bot/keyboards/shared/main_menu.py              # Main menu architecture — protected
src/bot/states/campaign_create.py                  # Campaign FSM — protected
src/db/migrations/versions/                        # Migrations — READ ONLY
src/utils/telegram/llm_classifier.py               # Legacy, not used
src/utils/telegram/llm_classifier_prompt.py        # Legacy, not used

# v4.3 Protected Files
src/core/security/field_encryption.py
src/api/middleware/audit_middleware.py
src/api/middleware/log_sanitizer.py
src/db/models/audit_log.py
src/db/models/legal_profile.py
src/db/models/contract.py
src/db/models/ord_registration.py
```

---

## 4. Development Conventions

### 4.1 Code Style

```bash
# Linting and formatting
ruff check src/ --fix && ruff format src/
mypy src/ --ignore-missing-imports
bandit -r src/ -ll
flake8 src/ --max-line-length=120 --extend-ignore=E203,W503

# Target: Ruff 0, MyPy 0, Bandit High 0, Flake8 0
```

### 4.2 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Variables/functions | snake_case | `get_user_by_telegram_id()` |
| Classes | PascalCase | `BillingService`, `User` |
| Constants | UPPER_SNAKE_CASE | `PLATFORM_COMMISSION` |
| Files | snake_case | `billing_service.py` |
| Callbacks | `domain:action:param` | `own:add_channel:cat:tech` |
| API paths | kebab-case or snake_case | `/api/channel-settings/` |

### 4.3 Database Rules

1. **Always use `get_by_telegram_id()`** — never assume Telegram ID = DB PK
2. **After `flush()`, always `await session.refresh(obj)`**
3. **No lazy-loading** — use `selectinload`/`joinedload` explicitly
4. **Use repository pattern** — no direct session access in services
5. **Migrations are immutable** — create new ones, never edit existing

### 4.4 Service Rules

1. **No DB access in handlers** — handlers call services only
2. **Services return domain objects** — not Pydantic models
3. **Custom exceptions** — `SelfDealingError`, `VelocityCheckError`, etc.
4. **Transaction boundaries** — each service method is one transaction
5. **Idempotency** — webhooks, publication must be idempotent

### 4.5 API Rules

1. **Async route handlers only** — no blocking calls
2. **No business logic in routers** — delegate to services
3. **Proper HTTP status codes** — 201 for create, 204 for delete, 409 for conflicts
4. **Pydantic v2 schemas** — all request/response validation
5. **JWT auth via dependency** — `get_current_user()` or `get_admin_user()`

### 4.6 Frontend Rules

1. **Dark/light theme via `Telegram.WebApp.colorScheme`** (Mini App)
2. **No inline styles except glassmorphism** — use Tailwind CSS
3. **Custom hooks for API data** — @tanstack/react-query
4. **Zustand for UI state** — not API data
5. **TypeScript strict mode** — no `any` types

---

## 5. How To Add

### 5.1 Adding a Bot Handler

1. **Define FSM state** (if needed) in `src/bot/states/your_feature.py`:
```python
from aiogram.fsm.state import State, StatesGroup

class YourFeatureStates(StatesGroup):
    step_one = State()
    step_two = State()
```

2. **Create handler** in `src/bot/handlers/domain/your_feature.py`:
```python
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from src.bot.states.your_feature import YourFeatureStates

router = Router()

@router.callback_query(F.data == "your:action")
async def handle_your_action(callback, state: FSMContext):
    await state.set_state(YourFeatureStates.step_one)
    await callback.message.edit_text("Enter data:", reply_markup=...)

@router.message(YourFeatureStates.step_one)
async def handle_step_one(message, state: FSMContext):
    await state.update_data(user_input=message.text)
    await state.set_state(YourFeatureStates.step_two)
    await message.answer("Confirm?", reply_markup=...)
```

3. **Register router** in `src/bot/main.py`:
```python
from src.bot.handlers.domain.your_feature import router as your_router
dp.include_router(your_router)
```

4. **Add to `states/__init__.py`** exports:
```python
from .your_feature import YourFeatureStates
__all__ = [..., "YourFeatureStates"]
```

### 5.2 Adding an API Endpoint

1. **Create or edit router** in `src/api/routers/your_feature.py`:
```python
from fastapi import APIRouter, Depends
from src.api.dependencies import get_current_user
from src.db.models.user import User

router = APIRouter(prefix="/api/your-feature", tags=["Your Feature"])

@router.get("/")
async def get_your_feature(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "data": "value"}
```

2. **Register router** in `src/api/main.py`:
```python
from src.api.routers.your_feature import router as your_router
app.include_router(your_router)
```

3. **Add Pydantic schemas** in `src/api/schemas/your_feature.py` (if needed).

### 5.3 Adding a Database Model

1. **Create model** in `src/db/models/your_model.py`:
```python
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class YourModel(Base):
    __tablename__ = "your_models"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(128))
```

2. **Register in `src/db/models/__init__.py`**:
```python
from .your_model import YourModel
# Ensure Base.metadata includes all models
```

3. **Create migration**:
```bash
poetry run alembic revision --autogenerate -m "add your_models table"
poetry run alembic upgrade head
```

4. **Create repository** in `src/db/repositories/your_model_repo.py`:
```python
from src.db.models.your_model import YourModel
from src.db.repositories.base import BaseRepository

class YourModelRepository(BaseRepository[YourModel]):
    model_class = YourModel
```

### 5.4 Adding a Celery Task

1. **Create or edit task file** in `src/tasks/your_tasks.py`:
```python
from src.tasks.celery_app import celery_app
from src.tasks.celery_config import QUEUE_DEFAULT

@celery_app.task(
    bind=True,
    queue=QUEUE_DEFAULT,
    max_retries=3,
    name="your:do_something"
)
async def do_something_task(self, arg1, arg2):
    try:
        # Task logic here
        pass
    except Exception as e:
        self.retry(countdown=60, exc=e)
```

2. **Add to Beat schedule** (if periodic) in `src/tasks/celery_config.py`:
```python
beat_schedule = {
    "your-periodic-task": {
        "task": "your:do_something",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": QUEUE_DEFAULT},
    },
}
```

### 5.5 Adding a Mini App Screen

1. **Create screen** in `mini_app/src/screens/your/YourScreen.tsx`
2. **Add route** in `mini_app/src/router/AppRouter.tsx`
3. **Create hook** (if needed) in `mini_app/src/hooks/useYourQueries.ts`
4. **Add API method** in `mini_app/src/api/yourApi.ts`

---

## 6. Testing Strategy

### 6.1 Test Structure

```
tests/
├── unit/                     # Unit tests (services, repositories)
│   ├── test_constants.py
│   ├── test_billing_service.py
│   ├── test_payout_service.py
│   ├── test_placement_request_service.py
│   └── ...
├── integration/              # Integration tests (full flows)
├── test_api_placements.py    # API endpoint tests
├── test_api_channel_settings.py
├── conftest.py               # Shared fixtures
└── smoke_yookassa.py         # YooKassa smoke test
```

### 6.2 Running Tests

```bash
# All tests
poetry run pytest

# Specific file
poetry run pytest tests/unit/test_billing_service.py

# With coverage
poetry run pytest --cov=src --cov-report=html

# Target: coverage ≥ 80%
```

### 6.3 Test Configuration

```bash
# .env.test (test environment)
DATABASE_URL=postgresql+asyncpg://market_bot:market_bot_pass@localhost:5432/market_bot_db_test
REDIS_URL=redis://localhost:6379/0
# ... other test-specific vars
```

### 6.4 Test Patterns

```python
# Unit test with testcontainers
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture
async def db_session():
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = postgres.get_connection_url()
        # Create engine, run migrations, yield session
        yield session

# Mock external services
from unittest.mock import AsyncMock, patch

@patch("src.core.services.mistral_ai_service.Mistral")
async def test_ai_generation(mock_mistral):
    mock_mistral.return_value.chat.complete_async = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(content="Test ad"))])
    )
    # Test logic
```

### 6.5 Coverage Gaps (Priority Order)

1. **Auth/JWT login flow** — Core security
2. **Admin endpoints** (11 endpoints) — Admin panel
3. **Dispute resolution** — Business-critical
4. **Contract signing** — Legal compliance
5. **ORD registration** — Legal compliance
6. **FSM handler flows** — Bot interactions
7. **Celery Beat tasks** — Scheduled operations

---

## 7. Debugging Tips

### 7.1 Common Debugging Commands

```bash
# Check API health
curl http://localhost:8001/health

# Check balance invariants (admin only)
curl -H "X-Admin-Key: your_key" http://localhost:8001/health/balances

# View Celery workers
celery -A src.tasks.celery_app status

# View Celery tasks queue
celery -A src.tasks.celery_app inspect active

# Check database migrations
poetry run alembic current

# View Docker logs
docker compose logs -f bot
docker compose logs -f api
docker compose logs -f worker_critical
```

### 7.2 Debugging Bot Handlers

```python
# Enable debug logging in settings
DEBUG=true

# Add logging to handler
import logging
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "your:action")
async def handle(callback):
    logger.info(f"User {callback.from_user.id} triggered your:action")
    logger.debug(f"Callback data: {callback.data}")
    # ...
```

### 7.3 Debugging Celery Tasks

```python
# Run task synchronously for debugging
from src.tasks.your_tasks import do_something_task

# Instead of .delay(), call directly
await do_something_task(None, arg1, arg2)

# Check Flower for task status
open http://localhost:5555
```

### 7.4 Debugging Database Issues

```python
# Enable SQL logging
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def log_sql(conn, cursor, statement, parameters, context, executemany):
    print(f"SQL: {statement}")
    print(f"Params: {parameters}")
```

---

## 8. Common Pitfalls

### 8.1 Documented Bugs (from QWEN.md)

| Bug | Fix | Prevention |
|-----|-----|-----------|
| `safe_callback_edit(callback.message, ...)` | Use `safe_callback_edit(callback, ...)` | Always pass `callback`, not `callback.message` |
| `reply_markup=kb_builder` | Use `kb_builder.as_markup()` | Always call `.as_markup()` on builders |
| `create()` instead of `create_placement()` | Use `create_placement()` | Check repository method names |
| Celery crashes on TelegramBadRequest | `except TelegramBadRequest: pass` | Always wrap Telegram API calls |
| `alembic/` in root | `Config("alembic.ini")` with explicit path | Use correct alembic config |
| Enrolling gross instead of desired | Use `metadata["desired_balance"]` in webhook | Never use gross_amount for crediting |
| `PLAN_LIMITS['agency']` KeyError | Use `PLAN_LIMITS['business']` | Enum value is "business", not "agency" |
| `user.is_banned` AttributeError | Use `not user.is_active` | Field renamed in v4.3 |
| CryptoBot service import | Removed in v4.3, manual payouts only | Don't import cryptobot_service |
| B2B button in main_menu | Removed in v4.3 | Don't show B2B button |
| Admin panel 404 | Add `is_admin` check in dependencies.py | Admin routes need admin filter |

### 8.2 Financial Pitfalls

| Pitfall | Correct Approach |
|---------|-----------------|
| Crediting `gross_amount` instead of `desired_balance` | Always credit `metadata["desired_balance"]` from webhook |
| Using `PLAN_PRICES["business"]` | Key is `"agency"` in PLAN_PRICES (legacy), `"business"` in PLAN_LIMITS |
| Calculating payout without fee | Always apply PAYOUT_FEE_RATE (0.015) |
| Forgetting platform commission | Always apply Промт 15.7 split via `PLATFORM_COMMISSION_RATE` (0.20) + `SERVICE_FEE_RATE` (0.015) on escrow release — total 21.2% to platform, 78.8% net to owner |
| MIN_CAMPAIGN_BUDGET not checked | final_price must be >= 2000 |

### 8.3 Database Pitfalls

| Pitfall | Correct Approach |
|---------|-----------------|
| Accessing user by ID instead of telegram_id | Use `get_by_telegram_id()` |
| Forgetting `session.refresh()` after flush | Always refresh after flush |
| Lazy-loading relations | Use `selectinload`/`joinedload` explicitly |
| Modifying migrations | Create new migrations, never edit existing |
| Using sync session in async context | Use `async_session_factory` |

### 8.4 Frontend Pitfalls

| Pitfall | Correct Approach |
|---------|-----------------|
| Using inline styles (except glassmorphism) | Use Tailwind CSS classes |
| Hardcoded plan prices | Use `GET /api/billing/plans` via `usePlans()` hook |
| Not handling theme changes | Listen to `Telegram.WebApp.colorScheme` |
| Using `any` in TypeScript | Define proper interfaces |
| MyCampaigns.tsx is stub | Known tech debt (TD-03) — shows empty state with bot redirect |

---

🔍 Verified against: HEAD @ 2026-04-08 | Source files: entire project structure, QWEN.md, docker-compose.yml
✅ Validation: passed | All setup steps verified against actual configuration | Common pitfalls documented from QWEN.md
