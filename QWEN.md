# Market Telegram Bot — Project Context

> This file is automatically loaded by Qwen Code on every session in this repository.
> It provides the agent with persistent project memory, conventions, and architectural context.
> Refresh with `/memory refresh` · Verify loaded context with `/memory show`

---

## Project Overview

**Market Telegram Bot** is a SaaS platform for automated advertising in Russian-language Telegram communities. Users create ad campaigns, top up their balance, set targeting parameters, and the bot autonomously finds suitable public chats and broadcasts the ad.

| Field | Value |
|---|---|
| **Repository** | `github.com/your-org/market-telegram-bot` |
| **Python** | 3.13.7 (managed via pyenv) |
| **Package manager** | Poetry |
| **Primary language** | Python (backend), TypeScript (Mini App) |
| **Deployment target** | timeweb.cloud (Ubuntu 22.04, Docker Compose) |
| **Bot framework** | aiogram 3.x |

---

## Team & Branch Ownership

| Developer | Personal branch | Responsibility |
|---|---|---|
| **belin** | `developer/belin` | Architecture, DB, parser, Celery, AI service, analytics, DevOps |
| **tsaguria** | `developer/tsaguria` | Bot handlers, FSM dialogs, keyboards, billing UI, Mini App (React) |

**Active branches:**
- `main` — production-ready, auto-deploys to timeweb.cloud on push
- `develop` — integration branch, all feature branches merge here
- `developer/belin`, `developer/tsaguria` — personal bases; feature branches are cut from these
- `feature/*` — short-lived, one task per branch, squash-merged into `develop`
- `hotfix/*` — emergency fixes branched from `main`, merged into both `main` and `develop`

**Branch workflow for every task:**
```bash
git checkout develop && git pull origin develop
git checkout developer/<your-name> && git merge develop
git checkout -b feature/<task-name>
# ... commit, push ...
# Open PR → develop → other dev reviews → Squash Merge
```

**Commit convention (Conventional Commits):**
```
feat(scope): short description
fix(scope): short description
refactor(scope): ...
test(scope): ...
docs(scope): ...
chore(scope): ...
```

---

## Architecture Summary

```
market-telegram-bot/
├── src/
│   ├── bot/              # aiogram 3 handlers, FSM states, keyboards, middlewares
│   ├── api/              # FastAPI — Mini App backend, JWT auth via Telegram initData
│   ├── core/
│   │   └── services/     # Business logic (mailing, billing, ai, analytics, notifications)
│   ├── db/
│   │   ├── models/       # SQLAlchemy 2.0 async models
│   │   ├── repositories/ # Repository pattern (BaseRepository[T])
│   │   └── migrations/   # Alembic migrations
│   ├── tasks/            # Celery tasks + Beat scheduler
│   ├── utils/
│   │   ├── telegram/     # parser.py, sender.py, topic_classifier.py
│   │   └── content_filter/  # 3-level filter: regex → pymorphy3 → LLM
│   └── config/           # Pydantic Settings, logging
├── mini_app/             # Vite + React + TypeScript (Telegram WebApp)
├── tests/
│   ├── unit/             # Pure logic tests, no DB
│   └── integration/      # testcontainers (real PostgreSQL + Redis)
├── docker/               # Dockerfiles, nginx.conf, grafana dashboard
├── docker-compose.yml    # Local development
├── docker-compose.prod.yml  # Production (timeweb.cloud)
├── .github/workflows/    # ci.yml (lint+test on PR), deploy.yml (push to main)
└── Makefile              # make run | test | lint | migrate | shell
```

---

## Tech Stack & Key Libraries

| Layer | Library | Notes |
|---|---|---|
| Bot | `aiogram==3.x` | webhook in prod, polling in dev |
| DB ORM | `SQLAlchemy==2.0` async | `asyncpg` driver |
| Migrations | `alembic` | async env.py |
| Cache / Queue | `redis[asyncio]` | FSM storage, rate-limit, AI cache |
| Task queue | `celery[redis]==5.x` + beat | `mailing`, `parser` queues |
| API | `fastapi` + `uvicorn` | Mini App backend |
| Settings | `pydantic-settings` | reads `.env` |
| AI | `anthropic` (Claude) | fallback: `openai` (GPT-4o) |
| Payments | `yookassa` | webhook-based |
| Chat parser | `telethon` | user-account API |
| Content filter | `pymorphy3` + regex + LLM | 3-level pipeline |
| PDF reports | `reportlab` | sent as Bot document |
| Mini App | Vite + React + TypeScript | `@twa-dev/sdk`, `recharts`, `zustand` |
| Monitoring | `prometheus-client`, Grafana, Sentry | production only |
| Testing | `pytest`, `pytest-asyncio`, `testcontainers` | |
| Linting | `ruff` + `mypy` | enforced in CI and pre-commit |

---

## Database Models (SQLAlchemy)

All models inherit from `TimestampMixin` (adds `created_at`, `updated_at`).

| Model | Key fields |
|---|---|
| `User` | `telegram_id` (BigInt PK), `username`, `balance` (Numeric 12,2), `plan` (Enum), `referral_code`, `is_banned` |
| `Campaign` | `id`, `user_id` (FK), `title`, `text`, `status` (Enum: draft/queued/running/done/error), `filters_json` (JSONB), `scheduled_at` |
| `Chat` | `telegram_id` (BigInt UNIQUE), `title`, `username`, `member_count`, `topic`, `is_active`, `rating` (Float), `last_checked` |
| `MailingLog` | `campaign_id` (FK), `chat_id` (FK), `status` (Enum: sent/failed/skipped), `error_msg`, `sent_at` |
| `Transaction` | `user_id` (FK), `amount` (Numeric), `type` (Enum: topup/spend), `payment_id`, `meta_json` (JSONB) |
| `ContentFlag` | `campaign_id` (FK), `categories` (ARRAY), `flagged_fragments` (JSONB), `decision` (Enum), `reviewed_by` |

---

## Service Layer Contracts

> **Rule:** Handlers NEVER access the DB directly. Always call the appropriate service or repository.

```python
# ✅ Correct in a handler
user = await user_repo.get_by_telegram_id(telegram_id)
stats = await analytics_service.get_campaign_stats(campaign_id)

# ❌ Wrong — no raw queries in handlers
result = await session.execute(select(User).where(...))
```

### Key service methods

| Service | Method | Owner |
|---|---|---|
| `user_repo` | `get_by_telegram_id`, `create_or_update`, `update_balance` | belin |
| `campaign_repo` | `create`, `get_by_user`, `update_status`, `get_scheduled_due` | belin |
| `chat_repo` | `upsert_batch`, `get_active_filtered` | belin |
| `mailing_service` | `run_campaign`, `select_chats`, `check_rate_limit` | belin |
| `billing_service` | `create_payment`, `check_payment`, `deduct_balance`, `apply_referral_bonus` | tsaguria |
| `ai_service` | `generate_ad_text`, `generate_ab_variants`, `improve_text` | belin |
| `analytics_service` | `get_campaign_stats`, `get_user_summary`, `get_top_performing_chats` | belin |
| `notification_service` | `notify_campaign_started`, `notify_campaign_done`, `notify_low_balance` | belin |
| `content_filter` | `check(text) → FilterResult` | belin |

---

## Celery Task Queues

```python
# Two queues, routing defined in celery_config.py
# mailing.*  → queue="mailing"
# parser.*   → queue="parser"

# Beat schedule (celery_config.py):
# - refresh_chat_database    → every 24 hours
# - check_scheduled_campaigns → every 5 minutes
# - delete_old_logs          → every Sunday 03:00
```

---

## Content Filter — 3 Levels

```
Level 1 → regex_check(text)      # < 1ms, compiled patterns from stopwords_ru.json
Level 2 → morph_check(text)      # pymorphy3, catches all inflections
Level 3 → llm_check(text)        # Claude API — only if score(L1+L2) > 0.3
```

**8 blocked categories:** `drugs`, `terrorism`, `weapons`, `adult`, `fraud`, `suicide`, `extremism`, `gambling`

---

## FSM Campaign Wizard (tsaguria)

```
CampaignStates:
  waiting_title → waiting_text → (waiting_ai_description) → waiting_topic
  → waiting_member_count → waiting_schedule → waiting_confirm
```

- Every step has a `← Назад` button that returns to the previous State
- `content_filter.check(text)` runs BEFORE showing the confirmation card
- On confirm: `campaign_repo.create()` then `mailing_tasks.send_campaign.delay(campaign_id)`

---

## API Authentication (FastAPI)

Mini App authenticates via Telegram `initData` HMAC-SHA256:

```python
# src/api/dependencies.py — get_current_user()
# 1. Read X-Init-Data header
# 2. Validate HMAC-SHA256 with BOT_TOKEN
# 3. Cache result in Redis TTL=600
# 4. Return User ORM object
```

---

## Environment Variables

> Never commit `.env`. Use `.env.example` as the template.

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram Bot token from @BotFather |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost:5432/marketbot` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `ANTHROPIC_API_KEY` | Claude API key (AI generation + content filter L3) |
| `OPENAI_API_KEY` | Fallback if Claude rate-limited |
| `YOOKASSA_SHOP_ID` | YooKassa merchant ID |
| `YOOKASSA_SECRET_KEY` | YooKassa secret key |
| `ADMIN_IDS` | Comma-separated Telegram IDs of admins |
| `WEBHOOK_URL` | `https://yourdomain.com/webhook` (production) |
| `MINI_APP_URL` | `https://yourdomain.com/app` (production) |
| `SENTRY_DSN` | Sentry error tracking DSN |
| `API_ID` | Telegram API ID (Telethon parser) |
| `API_HASH` | Telegram API Hash (Telethon parser) |
| `AI_COST_PER_GENERATION` | Cost in RUB per AI text generation (default: 10) |

---

## Common Commands

```bash
# Development
make run          # Start bot in polling mode
make migrate      # alembic upgrade head
make shell        # Open Python REPL with app context

# Testing & Linting
make test         # pytest tests/ --tb=short
make lint         # ruff check + ruff format --check + mypy src/

# Docker
docker compose up -d              # Start postgres + redis locally
docker compose ps                 # Check health
docker compose logs -f bot        # Follow bot logs

# Celery
celery -A src.tasks.celery_app worker --loglevel=info -Q mailing,parser
celery -A src.tasks.celery_app beat --loglevel=info

# Database
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Mini App
cd mini_app && npm run dev        # Dev server (proxies /api → :8001)
cd mini_app && npm run build      # Build to src/static/mini_app/
```

---

## Code Quality Rules

- **No direct DB queries in handlers** — use repositories only
- **No `print()`** — use `logging.getLogger(__name__)`
- **All async functions must use `await`** — no blocking calls in async context
- **Type hints required** on all function signatures
- **No hardcoded secrets** — all from `settings.py` (Pydantic Settings)
- **Max PR size: 400 lines** — split larger changes into multiple PRs
- **Tests required** for all new services and repositories
- **Ruff + mypy must pass** before opening a PR (enforced by CI)

---

## Testing Conventions

```python
# Unit tests — pure logic, no DB, mock everything external
# tests/unit/test_content_filter.py
# tests/unit/test_ai_service.py

# Integration tests — real DB via testcontainers
# tests/integration/test_user_repo.py
# tests/integration/test_campaign_repo.py

# Fixtures in tests/conftest.py:
# - async_session (testcontainers PostgreSQL)
# - redis_client (testcontainers Redis)
# - mock_bot (aiogram Bot mock)
```

---

## Mini App (Telegram WebApp)

- **Stack:** Vite + React 18 + TypeScript + Tailwind CSS
- **Auth:** `window.Telegram.WebApp.initData` → POST `/api/auth/login` → JWT stored in Zustand
- **Theme:** auto-detects `Telegram.WebApp.colorScheme` (light/dark)
- **Design:** glassmorphism — `backdrop-filter: blur(12px)`, `rgba(255,255,255,0.1)` cards
- **Charts:** `recharts` (LineChart, BarChart, PieChart)
- **Routing:** `react-router-dom` — `/`, `/campaigns`, `/analytics`, `/billing`
- **Build output:** `mini_app/dist/` → copied to `src/static/mini_app/` → served by Nginx

---

## Production Infrastructure (timeweb.cloud)

```
Nginx (443 HTTPS, certbot SSL)
  ├── /webhook  → bot container  (aiogram webhook)
  ├── /api      → api container  (FastAPI uvicorn)
  └── /         → mini_app static files

Services: bot | worker (Celery) | api | postgres:16 | redis:7 | flower | grafana | nginx
Monitoring: Prometheus metrics → Grafana dashboard | Sentry DSN for errors
Backup: pg_dump every 6h → timeweb Object Storage (7-day retention)
Deploy: GitHub Actions deploy.yml on push to main (SSH → git pull → docker compose up --no-deps)
```

---

## Important File Locations

| What | Path |
|---|---|
| Bot entry point | `src/bot/main.py` |
| Settings | `src/config/settings.py` |
| DB session | `src/db/session.py` |
| All models | `src/db/models/` |
| All repositories | `src/db/repositories/` |
| Content filter | `src/utils/content_filter/filter.py` |
| Stopwords JSON | `src/utils/content_filter/stopwords_ru.json` |
| Celery app | `src/tasks/celery_app.py` |
| AI service | `src/core/services/ai_service.py` |
| Mailing service | `src/core/services/mailing_service.py` |
| FastAPI entry | `src/api/main.py` |
| Mini App entry | `mini_app/src/main.tsx` |
| Nginx config | `docker/nginx.conf` |
| CI workflow | `.github/workflows/ci.yml` |
| Deploy workflow | `.github/workflows/deploy.yml` |

@src/config/settings.py
@src/db/models/
@src/db/repositories/base.py
