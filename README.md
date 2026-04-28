# RekHarborBot — Telegram Advertising Exchange

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![SQLAlchemy 2](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://docs.sqlalchemy.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![v4.5](https://img.shields.io/badge/Version-4.5-orange.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**RekHarborBot** — Telegram-native рекламная биржа для каналов 1K–50K подписчиков. Платформа соединяет рекламодателей (малый и средний бизнес) с владельцами тематических каналов. Весь цикл — от выбора каналов до оплаты, публикации и аналитики — происходит внутри Telegram без перехода на сторонние сайты.

**Конкуренты:** Telega.in, Epicstars, TGStat. **Ключевое отличие:** Telegram-native, эскроу-защита, ИИ-генерация текстов, автоматическая ОРД-регистрация.

---

## 🆕 What's New in v4.5 (April 2026)

| # | Change | Impact |
|---|--------|--------|
| 1 | **Web Portal** — React SPA, 107 `.tsx` / 66 экранов / 126 Playwright-спеков | Второй фронтенд помимо Mini App |
| 2 | **Landing** — статический одностраничник на `rekharbor.ru` | Маркетинговая витрина |
| 3 | **Unified disputes flow** — единые лейблы, роль-зависимый текст, сервер-инварианты | S-48 consumer trust |
| 4 | **ORD via Yandex API v7** — `YandexOrdProvider` + автопроброс ERID | ФЗ-38 compliance (stub по умолчанию) |
| 5 | **Accounting module** — КУДиР, акты, счета-фактуры, квартальная отчётность | S-26 B2B hygiene |
| 6 | **SonarQube: 4 sub-projects scanned** | src + mini_app + web_portal + landing |
| 7 | **Schema consolidated** — все миграции свернуты в `0001_initial_schema.py` | Pre-prod reset pattern |
| 8 | **Python 3.14 upgrade** | Celery/pyright/ruff под новый target |

📜 Полная история изменений: [CHANGELOG.md](CHANGELOG.md)

---

## ✨ Value Proposition

### Для рекламодателя

**Запусти рекламу в 10 каналах за 5 минут прямо в Telegram.** Деньги заморожены в эскроу до публикации. Отчёт с CPM, CTR, ROI после размещения.

- ✅ 9-шаговый мастер кампаний с ИИ-генерацией текстов (Mistral AI)
- ✅ Таргетинг по 11 категориям, размеру чатов, рейтингу
- ✅ Эскроу-защита: средства блокируются до публикации
- ✅ Юридические договоры + ОРД-регистрация (v4.3)

### Для владельца канала

**Подключи бота один раз — получай заявки и автоматические выплаты.** Ты контролируешь что публиковать.

- ✅ Opt-in: владелец сам добавляет бота администратором
- ✅ Арбитраж: принятие/отклонение/контр-предложение (макс 3 раунда)
- ✅ Выплаты владельцу (Промт 15.7): 78.8% net, платформа 21.2% total
- ✅ Репутация 0–10, система отзывов, реферальная программа

---

## 💰 Financial Model (Промт 15.7, 28.04.2026)

- **1 кредит = 1 RUB** (виртуальная единица)
- **Комиссия платформы:** 20% валовая + 1.5% сервисный сбор из доли владельца → **21.2%** total
- **Владелец получает:** 80% gross − 1.5% сервисный сбор → **78.8%** net
- **Налог платформы:** ООО УСН (доходы − расходы) 15%; ИП — 6% (УСН-доходы)

| Сбор | Размер | Кто платит |
|------|--------|------------|
| Комиссия платформы (gross) | 20% | Удерживается из размещения |
| Сервисный сбор | 1.5% | Удерживается из доли владельца |
| Эффективная доля платформы | **21.2%** | от `final_price` |
| Эффективная выплата владельцу | **78.8%** | от `final_price` |
| ЮKassa pass-through fee | 3.5% | Пользователь при пополнении (платформа зарабатывает 0) |
| Cancel after_confirmation | 50 / 40 / 10 | Возврат рекламодателю / владельцу / платформе |
| Вывод средств (`PAYOUT_FEE_RATE`) | 1.5% | Владелец при выплате |

**Способы оплаты:** ЮKassa (карта, СБП, YooMoney). ~~Telegram Stars~~ и ~~CryptoBot~~ отключены в v4.3.

---

## 📦 Tariffs

| Тариф | Цена | Кампаний/мес | AI запросов | Форматы | Рефералы |
|-------|------|--------------|-------------|---------|----------|
| **Free** | 0 ₽ | 1 | 0 | post_24h | ❌ |
| **Starter** | 490 ₽ | 5 | 3 | post_24h, post_48h | ❌ |
| **Pro** | 1 490 ₽ | 20 | 20 | + post_7d | ✅ |
| **Agency** | 4 990 ₽ | ∞ | ∞ | Все 5 форматов | ✅ |

**Форматы:** `post_24h` (×1.0) · `post_48h` (×1.4) · `post_7d` (×2.0) · `pin_24h` (×3.0) · `pin_48h` (×4.0)

---

## 👥 User Roles

| Роль | Код | Доступ |
|------|-----|--------|
| Новый | `new` | Онбординг, выбор роли |
| Рекламодатель | `advertiser` | Кампании, аналитика, юр. профили, ОРД |
| Владелец | `owner` | Каналы, заявки, выплаты, репутация |
| Обе роли | `both` | Комбинированное меню |
| Администратор | `admin` | Полный доступ, Mini Admin Panel (7 экранов) |

> v4.3+: Рекламодатели и владельцы создают **LegalProfile** (юрлица, ИП, самозанятые) и подписывают **Contract** через платформу.

---

## 🏗️ Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Telegram    │   │  Mini App    │   │  Web Portal  │   │   Landing    │
│  Bot (poll)  │   │  (React SPA) │   │  (React SPA) │   │  (static)    │
│              │   │  app.rekh... │   │ portal.rekh. │   │  rekharbor.  │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────────────┘
       └──────────────────┼──────────────────┘
                          │
               ┌──────────▼──────────┐
               │   FastAPI Router    │
               │  27 routers / 131   │
               │     endpoints       │
               └──────────┬──────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────┐         ┌─────▼────┐         ┌──────▼──────┐
│aiogram │         │ Celery   │         │ Parser      │
│Handlers│         │ 3 workers│         │ (Telethon)  │
│(FSM)   │         │ 9 queues │         │ (read-only) │
└───┬────┘         └─────┬────┘         └──────┬──────┘
    └─────────────────────┼─────────────────────┘
                          │
               ┌──────────▼──────────┐
               │  35 Core Services   │
               └──────────┬──────────┘
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────────┐   ┌───────▼──────┐   ┌──────────▼────────┐
│ PostgreSQL  │   │   Redis 7    │   │   Mistral AI SDK  │
│ 31 models   │   │ FSM+Broker   │   │   (AI generation) │
└────────────┘   └──────────────┘   └───────────────────┘
```

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| Bot | aiogram 3.x | 22 handler-файла, 11 FSM-групп, 4 middleware |
| Mini App | React 19 + TS 6 + Vite 8 + Tailwind v4 | 55 экранов · `@telegram-apps/sdk-react` · ky + TanStack Query |
| Web Portal | React 19 + TS 6 + Vite 8 + Tailwind v4 | 66 экранов · JWT в localStorage · Telegram Login Widget |
| Landing | Static Vite + Tailwind v4 | `rekharbor.ru` — маркетинг, CSP без unsafe-inline |
| API | FastAPI | 27 роутеров, 131 endpoint, JWT через Telegram initData HMAC-SHA256 |
| Workers | Celery + Beat | 3 воркера / 9 очередей / 66 задач / 18 периодических |
| DB | PostgreSQL 16 + SQLAlchemy 2.0 async | 31 модель, 26 репозиториев, consolidated schema |
| Cache | Redis 7 | FSM storage, rate limiting, AI cache |
| AI | Mistral AI (mistralai>=1.12.4) | Генерация текстов, L3 контент-фильтр, классификация тем |
| Payments | ЮKassa | Пополнение баланса (карта, СБП, YooMoney) |

---

## 🛠️ Tech Stack

**Backend:** Python 3.14 · aiogram 3.x · SQLAlchemy 2.0 async · FastAPI 0.115+ · Alembic 1.14+ · Celery 5.x · asyncpg 0.30+ · pydantic-settings 2.7+ · mistralai 1.12.4+ · Telethon 1.36+ · pymorphy3 2.0+ · yookassa 3.2.0 · reportlab 4.3+

**Frontend (Mini App · Web Portal · Landing):** React 19.2 · TypeScript 6.0 · Vite 8 · TailwindCSS v4 (CSS-first, `@theme`) · Zustand 5 · TanStack React Query 5 · ky 1.x · React Hook Form + zod · Recharts 3 · react-router-dom 7 · `@telegram-apps/sdk-react` 2 · Motion 12 · Sentry

**DevOps & Tools:** Docker Compose · nginx · Cloudflare Tunnel · GitHub Actions · GlitchTip + Sentry · SonarQube (4 sub-projects) · Gitleaks · Ruff · MyPy · pytest + testcontainers · Playwright (e2e) · Flower · Grafana

---

## 🚀 Quick Start

### Requirements

- **Python 3.14** (через pyenv)
- **Poetry** (менеджер зависимостей)
- **Docker** (PostgreSQL 16, Redis 7)
- **Node.js 20+** (для Mini App / Web Portal / Landing)

### Setup

```bash
# 1. Clone & install deps
git clone https://github.com/rybkagreen/market-telegram-bot.git
cd market-telegram-bot
poetry install

# 2. Configure environment
cp .env.example .env
# Edit .env — см. [.env.example](.env.example) для полного списка

# 3. Start infrastructure
docker compose up -d postgres redis

# 4. Apply schema (single consolidated migration pre-prod)
make migrate   # or: poetry run alembic upgrade head

# 5. Run bot (polling mode for development)
make run       # or: poetry run python -m src.bot.main

# 6. Run Celery workers (3 workers, 9 queues)
celery -A src.tasks.celery_app worker -Q worker_critical,mailing,notifications,billing,placement -n critical@%h --concurrency=2 -l info
celery -A src.tasks.celery_app worker -Q parser,cleanup,background -n background@%h --concurrency=4 -l info
celery -A src.tasks.celery_app worker -Q gamification,badges -n game@%h --concurrency=2 -l info

# 7. Run Celery Beat (periodic tasks — ONE instance only)
celery -A src.tasks.celery_app beat -l info

# 8. Mini App (optional, dev server on :3000)
cd mini_app && npm install && npm run dev

# 9. Web Portal (optional, dev server on :5174)
cd web_portal && npm install && npm run dev

# 10. Landing (optional)
cd landing && npm install && npm run dev
```

> **Bot token:** Получить у [@BotFather](https://t.me/BotFather). **Mistral API:** [console.mistral.ai](https://console.mistral.ai). **ЮKassa:** merchant dashboard.

---

## 📁 Project Structure

```
market-telegram-bot/
├── src/
│   ├── bot/              # aiogram: 22 handler-файла, 11 FSM-групп, 15 клавиатур, 4 middleware
│   ├── api/              # FastAPI: 27 роутеров, 131 endpoint, JWT, 2 middleware
│   ├── db/               # SQLAlchemy: 31 модель, 26 репозиториев, 1 consolidated migration
│   ├── core/             # 35 бизнес-сервисов (billing, payout, ORD, contracts, …)
│   ├── tasks/            # Celery: 12 task-файлов, 66 задач, 18 периодических
│   ├── utils/            # Telegram sender/parser, content filter (L1/L2/L3), PDF builders
│   └── config/           # Pydantic settings
├── mini_app/             # Telegram Mini App — React 19 + TS 6 + Vite 8, 55 экранов
├── web_portal/           # Web Portal — React 19 + TS 6 + Vite 8, 66 экранов, 126 Playwright-спеков
├── landing/              # Маркетинговый лендинг — static Vite + Tailwind v4
├── tests/                # pytest: 37 файлов тестов (unit/, integration/, e2e_api/, tasks/)
├── docs/                 # AAA-01…AAA-12 — архитектура, API, DB, сервисы, FSM, Celery, фронт, деплой, тесты
├── reports/              # Discovery-отчёты, CHANGES_*.md, sprint reports
├── .qwen/skills/         # 10 project-specific skills для Qwen Code
├── docker-compose.yml    # 11 сервисов (postgres, redis, bot, 3×worker, beat, flower, api, nginx, glitchtip)
├── nginx/                # Reverse proxy, HTTPS, server blocks для app/portal/landing
└── scripts/              # Utility scripts (DB cleanup, etc.)
```

---

## 🗄️ Database

**31 SQLAlchemy моделей · 26 репозиториев · 1 consolidated migration** (head: `0001_initial_schema`).

> **Migration policy:** до первого прод-пользователя не создаём инкрементальные Alembic-миграции — редактируем `0001_initial_schema.py` и пересоздаём БД. После старта прод — стандартный Alembic workflow.

### Core Models

| Модель | Назначение |
|--------|-----------|
| `User` | Пользователи: баланс, план, роли, XP, рефералы |
| `TelegramChat` | Telegram-каналы: подписчики, рейтинг, тематика |
| `Campaign` | Кампании: broadcast/placement, бюджет, метрики |
| `PlacementRequest` | Заявки на размещение: эскроу, арбитраж, 5 форматов |
| `ChannelSettings` | Настройки монетизации канала |
| `ReputationScore` / `ReputationHistory` | Репутация пользователей (0–10, ≠ XP) |
| `Transaction` | Финансовые операции: topup, escrow, commission |
| `PayoutRequest` | Запросы на вывод: gross/fee/net, velocity check |
| `PlatformAccount` | Счёт платформы (singleton id=1): эскроу, прибыль |
| `Review` | Отзывы 1–5 звёзд после размещения |

### v4.3 Legal & Compliance

| Модель | Назначение |
|--------|-----------|
| `LegalProfile` | Юридические профили (юрлица, ИП, самозанятые), PII encrypted |
| `Contract` / `ContractSignature` | Договоры с платформой, PDF генерация |
| `OrdRegistration` | ОРД-регистрация рекламных кампаний |
| `AuditLog` | Журнал аудита критических операций |
| `PublicationLog` | Лог публикаций/удалений постов |
| `ClickTracking` | Трекинг кликов по ссылкам кампаний |

### v4.4 Accounting (S-26)

| Модель | Назначение |
|--------|-----------|
| Accounting models | КУДиР, акты, счета-фактуры, НДС, документооборот |

> Полные спецификации моделей: [QWEN.md — Database Models](QWEN.md#database-models)

---

## 🚀 Development Workflow

```bash
# ── Run bot ──
make run                              # polling mode

# ── Celery ──
celery -A src.tasks.celery_app worker -Q critical,background,monitoring -l info
celery -A src.tasks.celery_app beat -l info

# ── Tests ──
poetry run pytest tests/ -v           # 37 test files (unit/, integration/, e2e_api/, tasks/)
poetry run pytest --cov=src           # coverage gate ≥80%
cd web_portal && npx playwright test  # 126 e2e specs (mobile + desktop)

# ── Linting ──
ruff check src/ --fix && ruff format src/
mypy src/ --ignore-missing-imports
bandit -r src/ -ll
flake8 src/ --max-line-length=120 --extend-ignore=E203,W503

# ── Migrations ──
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head

# ── Target: Ruff 0, MyPy 0, Bandit High 0, Flake8 0 ──
```

### Qwen Code Skills

Проект использует систему **.qwen/skills/** (10 skills) для AI-assisted разработки:

| Skill | Zone |
|-------|------|
| `aiogram-handler` | Handlers, FSM, callback routing, middlewares |
| `celery-task` | Tasks, retry policies, Beat schedules |
| `content-filter` | 3-level moderation pipeline (regex → pymorphy3 → LLM) |
| `docker-compose` | Services, multi-stage builds, healthchecks |
| `docs-sync` | Post-change documentation updates |
| `fastapi-router` | Routers, JWT auth, Pydantic v2 schemas |
| `pytest-async` | Async testing, testcontainers, coverage gates |
| `python-async` | asyncio patterns, async context managers |
| `react-mini-app` | Telegram Mini App: React, TS, glassmorphism, Zustand |
| `sqlalchemy-repository` | SQLAlchemy 2.0 async, repository pattern |

> ⚠️ После любых изменений **обязательно** запускай `docs-sync` skill для обновления документации.

---

## 🚀 Deployment

### Production (timeweb.cloud)

**Stack:** Ubuntu 22.04 · Docker Compose · nginx (HTTPS) · Cloudflare Tunnel

**Services:** `bot` (webhook) · `worker-critical` (4 concurrency) · `worker-background` (8 concurrency) · `worker-monitoring` (2 concurrency) · `beat` (1 instance) · `api` (uvicorn) · `postgres:16` · `redis:7` · `flower` · `grafana` · `nginx`

```bash
# Manual deploy
cd /opt/market-telegram-bot
git pull origin main
docker compose pull
docker compose up -d --no-deps

# CI/CD: GitHub Actions on push to main (see .github/workflows/)
```

**Environment:** см. [.env.example](.env.example) для всех переменных. В production: `ENVIRONMENT=production`, `DEBUG=false`, webhook URL вместо polling.

---

## 📊 Monitoring

| Инструмент | Назначение | URL |
|-------------|-----------|-----|
| **GlitchTip / Sentry** | Ошибки, трассировки | Sentry dashboard |
| **SonarQube** | Статический анализ кода (src, mini_app/src, web_portal/src, landing) | SonarQube dashboard |
| **Flower** | Celery task monitoring | `:5555` |
| **Grafana** | Метрики приложения | `:3000` |
| **Gitleaks** | Secrets detection в git (pre-commit + CI) | `.gitleaks.toml` |

---

## 📚 Documentation

**AAA reference set** (`docs/` — Diátaxis framework, verified 2026-04-21):

| # | Doc | Scope |
|---|-----|-------|
| 01 | [AAA-01_ARCHITECTURE](docs/AAA-01_ARCHITECTURE.md) | Слои, диаграммы потоков, технологический стек |
| 02 | [AAA-02_API_REFERENCE](docs/AAA-02_API_REFERENCE.md) | 27 FastAPI-роутеров, 131 endpoint, JWT, webhook-спеки |
| 03 | [AAA-03_DATABASE_REFERENCE](docs/AAA-03_DATABASE_REFERENCE.md) | 31 модель, 26 репозиториев, ERD, миграции |
| 04 | [AAA-04_SERVICE_REFERENCE](docs/AAA-04_SERVICE_REFERENCE.md) | 35 Core Services (billing, payout, ORD, contracts, …) |
| 05 | [AAA-05_FSM_REFERENCE](docs/AAA-05_FSM_REFERENCE.md) | 11 FSM-групп / 52 states, keyboards, routing |
| 06 | [AAA-06_CELERY_REFERENCE](docs/AAA-06_CELERY_REFERENCE.md) | 9 очередей / 66 задач / 18 периодических |
| 07 | [AAA-07_FRONTEND_REFERENCE](docs/AAA-07_FRONTEND_REFERENCE.md) | Mini App (55 экранов) · Web Portal (66 экранов) · Landing |
| 08 | [AAA-08_ONBOARDING](docs/AAA-08_ONBOARDING.md) | Developer onboarding, setup, проектные инварианты |
| 09 | [AAA-09_DEPLOYMENT](docs/AAA-09_DEPLOYMENT.md) | Docker Compose, nginx, CI/CD, backup/restore |
| 09 | [AAA-09_TESTING_QUALITY](docs/AAA-09_TESTING_QUALITY.md) | pytest, Playwright, SonarQube, coverage |
| 10 | [AAA-10_DISCREPANCY_REPORT](docs/AAA-10_DISCREPANCY_REPORT.md) | Drift-репорт между документацией и реальностью |
| 11 | [AAA-11_PRODUCTION_FIX_PLAN](docs/AAA-11_PRODUCTION_FIX_PLAN.md) | Pre-launch блокеры (ORD, FNS, etc.) |
| 12 | [AAA-12_CONTAINER_STARTUP_DEEP_DIVE](docs/AAA-12_CONTAINER_STARTUP_DEEP_DIVE.md) | Лайфцикл контейнеров, healthchecks |

| Resource | Description |
|----------|-------------|
| [QWEN.md](QWEN.md) | Developer context — финансовые константы, модели, сервис-контракты |
| [CHANGELOG.md](CHANGELOG.md) | Полная история версий (v4.2 → v4.5) |
| [reports/](reports/) | Sprint reports, discovery отчёты, CHANGES_*.md |
| [.qwen/skills/](.qwen/skills/) | 10 project-specific skills для AI-assisted разработки |

**Deep-dive documentation (Diátaxis framework):** подробная документация формата AAA обновляется через `docs-sync` skill после изменений в кодовой базе.

---

## 📝 License

[MIT License](LICENSE)

---

## 📞 Contacts

- **Repository:** https://github.com/rybkagreen/market-telegram-bot
- **Issues:** https://github.com/rybkagreen/market-telegram-bot/issues
- **Support:** @rekharbor_support (Telegram)
