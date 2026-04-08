# RekHarborBot — Telegram Advertising Exchange

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![SQLAlchemy 2](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://docs.sqlalchemy.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![v4.4](https://img.shields.io/badge/Version-4.4-orange.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**RekHarborBot** — Telegram-native рекламная биржа для каналов 1K–50K подписчиков. Платформа соединяет рекламодателей (малый и средний бизнес) с владельцами тематических каналов. Весь цикл — от выбора каналов до оплаты, публикации и аналитики — происходит внутри Telegram без перехода на сторонние сайты.

**Конкуренты:** Telega.in, Epicstars, TGStat. **Ключевое отличие:** Telegram-native, эскроу-защита, ИИ-генерация текстов, автоматическая ОРД-регистрация.

---

## 🆕 What's New in v4.4 (April 2026)

| # | Change | Impact |
|---|--------|--------|
| 1 | **Web Portal** — React SPA, 137 TSX files | Второй фронтенд помимо Mini App |
| 2 | **6 critical security fixes** | Rate limiting, banned-user checks, webhook error handling |
| 3 | **SonarQube: 580 files scanned** | src + mini_app + web_portal |
| 4 | **~70 code quality improvements** | Accessibility, keyboard navigation, unused param cleanup |
| 5 | **Billing prices from settings** | 490/1490/4990 вместо хардкода |
| 6 | **Telegram widget 500 fix** | Migration `t1u2v3w4x5y6` |

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
- ✅ Выплаты 85% владельцу, 15% комиссия платформы
- ✅ Репутация 0–10, система отзывов, реферальная программа

---

## 💰 Financial Model v4.2

- **1 кредит = 1 RUB** (виртуальная единица)
- **Комиссия платформы:** 15% с размещения
- **Владелец получает:** 85% от размещения
- **Налог:** ИП УСН 6%

| Сбор | Размер | Кто платит |
|------|--------|------------|
| Комиссия платформы | 15% | Удерживается из размещения |
| ЮKassa fee | 3.5% | Пользователь при пополнении |
| Вывод средств | 1.5% | Владелец при выплате |

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
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Telegram    │   │  Mini App    │   │  Web Portal  │
│  Bot (poll)  │   │  (React SPA) │   │  (React SPA) │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       └──────────────────┼──────────────────┘
                          │
               ┌──────────▼──────────┐
               │   FastAPI Router    │
               │  (JWT via Tg Auth)  │
               └──────────┬──────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────┐         ┌─────▼────┐         ┌──────▼──────┐
│aiogram │         │ Celery   │         │ Parser      │
│Handlers│         │ Workers  │         │ (Telethon)  │
│(FSM)   │         │ 3 queues │         │ (read-only) │
└───┬────┘         └─────┬────┘         └──────┬──────┘
    └─────────────────────┼─────────────────────┘
                          │
               ┌──────────▼──────────┐
               │   Service Layer     │
               └──────────┬──────────┘
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────────┐   ┌───────▼──────┐   ┌──────────▼────────┐
│ PostgreSQL  │   │   Redis 7    │   │   Mistral AI SDK  │
│ (asyncpg)   │   │ FSM+Broker   │   │   (AI generation) │
└────────────┘   └──────────────┘   └───────────────────┘
```

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| Bot | aiogram 3.x | Команды, FSM-диалоги, middlewares |
| Mini App | React 19 + TypeScript + Vite | Telegram WebApp интерфейс |
| Web Portal | React 19 + TypeScript + Vite | Полноценный веб-портал (v4.4) |
| API | FastAPI | JWT auth через Telegram initData HMAC-SHA256 |
| Workers | Celery + Beat | 3 очереди: critical, background, monitoring |
| DB | PostgreSQL 16 + SQLAlchemy 2.0 async | 32 миграции, repository pattern |
| Cache | Redis 7 | FSM storage, rate limiting, AI cache |
| AI | Mistral AI (mistralai>=1.12.4) | Генерация текстов, контент-фильтр |
| Payments | ЮKassa | Пополнение баланса (карта, СБП) |

---

## 🛠️ Tech Stack

**Backend:** Python 3.13 · aiogram 3.x · SQLAlchemy 2.0 async · FastAPI 0.115+ · Alembic 1.14+ · Celery 5.x · asyncpg 0.30+ · pydantic-settings 2.7+ · mistralai 1.12.4+ · Telethon 1.36+ · pymorphy3 2.0+ · yookassa 3.2.0 · reportlab 4.3+

**Frontend (Mini App + Web Portal):** React 19 · TypeScript 5.9/6.0 · Vite 5/8 · TailwindCSS 3/4 · Zustand 4.x · Recharts 2.x · react-router-dom 6.x · @twa-dev/sdk 7.x · CSS Modules

**DevOps & Tools:** Docker Compose · nginx · Cloudflare Tunnel · GitHub Actions · GlitchTip + Sentry · SonarQube · Gitleaks · Ruff · MyPy · pytest + testcontainers · Flower · Grafana

---

## 🚀 Quick Start

### Requirements

- **Python 3.13** (через pyenv)
- **Poetry** (менеджер зависимостей)
- **Docker** (PostgreSQL 16, Redis 7)
- **Node.js 20+** (для Mini App / Web Portal)

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

# 4. Apply migrations (32 migrations as of v4.4)
make migrate   # or: poetry run alembic upgrade head

# 5. Run bot (polling mode for development)
make run       # or: poetry run python -m src.bot.main

# 6. Run Celery workers
celery -A src.tasks.celery_app worker -Q critical,background,monitoring -l info

# 7. Run Celery Beat (periodic tasks — ONE instance only)
celery -A src.tasks.celery_app beat -l info

# 8. Mini App (optional)
cd mini_app && npm install && npm run dev

# 9. Web Portal (optional, v4.4)
cd web_portal && npm install && npm run dev
```

> **Bot token:** Получить у [@BotFather](https://t.me/BotFather). **Mistral API:** [console.mistral.ai](https://console.mistral.ai). **ЮKassa:** merchant dashboard.

---

## 📁 Project Structure

```
market-telegram-bot/
├── src/
│   ├── bot/              # aiogram handlers, keyboards, FSM states, middlewares
│   ├── api/              # FastAPI routers, JWT auth, dependencies
│   ├── db/               # SQLAlchemy models, repositories, Alembic migrations
│   ├── core/             # Business logic services, exceptions, constants
│   ├── tasks/            # Celery tasks, Beat schedule, config
│   ├── utils/            # Telegram sender, parser, content filter
│   └── config/           # Pydantic settings
├── mini_app/             # Telegram Mini App (React 19, TS, Vite)
├── web_portal/           # Web Portal (React 19, TS, Vite) — v4.4
├── tests/                # pytest unit + integration tests (101 tests)
├── docs/                 # Technical documentation, reports
├── .qwen/skills/         # 10 project-specific skills для Qwen Code
├── docker-compose.yml    # Production services definition
├── nginx/                # Reverse proxy, HTTPS config
└── scripts/              # Utility scripts (DB cleanup, etc.)
```

---

## 🗄️ Database

**32 Alembic migrations** (head: `s31a001_document_uploads`). Модели описаны подробно в [QWEN.md](QWEN.md#database-models).

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
poetry run pytest tests/ -v           # all 101 tests
poetry run pytest --cov=src           # coverage gate ≥80%

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
| **SonarQube** | Статический анализ кода (580 файлов) | SonarQube dashboard |
| **Flower** | Celery task monitoring | `:5555` |
| **Grafana** | Метрики приложения | `:3000` |
| **Gitleaks** | Secrets detection в git (pre-commit + CI) | `.gitleaks.toml` |

---

## 📚 Documentation

| Resource | Description |
|----------|-------------|
| [QWEN.md](QWEN.md) | Developer context — финансовые константы, модели, сервис-контракты, FSM states, архитектурные правила |
| [CHANGELOG.md](CHANGELOG.md) | Полная история версий (v4.2 → v4.4) |
| [docs/](docs/) | Технические отчёты, code review, deployment checklists |
| [reports/](reports/) | Sprint reports, tech debt registry |
| [.qwen/skills/](.qwen/skills/) | 10 project-specific skills для AI-assisted разработки |

**Deep-dive documentation (Diátaxis framework):** подробная документация формата AAA создаётся через `docs-sync` skill после изменений в кодовой базе.

---

## 📝 License

[MIT License](LICENSE)

---

## 📞 Contacts

- **Repository:** https://github.com/rybkagreen/market-telegram-bot
- **Issues:** https://github.com/rybkagreen/market-telegram-bot/issues
- **Support:** @rekharbor_support (Telegram)
