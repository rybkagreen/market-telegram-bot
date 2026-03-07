# Market Telegram Bot — Структура проекта

> Полная документация архитектуры и структуры проекта Market Telegram Bot (RekHarbor)

---

## 📋 Содержание

1. [Обзор проекта](#обзор-проекта)
2. [Архитектура](#архитектура)
3. [Структура файлов](#структура-файлов)
4. [Основные компоненты](#основные-компоненты)
5. [База данных](#база-данных)
6. [Telegram Bot](#telegram-bot)
7. [API и Mini App](#api-и-mini-app)
8. [Celery задачи](#celery-задачи)
9. [Сервисы](#сервисы)
10. [Развёртывание](#развёртывание)

---

## Обзор проекта

**Market Telegram Bot (RekHarbor)** — SaaS-платформа для автоматизированной рекламы в русскоязычных Telegram-сообществах.

### Возможности

- **Для рекламодателей:**
  - Создание рекламных кампаний (вручную, через AI, из шаблонов)
  - Таргетинг по тематикам и количеству подписчиков
  - Автоматическая рассылка по подобранным каналам
  - Аналитика и отслеживание результатов

- **Для владельцев каналов:**
  - Регистрация своих Telegram-каналов
  - Монетизация через размещение рекламы
  - Управление заявками на размещение
  - Выплаты за публикации

- **Платформа:**
  - Кредитная система оплаты (USDT, TON, BTC, Stars)
  - Геймификация (уровни, XP, значки)
  - Реферальная программа
  - B2B-пакеты каналов

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx (443 HTTPS)                       │
│  /webhook → bot  |  /api → api  |  / → mini_app static         │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │   Bot   │          │   API   │          │ Worker  │
   │ aiogram │          │FastAPI  │          │ Celery  │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
        ┌─────▼─────┐                   ┌────▼────┐
        │ PostgreSQL│                   │  Redis  │
        │   16      │                   │    7    │
        └───────────┘                   └─────────┘
```

### Технологический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| **Язык** | Python | 3.13.7 |
| **Bot Framework** | aiogram | 3.x |
| **API** | FastAPI + Uvicorn | latest |
| **ORM** | SQLAlchemy | 2.0 async |
| **DB** | PostgreSQL | 16-alpine |
| **Cache/Queue** | Redis | 7-alpine |
| **Task Queue** | Celery + Beat | 5.x |
| **Mini App** | React + TypeScript | Vite |
| **Payments** | CryptoBot, Stars | - |
| **AI** | OpenRouter (Qwen, Step) | - |
| **Parser** | Telethon | 1.42.0 |
| **Monitoring** | Sentry, Flower | - |

---

## Структура файлов

```
market-telegram-bot/
├── src/
│   ├── bot/                          # aiogram бот
│   │   ├── handlers/                 # Обработчики команд
│   │   │   ├── start.py              # /start, онбординг
│   │   │   ├── cabinet.py            # Личный кабинет
│   │   │   ├── campaigns.py          # Создание кампаний
│   │   │   ├── campaign_create_ai.py # AI-создание кампаний
│   │   │   ├── channel_owner.py      # Управление каналами
│   │   │   ├── analytics.py          # Аналитика
│   │   │   ├── billing.py            # Биллинг и оплата
│   │   │   ├── admin.py              # Админ-панель
│   │   │   ├── feedback.py           # Обратная связь
│   │   │   ├── templates.py          # Шаблоны кампаний
│   │   │   └── stats.py              # Статистика платформы
│   │   │
│   │   ├── keyboards/                # Inline-клавиатуры
│   │   │   ├── main_menu.py          # Главное меню (роль-зависимое)
│   │   │   ├── cabinet.py            # Меню кабинета
│   │   │   ├── campaigns.py          # Меню кампаний
│   │   │   ├── channels.py           # Меню каналов
│   │   │   ├── billing.py            # Платежные клавиатуры
│   │   │   ├── analytics.py          # Аналитика
│   │   │   ├── admin.py              # Админ-панель
│   │   │   ├── feedback.py           # Обратная связь
│   │   │   └── pagination.py         # Пагинация
│   │   │
│   │   ├── states/                   # FSM состояния
│   │   │   ├── campaign.py           # Создание кампании
│   │   │   ├── channel_owner.py      # Добавление канала
│   │   │   ├── admin.py              # Админ-задачи
│   │   │   ├── feedback.py           # Обратная связь
│   │   │   └── onboarding.py         # Онбординг пользователя
│   │   │
│   │   ├── utils/                    # Утилиты бота
│   │   │   ├── safe_callback.py      # Безопасное редактирование
│   │   │   ├── message_utils.py      # Утилиты сообщений
│   │   │   └── decorators.py         # Декораторы
│   │   │
│   │   ├── assets/                   # Статические файлы
│   │   │   └── images/               # Изображения (баннеры)
│   │   │
│   │   └── main.py                   # Точка входа бота
│   │
│   ├── api/                          # FastAPI API
│   │   ├── routes/                   # API роуты
│   │   │   ├── auth.py               # JWT аутентификация
│   │   │   ├── campaigns.py          # API кампаний
│   │   │   ├── analytics.py          # API аналитики
│   │   │   └── billing.py            # API биллинга
│   │   ├── dependencies.py           # FastAPI зависимости
│   │   ├── main.py                   # Точка входа API
│   │   └── middleware/               # Middleware
│   │
│   ├── core/                         # Бизнес-логика
│   │   └── services/                 # Сервисы приложения
│   │       ├── ai_service.py         # AI генерация (OpenRouter)
│   │       ├── analytics_service.py  # Аналитика и статистика
│   │       ├── billing_service.py    # Биллинг и эскроу
│   │       ├── mailing_service.py    # Рассылки
│   │       ├── user_role_service.py  # Определение роли
│   │       ├── xp_service.py         # Геймификация (XP)
│   │       ├── badge_service.py      # Значки достижений
│   │       ├── notification_service.py # Уведомления
│   │       └── content_filter/       # Фильтр контента (3 уровня)
│   │
│   ├── db/                           # Работа с БД
│   │   ├── models/                   # SQLAlchemy модели
│   │   │   ├── user.py               # Пользователи
│   │   │   ├── campaign.py           # Кампании
│   │   │   ├── chat.py               # Чаты/каналы
│   │   │   ├── transaction.py        # Транзакции
│   │   │   ├── notification.py       # Уведомления
│   │   │   ├── analytics.py          # Аналитика
│   │   │   ├── payout.py             # Выплаты
│   │   │   └── mailing_log.py        # Логи рассылок
│   │   │
│   │   ├── repositories/             # Repository pattern
│   │   │   ├── base.py               # BaseRepository[T]
│   │   │   ├── user_repo.py          # UserRepository
│   │   │   ├── campaign_repo.py      # CampaignRepository
│   │   │   ├── chat_repo.py          # ChatRepository
│   │   │   └── log_repo.py           # MailingLogRepository
│   │   │
│   │   └── session.py                # AsyncSession factory
│   │
│   ├── tasks/                        # Celery задачи
│   │   ├── celery_app.py             # Настройка Celery
│   │   ├── mailing_tasks.py          # Задачи рассылок
│   │   ├── notification_tasks.py     # Задачи уведомлений
│   │   ├── parser_tasks.py           # Задачи парсера
│   │   ├── cleanup_tasks.py          # Задачи очистки
│   │   └── billing_tasks.py          # Биллинг задачи
│   │
│   ├── utils/                        # Общие утилиты
│   │   ├── telegram/                 # Telegram утилиты
│   │   │   ├── parser.py             # Парсинг каналов
│   │   │   ├── sender.py             # Отправка сообщений
│   │   │   └── topic_classifier.py   # Классификация тем
│   │   │
│   │   └── content_filter/           # 3-уровневый фильтр
│   │       ├── filter.py             # Основной фильтр
│   │       ├── regex_check.py        # Уровень 1: regex
│   │       ├── morph_check.py        # Уровень 2: pymorphy3
│   │       ├── llm_check.py          # Уровень 3: LLM
│   │       └── stopwords_ru.json     # Стоп-слова
│   │
│   └── config/                       # Конфигурация
│       └── settings.py               # Pydantic Settings
│
├── mini_app/                         # Telegram Mini App
│   ├── src/
│   │   ├── components/               # React компоненты
│   │   ├── pages/                    # Страницы
│   │   ├── stores/                   # Zustand stores
│   │   ├── api/                      # API client
│   │   └── utils/                    # Утилиты
│   ├── package.json
│   └── vite.config.ts
│
├── docker/                           # Docker конфигурации
│   ├── Dockerfile.bot
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── nginx.conf
│
├── tests/                            # Тесты
│   ├── unit/                         # Unit тесты
│   └── integration/                  # Integration тесты
│
├── docker-compose.yml                # Development
├── docker-compose.prod.yml           # Production
├── pyproject.toml                    # Poetry зависимости
├── alembic.ini                       # Миграции БД
└── .env.example                      # Пример переменных
```

---

## Основные компоненты

### 1. Bot (aiogram 3.x)

**Точка входа:** `src/bot/main.py`

```python
# Webhook режим (production)
# Polling режим (development)

# Middleware:
# - Sentry logging
# - Error handling
# - User context
# - FSM storage (Redis)
```

**Обработчики команд:**

| Handler | Команды | Callbacks | Описание |
|---------|---------|-----------|----------|
| `start.py` | /start, /help | main_menu, onboarding | Онбординг, главное меню |
| `cabinet.py` | /cabinet | cabinet.* | Личный кабинет, геймификация |
| `campaigns.py` | /campaigns | create_*, campaign_* | Создание кампаний (manual) |
| `campaign_create_ai.py` | - | ai_campaign_* | AI-создание кампаний |
| `channel_owner.py` | /my_channels, /add_channel | channel_*, payout_* | Управление каналами |
| `analytics.py` | /analytics | analytics_* | Аналитика кампаний |
| `billing.py` | /balance | billing_*, crypto_* | Пополнение, тарифы |
| `admin.py` | /admin | admin_* | Админ-панель |
| `feedback.py` | - | feedback_* | Обратная связь |

**FSM States:**

```python
# CampaignStates: waiting_title → waiting_text → waiting_topic → ...
# AddChannelStates: waiting_username → waiting_price → ...
# OnboardingStates: role_selected
# FeedbackStates: waiting_message → waiting_confirm
# AdminStates: ban_user, broadcast, ai_generate, ...
```

---

### 2. API (FastAPI)

**Точка входа:** `src/api/main.py`

```python
# Port: 8001
# Auth: JWT через Telegram initData
# CORS: настроено для Mini App
```

**Маршруты:**

| Route | Method | Описание |
|-------|--------|----------|
| `/api/auth/login` | POST | JWT login через initData |
| `/api/campaigns` | GET/POST | CRUD кампаний |
| `/api/analytics` | GET | Статистика кампаний |
| `/api/billing` | GET/POST | Биллинг операции |

---

### 3. Celery Tasks

**Очереди:** `mailing`, `parser`, `cleanup`, `default`

**Задачи:**

```python
# mailing.*
- send_campaign(campaign_id)      # Отправка кампании
- check_scheduled_campaigns()     # Проверка запланированных (каждые 5 мин)
- check_low_balance()             # Уведомления о низком балансе (каждый час)
- notify_user(telegram_id, msg)   # Отправка уведомления
- notify_campaign_status()        # Статус кампании

# parser.*
- refresh_chat_database(category) # Парсинг каналов (ночью, 7 слотов)
- parse_single_chat(username)     # Парсинг одного канала
- collect_all_chats_stats()       # Сбор аналитики

# cleanup.*
- delete_old_logs()               # Удаление старых логов (воскресенье)
- cleanup_expired_sessions()      # Очистка сессий
- archive_old_campaigns()         # Архивация кампаний

# billing.*
- check_plan_renewals()           # Проверка продления тарифов
- check_pending_invoices()        # Проверка платежей (каждые 5 мин)
```

**Beat Schedule:**

```python
# parser: 00:15-03:30 UTC (7 слотов по 30 мин)
# mailing: */5 минут
# billing: каждый час
# cleanup: воскресенье 03:00 UTC
```

---

## База данных

### Модели (SQLAlchemy 2.0)

**Основные таблицы:**

| Модель | Таблица | Ключевые поля |
|--------|---------|---------------|
| `User` | `users` | telegram_id, balance, credits, plan, referral_code, level, xp_points |
| `Campaign` | `campaigns` | user_id, title, text, status, filters_json, scheduled_at |
| `TelegramChat` | `telegram_chats` | telegram_id, title, member_count, topic, rating, owner_user_id |
| `Transaction` | `transactions` | user_id, amount, type, payment_id, balance_before/after |
| `MailingLog` | `mailing_logs` | campaign_id, chat_id, status, error_msg |
| `Notification` | `notifications` | user_id, type, message, is_read |
| `CryptoPayment` | `crypto_payments` | user_id, method, amount, status, tx_hash |
| `Payout` | `payouts` | owner_id, channel_id, amount, status |
| `Badge` | `badges` | user_id, badge_type, earned_at |

**Репозитории:**

```python
# Паттерн Repository с базовыми CRUD
class BaseRepository[T]:
    get_by_id, get_all, create, update, delete
    find_one, find_many, exists, paginate

# Специализированные:
- UserRepository: get_by_telegram_id, update_balance, has_channels
- CampaignRepository: get_by_user, update_status, get_scheduled_due
- ChatRepository: upsert_batch, get_active_filtered
- MailingLogRepository: bulk_insert, count_pending_for_owner
```

---

## Telegram Bot

### Главное меню (роль-зависимое)

**Роль определяется динамически:**

```python
# UserRoleService.get_user_context(user_id)
if has_channels and has_campaigns: role = "both"
elif has_channels: role = "owner"
elif has_campaigns: role = "advertiser"
else: role = "new"
```

**Меню для каждой роли:**

| Роль | Кнопки меню |
|------|-------------|
| **new** (онбординг) | Хочу размещать рекламу, У меня есть канал, Статистика платформы |
| **advertiser** | Создать кампанию, Мои кампании, Каталог каналов, B2B-пакеты, Аналитика, Кабинет, Поддержка, **Сменить роль** |
| **owner** | Мои каналы, Заявки, Добавить канал, Выплаты, Аналитика, Кабинет, Поддержка, **Сменить роль** |
| **both** | Раздел Реклама + Раздел Канал (комбинированное) |

### Команды бота

```
/start — Главное меню
/help — Справка
/cabinet — Личный кабинет
/balance — Проверить баланс
/campaigns — Мои кампании
/analytics — Аналитика
/addchat — Добавить канал
/stats — Статистика платформы
/app — Открыть Mini App
```

---

## API и Mini App

### Аутентификация

```python
# 1. Mini App отправляет X-Init-Data (Telegram initData)
# 2. API валидирует HMAC-SHA256 с BOT_TOKEN
# 3. Возвращает JWT токен (24 часа)
# 4. JWT хранится в Zustand store
```

### Структура Mini App

```
mini_app/src/
├── components/
│   ├── Layout.tsx          # Основной layout
│   ├── Header.tsx          # Шапка с балансом
│   ├── CampaignCard.tsx    # Карточка кампании
│   └── StatsChart.tsx      # Графики (recharts)
│
├── pages/
│   ├── Dashboard.tsx       # Главная
│   ├── Campaigns.tsx       # Кампании
│   ├── Analytics.tsx       # Аналитика
│   └── Billing.tsx         # Биллинг
│
├── stores/
│   ├── authStore.ts        # JWT auth (Zustand)
│   ├── campaignStore.ts    # Состояние кампаний
│   └── uiStore.ts          # UI состояние
│
└── api/
    └── client.ts           # Axios instance
```

---

## Сервисы

### AI Service (OpenRouter)

```python
# Модели:
- FREE/STARTER → stepfun/step-3.5-flash:free (бесплатная)
- PRO/BUSINESS → qwen/qwen-plus (платная)

# Методы:
- generate_ad_text(topic, description) → текст кампании
- generate_ab_variants(text) → 2-3 варианта
- improve_text(text) → улучшение текста
```

### Content Filter (3 уровня)

```
Level 1 → regex_check(text)      # < 1ms, compiled patterns
Level 2 → morph_check(text)      # pymorphy3, все формы слов
Level 3 → llm_check(text)        # LLM, если score(L1+L2) > 0.3

8 blocked категорий:
drugs, terrorism, weapons, adult, fraud, suicide, extremism, gambling
```

### Billing Service

```python
# Credit rates:
- 1 USDT = 90 credits
- 1 TON = 400 credits
- 1 BTC = 9,000,000 credits
- 1 Star = 2 credits

# Методы:
- create_crypto_invoice(user_id, currency, amount)
- check_payment_status(invoice_id)
- deduct_balance(user_id, amount)
- apply_referral_bonus(referrer_id, referred_user_id)
- freeze_funds(campaign_id)  # Эскроу
- release_funds(campaign_id)  # После публикации
```

### Analytics Service

```python
# Методы:
- get_campaign_stats(campaign_id) → sent, failed, CTR
- get_user_summary(user_id) → total_campaigns, spent
- get_top_performing_chats() → лучшие каналы
- get_platform_stats() → публичная статистика
- generate_campaign_pdf_report(campaign_id) → PDF отчёт
```

---

## Развёртывание

### Docker Compose (Production)

```yaml
services:
  bot:       # aiogram polling/webhook
  api:       # FastAPI uvicorn
  worker:    # Celery worker
  celery_beat # Celery beat scheduler
  flower:    # Celery monitoring
  postgres:  # PostgreSQL 16
  redis:     # Redis 7
  nginx:     # Reverse proxy + SSL
```

### Переменные окружения (.env)

```bash
# Telegram
BOT_TOKEN=xxx:xxx
API_ID=12345
API_HASH=xxx

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# AI
OPENROUTER_API_KEY=xxx

# JWT
JWT_SECRET=xxx

# Payments
CRYPTOBOT_TOKEN=xxx
STARS_ENABLED=true

# Admin
ADMIN_IDS=123456789,987654321

# Webhook
WEBHOOK_URL=https://domain.com/webhook
MINI_APP_URL=https://domain.com/app
```

### Команды развёртывания

```bash
# Build
docker compose build

# Start
docker compose up -d

# Logs
docker compose logs -f bot
docker compose logs -f worker

# Migrations
docker compose exec bot alembic upgrade head

# Shell
docker compose exec bot poetry run python

# Restart
docker compose restart bot api worker
```

### Monitoring

- **Flower:** `https://domain.com:5555` — Celery monitoring
- **Sentry:** Error tracking (DSN в settings.py)
- **Docker logs:** `docker compose logs -f`

---

## Безопасность

### Content Filter

Все тексты кампаний проходят 3-уровневую проверку:

1. **Regex** — быстрые паттерны (стоп-слова)
2. **Morphology** — pymorphy3 (все формы слов)
3. **LLM** — финальная проверка через AI

### Rate Limiting

```python
# Mailing лимиты (на аккаунт):
- 10 сообщений/минуту
- 300 сообщений/час
- 2000 сообщений/день

# Redis keys:
- mailing:rate_limit:{chat_id}
- mailing:global:minute:{timestamp}
- mailing:global:hour:{timestamp}
- mailing:global:day:{timestamp}
```

### JWT Auth

```python
# Алгоритм: HS256
# Срок действия: 24 часа
# Хранение: Zustand store (Mini App)
# Refresh: через Telegram initData
```

---

## Тестирование

### Unit тесты

```bash
# Запуск
poetry run pytest tests/unit/

# Покрытие
poetry run pytest --cov=src tests/
```

### Integration тесты

```bash
# Testcontainers (PostgreSQL + Redis)
poetry run pytest tests/integration/
```

### Linting

```bash
# Ruff (lint + format)
poetry run ruff check src/
poetry run ruff format src/

# MyPy (types)
poetry run mypy src/ --ignore-missing-imports
```

---

## Вклад в проект

### Ветвление

```
main → production (auto-deploy)
develop → integration
developer/{name} → personal branches
feature/{task} → short-lived features
```

### Commit Convention

```
feat(scope): short description
fix(scope): short description
refactor(scope): ...
test(scope): ...
docs(scope): ...
chore(scope): ...
```

### PR Process

1. Создать feature branch от `develop`
2. Внести изменения
3. Запустить `make lint && make test`
4. Создать PR в `develop`
5. Code review
6. Squash merge

---

## Контакты

- **Repository:** github.com/rybkagreen/market-telegram-bot
- **Bot:** @RekharborBot
- **Support:** @marketbot_support

---

*Документ обновлён: 2026-03-07*
