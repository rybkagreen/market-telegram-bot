# Market Telegram Bot — Платформа рекламных рассылок в Telegram

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![SQLAlchemy 2](https://img.shields.io/badge/SQLAlchemy-2-red.svg)](https://docs.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Market Telegram Bot** — это SaaS-платформа для автоматизированной рекламы в русскоязычных Telegram-сообществах. Пользователи создают рекламные кампании, пополняют баланс, настраивают таргетинг, а бот автономно находит подходящие публичные чаты и транслирует рекламу.

---

## 📋 Оглавление

- [Возможности](#-возможности)
- [Архитектура](#-архитектура)
- [Стек технологий](#-стек-технологий)
- [Быстрый старт](#-быстрый-старт)
- [Структура проекта](#-структура-проекта)
- [База данных](#-база-данных)
- [Контент-фильтр](#-контент-фильтр)
- [Система кредитов](#-система-кредитов)
- [Тарифы](#-тарифы)
- [Админ-панель](#-админ-панель)
- [Защита от бана](#-защита-от-бана)
- [Разработка](#-разработка)
- [Git Workflow](#-git-workflow)
- [Деплой](#-деплой)
- [Мониторинг](#-мониторинг)
- [Лицензия](#-лицензия)

---

## ✨ Возможности

### Для пользователей

- ✅ **Создание кампаний** — мастер из 7 шагов (тематика, заголовок, текст, изображение, размер аудитории, расписание, подтверждение)
- ✅ **ИИ-генерация текстов** — Claude Sonnet 4.6 через OpenRouter (A/B тестирование, 3 варианта)
- ✅ **Таргетинг** — по тематикам (15+ категорий), размеру чатов (от 50 до 1M+ подписчиков)
- ✅ **Планирование** — запуск немедленно или по расписанию
- ✅ **Аналитика** — статистика кампаний, охваты, конверсии, ROI
- ✅ **Баланс и оплата** — кредиты (1 кр = 1₽), CryptoBot (USDT, TON, BTC), Telegram Stars
- ✅ **Тарифы** — FREE, STARTER, PRO, BUSINESS с разными лимитами
- ✅ **Mini App** — веб-интерфейс на React для управления кампаниями

### Для администраторов

- ✅ **Управление пользователями** — просмотр, бан/разбан, изменение баланса
- ✅ **Модерация кампаний** — 3-уровневый контент-фильтр (regex → pymorphy3 → LLM)
- ✅ **Статистика платформы** — пользователи, кампании, выручка
- ✅ **Бесплатные кампании** — запуск от имени админа (для тестов)
- ✅ **Broadcast** — рассылка всем пользователям

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Market Telegram Bot                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Telegram    │    │   Mini App   │    │   Admin Panel │              │
│  │  Bot (poll)  │    │  (React SPA) │    │  (aiogram)   │              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                       │
│         └───────────────────┼───────────────────┘                       │
│                             │                                           │
│                  ┌──────────▼──────────┐                               │
│                  │   FastAPI Router    │                               │
│                  │   (JWT via Tg Auth) │                               │
│                  └──────────┬──────────┘                               │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                       │
│         │                   │                   │                       │
│  ┌──────▼───────┐   ┌──────▼───────┐   ┌──────▼───────┐               │
│  │  aiogram     │   │  Celery      │   │  Parser      │               │
│  │  Handlers    │   │  Workers     │   │  (Telethon)  │               │
│  │  (FSM)       │   │  (mailing)   │   │  (250+ queries)│              │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘               │
│         │                   │                   │                       │
│         └───────────────────┼───────────────────┘                       │
│                             │                                           │
│                  ┌──────────▼──────────┐                               │
│                  │   Service Layer     │                               │
│                  │  (Business Logic)   │                               │
│                  └──────────┬──────────┘                               │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                       │
│         │                   │                   │                       │
│  ┌──────▼───────┐   ┌──────▼───────┐   ┌──────▼───────┐               │
│  │  PostgreSQL  │   │    Redis     │   │   OpenRouter │               │
│  │  (asyncpg)   │   │  (FSM+Cache) │   │   (Claude)   │               │
│  └──────────────┘   └──────────────┘   └──────────────┘               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Компоненты

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Bot** | aiogram 3.x | Обработка команд, FSM диалоги |
| **Mini App** | React 19 + TypeScript | Веб-интерфейс (Telegram WebApp) |
| **API** | FastAPI | JWT аутентификация через Telegram initData |
| **Parser** | Telethon | Поиск и парсинг Telegram каналов (250+ запросов) |
| **Workers** | Celery + Beat | Асинхронные задачи (рассылки, парсинг, очистка) |
| **DB** | PostgreSQL 16 | Хранение данных (SQLAlchemy 2 async) |
| **Cache** | Redis 7 | FSM storage, rate limiting, AI кэш |
| **AI** | OpenRouter (Claude Sonnet 4.6) | Генерация текстов, контент-фильтр L3 |
| **Payments** | CryptoBot, Telegram Stars | Пополнение баланса в кредитах |

---

## 🛠️ Стек технологий

### Backend

| Категория | Технология | Версия |
|-----------|------------|--------|
| **Язык** | Python | 3.13 |
| **Bot Framework** | aiogram | 3.x |
| **ORM** | SQLAlchemy | 2.x (async) |
| **DB Driver** | asyncpg | 0.30+ |
| **Migration** | Alembic | 1.14+ |
| **Task Queue** | Celery + Beat | 5.x |
| **Cache/Broker** | Redis | 7 |
| **API** | FastAPI + uvicorn | 0.115+ |
| **Settings** | pydantic-settings | 2.7+ |
| **AI** | openai (OpenRouter) | 1.12+ |
| **Parser** | Telethon | 1.36+ |
| **Content Filter** | pymorphy3, rapidfuzz | 2.0+, 3.6+ |
| **Payments** | yookassa, cryptobot | 3.2+ |
| **Monitoring** | sentry-sdk | 2.53+ |
| **PDF Reports** | reportlab | 4.3+ |

### Frontend (Mini App)

| Категория | Технология | Версия |
|-----------|------------|--------|
| **Framework** | React | 19 |
| **Language** | TypeScript | 5.x |
| **Build** | Vite | 5.x |
| **Styling** | TailwindCSS | 3.x |
| **Charts** | Recharts | 2.x |
| **State** | Zustand | 4.x |
| **Routing** | react-router-dom | 6.x |
| **Telegram SDK** | @twa-dev/sdk | 7.x |

### DevOps & Tools

| Категория | Инструмент | Назначение |
|-----------|------------|------------|
| **Containerization** | Docker + Compose | Локальная разработка, production |
| **Web Server** | nginx | HTTPS, reverse proxy |
| **Tunnel** | Cloudflare Tunnel | HTTPS для Mini App (бесплатно) |
| **CI/CD** | GitHub Actions | Lint+test на PR, deploy на main |
| **Monitoring** | Sentry, Grafana, Flower | Ошибки, метрики, Celery dashboard |
| **Testing** | pytest, testcontainers | Unit + integration тесты |
| **Linting** | ruff, mypy | Code style + type checking |
| **Pre-commit** | pre-commit, detect-secrets | Автоматические проверки |

---

## 🚀 Быстрый старт

### Требования

- **Python 3.13** (управляется через pyenv)
- **Poetry** (менеджер зависимостей)
- **Docker Desktop** (PostgreSQL, Redis)
- **Node.js 20+** (для Mini App, опционально)

### Установка

#### 1. Клонировать репозиторий

```bash
git clone https://github.com/rybkagreen/market-telegram-bot.git
cd market-telegram-bot
```

#### 2. Установить зависимости

```bash
poetry install
```

#### 3. Настроить окружение

```bash
cp .env.example .env
# Отредактировать .env:
# - BOT_TOKEN (от @BotFather)
# - DATABASE_URL (postgresql+asyncpg://...)
# - REDIS_URL (redis://...)
# - OPENROUTER_API_KEY (для ИИ)
# - ADMIN_IDS (Telegram ID админов)
```

**Минимальный `.env` для разработки:**

```env
# Telegram Bot
BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP

# Database
POSTGRES_USER=market_bot
POSTGRES_PASSWORD=market_bot_pass
POSTGRES_DB=market_bot_db
DATABASE_URL=postgresql+asyncpg://market_bot:market_bot_pass@localhost:5432/market_bot_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI (OpenRouter)
OPENROUTER_API_KEY=sk-or-...

# Admin IDs (ваш Telegram ID)
ADMIN_IDS=123456789

# Environment
ENVIRONMENT=development
DEBUG=true
```

#### 4. Запустить инфраструктуру

```bash
docker compose up -d postgres redis
```

Проверить:

```bash
docker compose ps
# postgres: healthy
# redis: healthy
```

#### 5. Применить миграции

```bash
make migrate
# или вручную:
poetry run alembic upgrade head
```

#### 6. Запустить бота (development)

```bash
make run
# или:
poetry run python -m src.bot.main
```

Бот запущен в режиме **polling** (для production используется webhook).

---

## 📁 Структура проекта

```
market-telegram-bot/
├── src/
│   ├── bot/                      # aiogram бот
│   │   ├── handlers/             # обработчики команд
│   │   │   ├── admin.py          # админ-панель
│   │   │   ├── start.py          # /start, регистрация
│   │   │   ├── campaigns.py      # создание кампаний
│   │   │   ├── billing.py        # оплата, тарифы
│   │   │   ├── cabinet.py        # личный кабинет
│   │   │   └── ...
│   │   ├── keyboards/            # inline клавиатуры
│   │   │   ├── admin.py          # админские кнопки
│   │   │   ├── billing.py        # оплата
│   │   │   └── ...
│   │   ├── states/               # FSM состояния
│   │   │   ├── admin.py          # состояния админки
│   │   │   └── campaign.py       # мастер кампании
│   │   ├── filters/              # кастомные фильтры
│   │   │   └── admin.py          # AdminFilter
│   │   └── middlewares/          # middleware
│   │       └── throttling.py     # rate limiting
│   │
│   ├── api/                      # FastAPI для Mini App
│   │   ├── routers/
│   │   │   ├── auth.py           # JWT auth via Telegram
│   │   │   ├── billing.py        # API оплаты
│   │   │   └── analytics.py      # API аналитики
│   │   ├── constants/            # централизованные константы
│   │   │   ├── tariffs.py        # тарифы и лимиты
│   │   │   ├── payments.py       # платёжные константы
│   │   │   ├── parser.py         # поисковые запросы (~400)
│   │   │   ├── celery.py         # Celery расписание
│   │   │   ├── limits.py         # ограничения по тарифам
│   │   │   └── content_filter.py # пороги фильтра
│   │   └── dependencies.py       # FastAPI зависимости
│   │
│   ├── db/                       # работа с БД
│   │   ├── models/               # SQLAlchemy модели
│   │   │   ├── user.py           # User (credits, plan)
│   │   │   ├── campaign.py       # Campaign (статусы, фильтры)
│   │   │   ├── chat.py           # TelegramChat (language, russian_score)
│   │   │   ├── transaction.py    # Transaction (topup/spend)
│   │   │   └── ...
│   │   ├── repositories/         # Repository pattern
│   │   │   ├── base.py           # BaseRepository[T]
│   │   │   ├── user_repo.py      # UserRepository
│   │   │   └── ...
│   │   └── migrations/           # Alembic миграции
│   │
│   ├── core/                     # бизнес-логика
│   │   └── services/
│   │       ├── ai_service.py     # ИИ-генерация (OpenRouter)
│   │       ├── billing_service.py# платежи, кредиты
│   │       ├── mailing_service.py# рассылки
│   │       └── notification_service.py # уведомления
│   │
│   ├── tasks/                    # Celery задачи
│   │   ├── celery_app.py         # конфигурация Celery
│   │   ├── mailing_tasks.py      # рассылки
│   │   ├── parser_tasks.py       # парсинг каналов
│   │   ├── billing_tasks.py      # продление тарифов
│   │   └── cleanup_tasks.py      # очистка старых данных
│   │
│   ├── utils/                    # утилиты
│   │   ├── telegram/
│   │   │   ├── parser.py         # Telethon parser
│   │   │   ├── sender.py         # отправка сообщений
│   │   │   ├── topic_classifier.py # классификатор тем
│   │   │   └── russian_lang_detector.py # детектор русского языка
│   │   └── content_filter/
│   │       ├── filter.py         # 3-уровневый фильтр
│   │       └── stopwords_ru.json # стоп-слова (8 категорий)
│   │
│   └── config/
│       └── settings.py           # Pydantic Settings
│
├── mini_app/                     # Telegram Mini App
│   ├── src/
│   │   ├── components/           # React компоненты
│   │   ├── pages/                # страницы (/campaigns, /analytics)
│   │   ├── hooks/                # custom hooks
│   │   ├── store/                # Zustand store
│   │   └── main.tsx              # entry point
│   └── dist/                     # build output → src/static/mini_app/
│
├── tests/
│   ├── unit/                     # unit-тесты
│   │   ├── test_content_filter.py
│   │   └── test_ai_service.py
│   └── integration/              # integration-тесты (testcontainers)
│       ├── test_user_repo.py
│       └── test_campaign_repo.py
│
├── docker/                       # Docker конфигурации
│   ├── Dockerfile.bot
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── Dockerfile.nginx
│   └── nginx.conf
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                # lint+test на PR
│   │   └── deploy.yml            # deploy на main
│   └── CODEOWNERS                # владельцы кода
│
├── docker-compose.yml            # local development
├── Makefile                      # make команды
├── pyproject.toml                # Poetry зависимости
└── README.md                     # этот файл
```

---

## 🗄️ База данных

### Основные модели

#### User (Пользователи)

```python
class User(Base):
    id: int                      # PK
    telegram_id: int             # UNIQUE, BIGINT
    username: str | None
    first_name: str | None
    credits: int                 # баланс в кредитах (1 кр = 1₽), CHECK >= 0
    plan: UserPlan               # FREE/STARTER/PRO/BUSINESS
    plan_expires_at: datetime    # когда истекает тариф
    ai_generations_used: int     # счётчик ИИ в текущем месяце
    referral_code: str           # уникальный реф. код
    is_banned: bool              # забанен ли
    is_active: bool              # активен ли
    language: str                # "ru" (по умолчанию)
    russian_score: float         # 1.0 (по умолчанию)
```

#### Campaign (Кампании)

```python
class Campaign(Base):
    id: int                      # PK
    user_id: int                 # FK → User
    title: str
    text: str
    status: CampaignStatus       # draft/queued/running/done/error/paused/banned
    filters_json: dict           # {topics, min_members, max_members}
    scheduled_at: datetime | None
    cost: Decimal                # стоимость в кредитах, CHECK >= 0
    total_chats: int             # всего чатов
    sent_count: int              # отправлено
    failed_count: int            # ошибок
```

#### TelegramChat (Каналы для рассылок)

```python
class TelegramChat(Base):
    id: int                      # PK
    telegram_id: int             # UNIQUE, BIGINT
    username: str                # UNIQUE
    title: str
    description: str | None
    member_count: int            # количество подписчиков
    topic: str | None            # тематика
    subcategory: str | None      # подкатегория
    rating: float                # 0-10
    language: str                # "ru", "en", "mixed", "unknown"
    russian_score: float         # 0.0-1.0
    is_active: bool              # активен ли
    is_blacklisted: bool         # в чёрном списке
    complaint_count: int         # количество жалоб
```

#### Transaction (Транзакции)

```python
class Transaction(Base):
    id: int                      # PK
    user_id: int                 # FK → User
    amount: Decimal              # сумма в рублях, CHECK > 0
    type: TransactionType        # topup/spend/bonus/adjustment
    payment_id: str | None       # ID в платёжной системе, UNIQUE
    meta_json: dict              # {credits, description, ...}
    created_at: datetime
```

### Целостность базы данных

**Check Constraints:**
- `ck_users_credits_positive` — `credits >= 0`
- `ck_users_balance_positive` — `balance >= 0`
- `ck_campaigns_cost_positive` — `cost >= 0`
- `ck_transactions_amount_positive` — `amount > 0`

**Unique Constraints:**
- `uq_users_telegram_id` — `users.telegram_id`
- `uq_users_referral_code` — `users.referral_code`
- `uq_transactions_payment_id` — `transactions.payment_id`
- `uq_mailing_logs_campaign_chat` — `(campaign_id, chat_telegram_id)`

**Foreign Keys с CASCADE:**
- `campaigns.user_id` → `users.id` (ON DELETE CASCADE)
- `transactions.user_id` → `users.id` (ON DELETE CASCADE)
- `mailing_logs.campaign_id` → `campaigns.id` (ON DELETE CASCADE)
- `mailing_logs.chat_id` → `telegram_chats.id` (ON DELETE SET NULL)

**Индексы:**
- `ix_users_telegram_id` — поиск по Telegram ID
- `ix_campaigns_user_status` — фильтрация кампаний по пользователю и статусу
- `ix_campaigns_status` — фильтрация по статусу
- `ix_transactions_user_type` — фильтрация транзакций по типу
- `ix_mailing_logs_status_campaign` — фильтрация логов по статусу

---

### Миграции

**Alembic** управляет миграциями базы данных.

```bash
# Создать новую миграцию
poetry run alembic revision --autogenerate -m "description"

# Применить все миграции
poetry run alembic upgrade head

# Откатить на 1 миграцию
poetry run alembic downgrade -1

# Проверить статус
poetry run alembic current

# Показать историю миграций
poetry run alembic history
```

**Текущая миграция:** `8885dc6d508e (head)` — add_check_constraint_transactions_amount

**История миграций:**
```
<base> -> 0014 (Previous schema migration - placeholder)
0014 -> 0015 (Initial schema - create all tables)
0015 -> d58411813eee (add_check_constraints_users)
d58411813eee -> 49ba417be2a8 (add_check_constraint_campaigns_cost)
49ba417be2a8 -> 8885dc6d508e (add_check_constraint_transactions_amount) [HEAD]
```

**Check Constraints в БД:**
- `ck_users_credits_positive` — credits >= 0
- `ck_users_balance_positive` — balance >= 0
- `ck_campaigns_cost_positive` — cost >= 0
- `ck_transactions_amount_positive` — amount > 0

---

## 🛡️ Контент-фильтр

### 3-уровневая система проверки

```
Текст рекламы
    │
    ▼
┌─────────────────────────────────┐
│ Уровень 1: regex_check()        │  < 1ms
│ - Компилированные паттерны      │
│ - stop words из stopwords_ru.json│
│ - Score < 0.2 → PASS            │
└──────────────┬──────────────────┘
               │ Score >= 0.2
               ▼
┌─────────────────────────────────┐
│ Уровень 2: morph_check()        │  < 10ms
│ - pymorphy3 (все формы слов)   │
│ - Склонения, спряжения          │
│ - Score < 0.5 → PASS            │
└──────────────┬──────────────────┘
               │ Score >= 0.5
               ▼
┌─────────────────────────────────┐
│ Уровень 3: llm_check()          │  1-3 сек
│ - Claude API (OpenRouter)       │
│ - Контекстный анализ            │
│ - Score < 0.7 → PASS            │
└──────────────┬──────────────────┘
               │ Score >= 0.7
               ▼
         BLOCKED ❌
```

### 8 заблокированных категорий

1. **drugs** — наркотики
2. **terrorism** — терроризм
3. **weapons** — оружие
4. **adult** — контент 18+
5. **fraud** — мошенничество
6. **suicide** — суицид
7. **extremism** — экстремизм
8. **gambling** — азартные игры

### Использование

```python
from src.utils.content_filter.filter import check as content_filter_check

result = content_filter_check("Текст рекламы")

if not result.passed:
    print(f"Заблокировано: {', '.join(result.categories)}")
    print(f"Фрагменты: {result.flagged_fragments}")
else:
    print("Текст прошёл проверку")
```

---

## 💰 Система кредитов

### Конвертация валют в кредиты

| Валюта | Кредитов за 1 единицу |
|--------|----------------------|
| **USDT** | 90 кр |
| **TON** | 400 кр |
| **BTC** | 9 000 000 кр |
| **ETH** | 300 000 кр |
| **LTC** | 7 000 кр |
| **Telegram Stars** | 2 кр за 1 ⭐ |

**1 кредит = 1 рублю** (виртуальная единица для упрощения расчётов).

### Пополнение баланса

```python
# Через CryptoBot
from src.core.services.cryptobot_service import cryptobot_service

invoice = await cryptobot_service.create_invoice(
    currency="USDT",
    amount=10.0,  # 10 USDT = 900 кр
    payload=f"user:{user_id}:credits:900",
)

# Через Telegram Stars
await bot.send_invoice(
    currency="XTR",  # Stars
    prices=[LabeledPrice(label="Кредиты", amount=50)],  # 50 ⭐ = 100 кр
)
```

### Списание кредитов

```python
# Оплата тарифа
await user_repo.update_credits(user_id, -999)  # PRO тариф

# Оплата кампании
await user_repo.update_credits(user_id, -100)  # 100 кр за кампанию

# ИИ-генерация (если превышен лимит)
await user_repo.update_credits(user_id, -10)  # 10 кр за генерацию
```

---

## 📦 Тарифы

| Тариф | Цена | Кампаний/мес | Чатов/кампанию | ИИ-генераций | Лимит подписчиков |
|-------|------|--------------|----------------|--------------|-------------------|
| **FREE** | 0 кр/мес | 0 | 0 | 0 | до 10K |
| **STARTER** | 299 кр/мес | 5 | 50 | за кредиты | до 50K |
| **PRO** | 999 кр/мес | 20 | 200 | 5 включено | до 200K |
| **BUSINESS** | 2999 кр/мес | 100 | 1000 | 20 включено | безлимит |

### Продление тарифа

Тариф продлевается **автоматически** каждые 30 дней. Если на балансе недостаточно кредитов — тариф сбрасывается на **FREE**.

```python
# src/tasks/billing_tasks.py
@celery_app.task(name="billing:check_plan_renewals")
def check_plan_renewals():
    # Проверка истекающих тарифов
    # Списывание кредитов
    # Продление или сброс на FREE
```

---

## 🔐 Админ-панель

### Доступные функции

- **Статистика платформы** — пользователи, кампании, выручка
- **Управление пользователями**:
  - Просмотр списка (пагинация)
  - Бан/разбан (кнопка в профиле)
  - Изменение баланса (пополнение/списание)
- **ИИ-генерация кампании** — создание от имени админа (бесплатно)
- **Broadcast** — рассылка всем пользователям
- **Контент-фильтр** — ручная модерация спорных случаев

### Вход в админку

```python
# Команда /admin (доступно только ADMIN_IDS)
/admin

# Через главное меню (кнопка "🔐 Админ-панель")
```

### Исправленные функции (Март 2026)

- ✅ **`toggle_ban`** — быстрый бан/разбан из профиля
- ✅ **`edit_balance`** — изменение баланса из профиля
- ✅ **`/cancel`** — отмена текущего действия админа

---

## 🛡️ Защита от бана

### Приоритет 1: Реализовано

#### Обработка Telegram ошибок

```python
from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
)

async def send_message_safe(chat_id: int, message: str):
    try:
        await bot.send_message(chat_id, message)
        return SendResult(status="sent")
        
    except FloodWaitError as e:
        return SendResult(status="rate_limited", retry_after=e.seconds)
    
    except ChatWriteForbiddenError:
        chat.is_blacklisted = True
        return SendResult(status="chat_blocked")
    
    except UserBannedInChannelError:
        campaign.status = CampaignStatus.ACCOUNT_BANNED
        await notify_admins(f"🚫 Аккаунт забанен!")
        return SendResult(status="user_banned")
```

#### Статусы кампании

- `PAUSED` — пауза из-за FloodWait (>5 мин)
- `ACCOUNT_BANNED` — аккаунт забанен в Telegram

#### Лимиты и задержки

```python
MAILING_SETTINGS = {
    "delay_between_messages": 5,        # базовая задержка (сек)
    "random_delay_range": [3, 10],      # случайная вариация
    "max_per_minute": 10,
    "max_per_hour": 300,
    "max_per_day": 2000,
}
```

### Приоритет 2: В разработке

#### Система жалоб

```python
class TelegramChat(Base):
    complaint_count: int         # количество жалоб
    is_blacklisted: bool         # в чёрном списке
    blacklisted_reason: str      # причина блокировки
```

**Пороги:**
- **3 жалобы** — пауза 24 часа
- **10 жалоб** — чёрный список навсегда

**Пороги контент-фильтра:**
- **LEVEL1_THRESHOLD = 0.2** — если score > 0.2, переходим на уровень 2 (morph)
- **LEVEL2_THRESHOLD = 0.5** — если score > 0.5, переходим на уровень 3 (LLM)
- **LEVEL3_THRESHOLD = 0.7** — если LLM score > 0.7, контент блокируется

#### Автоматическая блокировка чатов

```python
if chat.complaint_count >= 10:
    chat.is_blacklisted = True
    chat.blacklisted_reason = "Too many complaints"
```

### Приоритет 3: План

- [ ] Дашборд здоровья рассылок для админа
- [ ] Уведомления пользователей о статусе кампании
- [ ] Аналитика успешности по чатам

---

## 👨‍💻 Разработка

### Требования

- Python 3.13 (pyenv)
- Poetry
- Docker Desktop
- Node.js 20+ (опционально, для Mini App)

### Установка зависимостей

```bash
poetry install
```

### Запуск бота (development)

```bash
# Запустить PostgreSQL + Redis
docker compose up -d postgres redis

# Применить миграции
make migrate

# Запустить бота (polling)
make run
```

### Запуск Celery workers

```bash
# Worker (mailing, parser очереди)
celery -A src.tasks.celery_app worker --loglevel=info -Q mailing,parser

# Beat (периодические задачи)
celery -A src.tasks.celery_app beat --loglevel=info

# Flower (мониторинг Celery)
celery -A src.tasks.celery_app flower --port=5555
```

### Запуск Mini App (development)

```bash
cd mini_app
npm install
npm run dev
# Прокси на /api → http://localhost:8001
```

### Тестирование

```bash
# Unit тесты
poetry run pytest tests/unit/

# Integration тесты (testcontainers)
poetry run pytest tests/integration/

# Покрытие
poetry run pytest --cov=src --cov-report=html
```

---

## 🔀 Git Workflow

Проект использует **упрощённый Git Flow**:

```
main ────────────────●───────────────→ production (стабильные релизы)
                      ╲
develop ──────────────●──────────────→ integration (фичи сливаются сюда)
                       ╲
feature/* ─────────────●─────────────→ временные ветки для задач
```

### Ветки

| Ветка | Назначение | Защита |
|-------|------------|--------|
| `main` | Production релизы | 🔒 PR + 1 review |
| `develop` | Integration фич | 🔒 PR + 1 review |
| `developer/*` | Ветки разработчиков | ⚠️ CI при PR |
| `feature/*` | Временные фичи | ⚠️ CI при PR |

### Процесс разработки

1. **Создать ветку от `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature
   ```

2. **Внести изменения и закоммитить:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. **Отправить и создать PR:**
   ```bash
   git push origin feature/your-feature
   ```
   
   Создать PR: `feature/*` → `develop`

4. **Code Review:**
   - Минимум 1 approval
   - Все CI чеки проходят (lint, typecheck, test)

5. **Merge в `develop`** → тестирование → PR в `main`

### Conventional Commits

```
feat(scope): short description
fix(scope): short description
refactor(scope): ...
test(scope): ...
docs(scope): ...
chore(scope): ...
```

**Примеры:**
- `feat(parser): add Russian language detector`
- `fix(admin): toggle_ban callback handler`
- `refactor(billing): migrate to credits system`

---

## 🚀 Деплой

### Production (timeweb.cloud)

**Инфраструктура:**
- Ubuntu 22.04
- Docker Compose
- nginx (443 HTTPS, certbot)
- Cloudflare Tunnel (для Mini App)

**Сервисы:**
- `bot` — aiogram (webhook)
- `worker` — Celery workers
- `api` — FastAPI uvicorn
- `postgres:16` — база данных
- `redis:7` — кэш + брокер
- `flower` — Celery мониторинг
- `grafana` — метрики
- `nginx` — reverse proxy

**Деплой через GitHub Actions:**

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to timeweb
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_IP }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/market-telegram-bot
            git pull origin main
            docker compose pull
            docker compose up -d --no-deps
```

**Ручной деплой:**

```bash
# На сервере
cd /opt/market-telegram-bot
git pull origin main
docker compose pull
docker compose up -d --no-deps
```

### Переменные окружения (production)

```env
ENVIRONMENT=production
DEBUG=false

BOT_TOKEN=...
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
REDIS_URL=redis://redis:6379/0

OPENROUTER_API_KEY=...
CRYPTOBOT_TOKEN=...

WEBHOOK_URL=https://yourdomain.com/webhook
MINI_APP_URL=https://yourdomain.com/app

ADMIN_IDS=123456789
SENTRY_DSN=https://...@sentry.io/...
```

---

## 📊 Мониторинг

### Sentry (ошибки)

```python
# src/bot/main.py
import sentry_sdk

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    environment=settings.environment,
    traces_sample_rate=0.1,
)
```

**Дашборд:** https://sentry.io/organizations/your-org/

### Grafana (метрики)

**Метрики:**
- Количество пользователей
- Активные кампании
- Отправлено сообщений
- Ошибки рассылок
- Rate limit срабатывания

**Дашборд:** http://localhost:3000 (Grafana)

### Flower (Celery)

**Мониторинг задач:**
- Активные воркеры
- Очереди (mailing, parser, cleanup)
- Выполненные задачи
- Ошибки

**Дашборд:** http://localhost:5555

---

## 📝 Лицензия

[MIT License](LICENSE)

---

## 📞 Контакты

- **Repository:** https://github.com/rybkagreen/market-telegram-bot
- **Issues:** https://github.com/rybkagreen/market-telegram-bot/issues
- **Support:** @marketbot_support (Telegram)

---

## 📚 Дополнительная документация

- [LOCAL_CHECKS.md](LOCAL_CHECKS.md) — локальные проверки кода
- [DOCKER_README.md](DOCKER_README.md) — Docker инструкция
- [CLOUDFLARE_SETUP.md](CLOUDFLARE_SETUP.md) — настройка Cloudflare Tunnel
- [EXPANDED_ANALYTICS_AND_TARIFFS_v2.md](EXPANDED_ANALYTICS_AND_TARIFFS_v2.md) — аналитика и тарифы
- [PARSER_REFACTORING_FINAL.md](PARSER_REFACTORING_FINAL.md) — рефакторинг парсера
- [SECURITY_ACTION.md](SECURITY_ACTION.md) — безопасность
- [QWEN.md](QWEN.md) — контекст проекта для Qwen Code
