# RekHarborBot — Project Context

> This file is automatically loaded by Qwen Code on every session in this repository.
> It provides the agent with persistent project memory, conventions, and architectural context.
> Refresh with `/memory refresh` · Verify loaded context with `/memory show`

---

## Project Overview

**RekHarborBot** — Telegram-бот, рекламная биржа для Telegram-каналов. Платформа соединяет рекламодателей (малый и средний бизнес) с владельцами тематических каналов. Весь цикл — от выбора каналов до оплаты, публикации и аналитики — происходит внутри Telegram без перехода на сторонние сайты.

**Конкурентная среда:** Telega.in, Epicstars, TGStat.
**Ключевое отличие:** Telegram-native, простота для МСБ, эскроу-защита, аналитика из коробки.

| Field | Value |
|---|---|
| **Repository** | `github.com/rybkagreen/market-telegram-bot` |
| **Python** | 3.13 (managed via pyenv) |
| **Package manager** | Poetry |
| **Primary language** | Python (backend), TypeScript (Mini App) |
| **Deployment target** | timeweb.cloud (Ubuntu 22.04, Docker Compose) |
| **Bot framework** | aiogram 3.x |

### Value Proposition

**Для рекламодателя:** запустить рекламу в 10 каналах за 5 минут прямо в Telegram. Деньги заморожены до публикации. После — отчёт с CPM, CTR, ROI.

**Для владельца канала:** подключи бота один раз — получай заявки и автоматические выплаты. Ты контролируешь что публиковать. Деньги поступают только после размещения.

### Financial Model

- **1 кредит = 1 RUB**
- **Комиссия платформы:** 20% с каждого размещения
- **Владелец канала получает:** 80% от суммы размещения
- **Только opt-in каналы:** владелец сам добавляет бота администратором

### Tariff Plans

| Тариф | Цена | Особенности |
|-------|------|-------------|
| Free | 0 кр/мес | Базовый функционал, лимиты |
| Start | 299 кр/мес | Расширенные лимиты |
| Pro | 990 кр/мес | Полный функционал |
| Agency | 2999 кр/мес | B2B, белый лейбл, API |

---

## User Roles

| Роль | Код | Как получить | Функционал |
|------|-----|--------------|------------|
| Новый | `new` | По умолчанию при /start | Онбординг, выбор роли |
| Рекламодатель | `advertiser` | После выбора роли | Создание кампаний, аналитика, B2B |
| Владелец канала | `owner` | После регистрации канала | Управление каналами, заявки, выплаты |
| Обе роли | `both` | Если зарегистрирован в обеих | Комбинированное меню |
| Администратор | `admin` | Назначается вручную | Полный доступ, модерация |

---

## Architecture Summary

```
market-telegram-bot/
├── src/
│   ├── bot/                      # aiogram бот
│   │   ├── handlers/             # обработчики команд (иерархическая структура)
│   │   │   ├── __init__.py       # Главный router (включает все sub-packages)
│   │   │   ├── shared/           # Общие handlers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── start.py      # /start, онбординг, меню навигация ✅ Этап 0
│   │   │   │   ├── cabinet.py    # личный кабинет (профиль, XP, репутация)
│   │   │   │   ├── help.py       # помощь
│   │   │   │   ├── feedback.py   # обратная связь
│   │   │   │   └── notifications.py  # уведомления
│   │   │   ├── advertiser/       # Handlers рекламодателя
│   │   │   │   ├── __init__.py
│   │   │   │   ├── campaigns.py
│   │   │   │   ├── campaign_create_ai.py  # AI-wizard (13 FSM) — НЕ ТРОГАТЬ
│   │   │   │   ├── campaign_analytics.py  # аналитика по кампании
│   │   │   │   ├── analytics.py      # аналитика (advertiser + owner, раздельно)
│   │   │   │   ├── analytics_chats.py
│   │   │   │   ├── comparison.py     # сравнение каналов
│   │   │   │   └── b2b.py            # B2B-пакеты
│   │   │   ├── owner/            # Handlers владельца
│   │   │   │   ├── __init__.py
│   │   │   │   ├── channel_owner.py  # управление каналами владельца, выплаты
│   │   │   │   ├── channels_db.py    # каталог каналов, фильтрация
│   │   │   │   └── channels_db_mediakit.py  # медиакит канала
│   │   │   ├── placement/        # Handlers размещения (Этап 3)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── placement.py      # Заглушка (Этап 3.2)
│   │   │   │   ├── arbitration.py    # Заглушка (Этап 3.2)
│   │   │   │   └── channel_settings.py  # ✅ Этап 3.1: CRUD настроек канала (11 handlers, 9 FSM)
│   │   │   ├── billing/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── billing.py        # оплата, тарифы
│   │   │   │   └── templates.py
│   │   │   ├── infra/
│   │   │   │   ├── __init__.py
│   │   │   │   └── callback_schemas.py  # CallbackData схемы
│   │   │   └── admin/            # панель администратора
│   │   │       ├── __init__.py
│   │   │       ├── ai.py
│   │   │       ├── analytics.py
│   │   │       ├── campaigns.py
│   │   │       ├── users.py
│   │   │       ├── stats.py      # публичная статистика
│   │   │       └── monitoring.py # системный мониторинг
│   │   ├── keyboards/            # inline клавиатуры (иерархическая структура)
│   │   │   ├── __init__.py       # Только __all__
│   │   │   ├── shared/           # Общие клавиатуры
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main_menu.py  # главное меню + роль-меню ✅ Этап 0
│   │   │   │   ├── cabinet.py
│   │   │   │   ├── feedback.py
│   │   │   │   ├── pagination.py
│   │   │   │   └── channels_catalog.py  # каталог каналов (переименован из channels.py)
│   │   │   ├── advertiser/       # Клавиатуры рекламодателя
│   │   │   │   ├── __init__.py
│   │   │   │   ├── campaign.py
│   │   │   │   ├── campaign_ai.py    # AI wizard — НЕ ТРОГАТЬ
│   │   │   │   ├── campaign_analytics.py
│   │   │   │   └── comparison.py
│   │   │   ├── owner/            # Клавиатуры владельца
│   │   │   │   ├── __init__.py
│   │   │   │   └── mediakit.py
│   │   │   ├── placement/        # Клавиатуры размещения ✅ Этап 3.1
│   │   │   │   ├── __init__.py
│   │   │   │   ├── channel_settings.py  # настройки канала (ch_cfg:*)
│   │   │   │   ├── placement.py         # заявки на размещение (placement:*)
│   │   │   │   └── arbitration.py       # арбитраж (arbitration:*)
│   │   │   ├── billing/          # Биллинг
│   │   │   │   ├── __init__.py
│   │   │   │   └── billing.py
│   │   │   └── admin/            # Админка
│   │   │       ├── __init__.py
│   │   │       └── admin.py
│   │   ├── states/               # FSM StatesGroup
│   │   │   ├── campaign.py       # 9 состояний управления кампанией
│   │   │   ├── campaign_create.py  # 13 состояний AI wizard — НЕ ТРОГАТЬ
│   │   │   ├── channel_owner.py  # 6 состояний добавления канала
│   │   │   ├── onboarding.py
│   │   │   ├── feedback.py
│   │   │   ├── comparison.py
│   │   │   ├── mediakit.py
│   │   │   ├── placement.py      # НОВЫЙ (Этап 4): 9 состояний
│   │   │   ├── arbitration.py    # НОВЫЙ (Этап 4): 5 состояний
│   │   │   └── channel_settings.py  # НОВЫЙ (Этап 4): 6 состояний
│   │   ├── filters/
│   │   │   └── admin.py          # IsAdmin filter
│   │   ├── middlewares/
│   │   │   ├── fsm_timeout.py    # таймаут FSM состояний
│   │   │   └── throttling.py     # rate limiting
│   │   └── utils/
│   │       ├── message_utils.py
│   │       └── safe_callback.py
│   │
│   ├── api/                      # FastAPI REST API
│   │   ├── main.py               # FastAPI app
│   │   ├── auth_utils.py         # JWT авторизация
│   │   ├── dependencies.py       # DI: get_db, get_current_user
│   │   └── routers/
│   │       ├── auth.py           # POST /auth/telegram
│   │       ├── analytics.py      # GET /analytics/*
│   │       ├── campaigns.py      # CRUD /campaigns/*
│   │       ├── channels.py       # GET /channels/catalog, /channels/{id}
│   │       ├── billing.py        # POST /billing/topup, /billing/withdraw
│   │       ├── placements.py     # НОВЫЙ (Этап 6)
│   │       ├── channel_settings.py  # НОВЫЙ (Этап 6)
│   │       └── reputation.py     # НОВЫЙ (Этап 6)
│   │
│   ├── db/                       # работа с БД
│   │   ├── base.py               # DeclarativeBase
│   │   ├── session.py            # async_sessionmaker, get_db()
│   │   ├── models/               # SQLAlchemy модели
│   │   │   ├── user.py           # User (role, credits, plan, XP, levels)
│   │   │   ├── campaign.py       # Campaign (status, type: Broadcast/Placement)
│   │   │   ├── analytics.py      # TelegramChat, ChatSnapshot
│   │   │   ├── placement_request.py  # PlacementRequest ✅ Этап 1
│   │   │   ├── channel_settings.py   # ChannelSettings ✅ Этап 1
│   │   │   ├── reputation_score.py   # ReputationScore ✅ Этап 1
│   │   │   ├── reputation_history.py # ReputationHistory ✅ Этап 1
│   │   │   ├── transaction.py    # Transaction (topup/spend/escrow)
│   │   │   ├── mailing_log.py    # MailingLog (+placement_request_id)
│   │   │   ├── payout.py         # Payout
│   │   │   ├── review.py         # Review
│   │   │   ├── badge.py          # Badge, UserBadge
│   │   │   ├── channel_rating.py # ChannelRating
│   │   │   ├── b2b_package.py    # B2BPackage
│   │   │   ├── category.py       # Category, Subcategory
│   │   │   ├── channel_mediakit.py
│   │   │   ├── content_flag.py
│   │   │   ├── crypto_payment.py
│   │   │   └── notification.py
│   │   ├── migrations/           # Alembic миграции (head: 006)
│   │   └── repositories/         # Repository pattern
│   │       ├── base.py           # BaseRepository
│   │       ├── user_repo.py
│   │       ├── campaign_repo.py
│   │       ├── log_repo.py
│   │       ├── transaction_repo.py
│   │       ├── payout_repo.py
│   │       ├── placement_request_repo.py  # НОВЫЙ ✅ Этап 2
│   │       ├── channel_settings_repo.py   # НОВЫЙ ✅ Этап 2
│   │       ├── reputation_repo.py         # НОВЫЙ ✅ Этап 2
│   │       ├── category_repo.py
│   │       └── chat_analytics.py
│   │
│   ├── core/                     # бизнес-логика
│   │   ├── exceptions.py         # кастомные исключения
│   │   └── services/
│   │       ├── billing_service.py      # платежи, эскроу
│   │       ├── mailing_service.py      # рассылки, публикация placement
│   │       ├── payout_service.py       # выплаты
│   │       ├── notification_service.py # уведомления
│   │       ├── analytics_service.py    # аналитика
│   │       ├── mistral_ai_service.py   # ИИ-генерация (OpenRouter)
│   │       ├── user_role_service.py    # роли пользователей
│   │       ├── xp_service.py           # геймификация (НЕ ТРОГАТЬ)
│   │       ├── badge_service.py        # бейджи (НЕ ТРОГАТЬ)
│   │       ├── placement_request_service.py  # НОВЫЙ ✅ Этап 2
│   │       ├── reputation_service.py       # НОВЫЙ ✅ Этап 2
│   │       ├── category_classifier.py
│   │       ├── comparison_service.py
│   │       ├── link_tracking_service.py
│   │       ├── mediakit_service.py
│   │       ├── timing_service.py
│   │       ├── token_logger.py
│   │       ├── rating_service.py
│   │       └── review_service.py
│   │
│   ├── tasks/                    # Celery задачи
│   │   ├── celery_app.py         # Celery instance, 3 очереди
│   │   ├── celery_config.py      # Beat расписание
│   │   ├── billing_tasks.py      # expire placements, unblock users
│   │   ├── mailing_tasks.py      # send campaigns, publish placements
│   │   ├── notification_tasks.py # expiry notifications
│   │   ├── parser_tasks.py       # parse channels
│   │   ├── gamification_tasks.py # reputation recovery
│   │   ├── rating_tasks.py       # update channel ratings
│   │   ├── cleanup_tasks.py      # cleanup old logs
│   │   ├── badge_tasks.py
│   │   └── payout_tasks.py
│   │
│   ├── utils/                    # утилиты
│   │   ├── telegram/
│   │   │   ├── parser.py         # Telethon (read-only)
│   │   │   ├── sender.py         # отправка постов (Bot API)
│   │   │   ├── channel_rules_checker.py  # bot_is_admin проверка
│   │   │   ├── llm_classifier.py # LLM классификация тем
│   │   │   ├── topic_classifier.py
│   │   │   └── russian_lang_detector.py
│   │   └── content_filter/
│   │       ├── filter.py         # 3-уровневый фильтр
│   │       └── stopwords_ru.json
│   │
│   └── config/
│       └── settings.py           # Pydantic Settings
│
├── mini_app/                     # Telegram Mini App (React)
├── tests/
├── docker/
├── docs/                         # техническая документация v3.0
└── docker-compose.yml
```

---

## Tech Stack & Key Libraries

### Backend

| Категория | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| **Язык** | Python | 3.13 | — |
| **Bot Framework** | aiogram | 3.x | Telegram Bot API |
| **Web Framework** | FastAPI | 0.115+ | REST API, Mini App backend |
| **ORM** | SQLAlchemy | 2.0 async | Работа с БД |
| **DB Driver** | asyncpg | 0.30+ | PostgreSQL driver |
| **Migration** | Alembic | 1.14+ | Версионирование схемы |
| **Task Queue** | Celery + Beat | 5.x | Фоновые задачи |
| **Cache/Broker** | Redis | 7 | FSM storage, кэш |
| **AI** | Mistral via OpenRouter | — | Генерация текстов, классификация |
| **Parser** | Telethon | 1.36+ | Парсинг каналов (read-only) |
| **Content Filter** | pymorphy3, rapidfuzz | 2.0+, 3.6+ | 3-уровневая фильтрация |
| **Payments** | CryptoBot, Telegram Stars, ЮKassa, СБП | — | Способы оплаты |
| **Monitoring** | sentry-sdk, prometheus-client | 2.53+ | Ошибки, метрики |
| **PDF Reports** | reportlab | 4.3+ | Генерация PDF |

### AI Configuration

Переключается через `.env` переменную `AI_MODEL`:

| Среда | Модель | Стоимость |
|-------|--------|-----------|
| Dev / CI | `qwen/qwen3-235b-a22b:free` | Бесплатно (rate limit ~20 rps) |
| Production | `claude-sonnet-4-6` / Mistral | Платно |

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

## Database Models (SQLAlchemy)

Все модели наследуют от `Base` (`src/db/base.py`, `DeclarativeBase`).
Все временные поля — `DateTime(timezone=True)`.
`created_at` / `updated_at` — во всех основных моделях.

### 1. User (`src/db/models/user.py`)

Центральная модель. Один пользователь = один Telegram аккаунт.

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `telegram_id` | BigInteger UNIQUE | No | — | Telegram user_id |
| `username` | String(64) | Yes | None | @username без @ |
| `first_name` | String(128) | No | — | Имя в Telegram |
| `last_name` | String(128) | Yes | None | — |
| `role` | String(20) | No | `"new"` | new/advertiser/owner/both/admin |
| `credits` | Numeric(12,2) | No | 0.00 | Баланс кредитов |
| `plan` | String(20) | No | `"free"` | free/start/pro/agency |
| `plan_expires_at` | DateTime | Yes | None | Дата окончания тарифа |
| `plan_expiry_notified_at` | DateTime | Yes | None | Когда отправлено уведомление |
| `ai_provider` | String(50) | Yes | None | Провайдер AI для пользователя |
| `ai_model` | String(100) | Yes | None | Конкретная модель |
| `ai_requests_count` | Integer | No | 0 | Счётчик AI запросов |
| `language_code` | String(10) | Yes | None | Код языка Telegram |
| `russian_score` | Float | Yes | None | Вероятность русскоязычного пользователя |
| `is_banned` | Boolean | No | False | Глобальная блокировка |
| `ban_reason` | String(500) | Yes | None | — |
| `notifications_enabled` | Boolean | No | True | Глобальный toggle уведомлений |
| `login_streak` | Integer | No | 0 | Дней подряд в боте |
| `last_login_date` | Date | Yes | None | Дата последнего входа |
| `referral_code` | String(20) UNIQUE | Yes | None | Реферальный код пользователя |
| `referred_by_id` | Integer FK→users.id | Yes | None | Кто пригласил |
| `complaint_count` | Integer | No | 0 | Жалобы на пользователя |
| `is_blacklisted` | Boolean | No | False | Чёрный список |
| `blacklist_reason` | String(500) | Yes | None | — |
| **XP и уровни (геймификация)** | | | | |
| `advertiser_xp` | Integer | No | 0 | XP рекламодателя |
| `owner_xp` | Integer | No | 0 | XP владельца |
| `advertiser_level` | Integer | No | 0 | Уровень рекламодателя (0-6) |
| `owner_level` | Integer | No | 0 | Уровень владельца (0-6) |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**⚠️ XP/levels не связаны с ReputationScore — разные системы.**

**Relationships:**
- `campaigns` → list[Campaign]
- `telegram_chats` → list[TelegramChat]
- `badges` → list[UserBadge]
- `payouts` → list[Payout]
- `reputation_score` → ReputationScore (one-to-one)
- `referred_users` → list[User] (self-referential)

### 2. TelegramChat (`src/db/models/analytics.py`)

Telegram-канал в базе. Создаётся при парсинге или opt-in регистрации.

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `telegram_id` | BigInteger UNIQUE | No | — | Telegram channel id |
| `username` | String(64) UNIQUE | Yes | None | @handle |
| `title` | String(255) | No | — | Название канала |
| `description` | String(1000) | Yes | None | Описание |
| `owner_id` | Integer FK→users.id | Yes | None | Владелец (SET NULL) |
| `member_count` | Integer | No | 0 | Подписчиков |
| `avg_views` | Integer | No | 0 | Среднее просмотров |
| `last_er` | Float | Yes | None | Engagement Rate (%) |
| `rating` | Float | No | 5.0 | Рейтинг канала (0-10) |
| `topic` | String(100) | Yes | None | Тематика (AI классификация) |
| `subcategory` | String(100) | Yes | None | Подтематика |
| `language` | String(10) | Yes | None | Язык контента |
| `is_verified` | Boolean | No | False | Верифицирован модератором |
| `is_active` | Boolean | No | True | Активен в каталоге |
| `is_opt_in` | Boolean | No | False | Добровольная регистрация |
| `bot_is_admin` | Boolean | No | False | Бот — администратор |
| `bot_added_at` | DateTime | Yes | None | Когда бот добавлен |
| `last_parsed_at` | DateTime | Yes | None | Последний парсинг |
| `llm_classification_topic` | String(100) | Yes | None | LLM топик |
| `llm_classification_confidence` | Float | Yes | None | Уверенность классификации |
| `llm_classified_at` | DateTime | Yes | None | — |
| `price_per_post` | Numeric(10,2) | Yes | None | Цена установленная владельцем (устаревшее) |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Relationships:**
- `owner` → User
- `settings` → ChannelSettings (one-to-one)
- `placement_requests` → list[PlacementRequest]
- `snapshots` → list[ChatSnapshot]
- `mediakit` → ChannelMediakit (one-to-one)
- `channel_rating` → ChannelRating (one-to-one)

### 3. Campaign (`src/db/models/campaign.py`)

Рекламная кампания рекламодателя.

**Enum CampaignStatus:**
```python
class CampaignStatus(str, Enum):
    DRAFT      = "draft"
    QUEUED     = "queued"
    RUNNING    = "running"
    SCHEDULED  = "scheduled"
    DONE       = "done"
    ERROR      = "error"
    PAUSED     = "paused"
    CANCELLED  = "cancelled"
    MODERATION = "moderation"
```

**Enum CampaignType (добавлен в Этапе 1):**
```python
class CampaignType(str, Enum):
    BROADCAST = "broadcast"  # Старый тип: массовая рассылка
    PLACEMENT = "placement"  # Новый тип: размещение через арбитраж
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `advertiser_id` | Integer FK→users.id | No | — | CASCADE |
| `title` | String(255) | No | — | Название кампании |
| `text` | Text | No | — | Текст объявления |
| `topic_header_image_url` | String(512) | Yes | None | Изображение заголовка |
| `status` | CampaignStatus | No | DRAFT | — |
| `type` | CampaignType | No | BROADCAST | Тип кампании ✅ Этап 1 |
| `placement_request_id` | Integer FK→placement_requests.id | Yes | None | SET NULL ✅ Этап 1 |
| `budget` | Numeric(12,2) | Yes | None | Бюджет кампании |
| `spent` | Numeric(12,2) | No | 0.00 | Потрачено |
| `ctr` | Float | Yes | None | CTR (%) |
| `views_total` | Integer | No | 0 | Сумма просмотров |
| `clicks_total` | Integer | No | 0 | Сумма кликов |
| `channels_count` | Integer | No | 0 | Количество каналов |
| `target_category` | String(100) | Yes | None | Целевая тематика |
| `target_subcategory` | String(100) | Yes | None | — |
| `scheduled_at` | DateTime | Yes | None | Запланированное время |
| `started_at` | DateTime | Yes | None | Фактическое начало |
| `finished_at` | DateTime | Yes | None | Фактическое завершение |
| `meta_json` | JSON | Yes | None | Доп. метаданные (AI варианты и др.) |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

### 4. PlacementRequest (`src/db/models/placement_request.py`) ✅ Этап 1

Заявка на размещение рекламы. Центральная сущность нового флоу.

**Enum PlacementStatus:**
```python
class PlacementStatus(str, Enum):
    PENDING_OWNER   = "pending_owner"    # Ожидает решения владельца (24ч)
    COUNTER_OFFER   = "counter_offer"    # Владелец сделал контр-предложение
    PENDING_PAYMENT = "pending_payment"  # Принято, ждём оплаты (24ч)
    ESCROW          = "escrow"           # Средства заблокированы
    PUBLISHED       = "published"        # Успешно опубликовано
    FAILED          = "failed"           # Ошибка публикации
    REFUNDED        = "refunded"         # Средства возвращены
    CANCELLED       = "cancelled"        # Отменено
```

**Жизненный цикл:**
```
pending_owner ──► counter_offer ──► pending_owner (следующий раунд, макс 3)
     │                                     │
     │ (accept)                            │ (accept counter)
     ▼                                     ▼
pending_payment ◄────────────────────────────
     │
     │ (pay)
     ▼
  escrow ──► published
     │
     └──► failed ──► refunded

(любой статус) ──► cancelled
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `advertiser_id` | Integer FK→users.id | No | — | CASCADE |
| `campaign_id` | Integer FK→campaigns.id | No | — | CASCADE |
| `channel_id` | Integer FK→telegram_chats.id | No | — | CASCADE |
| `proposed_price` | Numeric(10,2) | No | — | Цена предложенная advertiser |
| `final_price` | Numeric(10,2) | Yes | None | Итоговая после арбитража |
| `proposed_schedule` | DateTime | Yes | None | Желаемое время публикации |
| `final_schedule` | DateTime | Yes | None | Согласованное время |
| `proposed_frequency` | Integer | Yes | None | Частота постов (пакеты) |
| `final_text` | Text | No | — | Финальный текст рекламы |
| `status` | PlacementStatus | No | PENDING_OWNER | — |
| `rejection_reason` | String(500) | Yes | None | Причина отклонения (мин 10 символов, должна содержать буквы) |
| `counter_offer_count` | Integer | No | 0 | Раундов арбитража (макс 3) |
| `last_counter_at` | DateTime | Yes | None | Время последнего контр-предложения |
| `escrow_transaction_id` | Integer FK→transactions.id | Yes | None | SET NULL |
| `expires_at` | DateTime | No | — | Дедлайн ответа (+24ч от создания/контр-предложения) |
| `published_at` | DateTime | Yes | None | Реальное время публикации |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Индексы:** advertiser_id, channel_id, campaign_id, status, expires_at, created_at

### 5. ChannelSettings (`src/db/models/channel_settings.py`) ✅ Этап 1

Настройки монетизации канала. PK = `channel_id` (строго one-to-one).

**Системные константы (class-level, неизменяемые):**
```python
MIN_PRICE_PER_POST    = Decimal("100.00")  # Минимум 100 кредитов
MAX_PACKAGE_DISCOUNT  = 50                 # Скидка пакета макс 50%
MIN_SUBSCRIPTION_DAYS = 7                  # Минимум 7 дней подписки
MAX_SUBSCRIPTION_DAYS = 365               # Максимум 1 год
MAX_POSTS_PER_DAY     = 5                  # Рекламных постов в день макс 5
MAX_POSTS_PER_WEEK    = 35                 # В неделю макс 35
MIN_HOURS_BETWEEN_POSTS = 4               # Между постами минимум 4 часа
PLATFORM_COMMISSION   = Decimal("0.20")   # 20% комиссия платформы
```

| Поле | Тип | Nullable | Default | Ограничение |
|------|-----|----------|---------|-------------|
| `channel_id` | Integer PK FK→telegram_chats.id | No | — | CASCADE |
| `owner_id` | Integer FK→users.id | No | — | CASCADE |
| `price_per_post` | Numeric(10,2) | No | 500.00 | ≥ MIN_PRICE_PER_POST |
| `daily_package_enabled` | Boolean | No | True | — |
| `daily_package_max` | Integer | No | 2 | 1–5 |
| `daily_package_discount` | Integer | No | 20 | 0–50 |
| `weekly_package_enabled` | Boolean | No | True | — |
| `weekly_package_max` | Integer | No | 5 | 1–35 |
| `weekly_package_discount` | Integer | No | 30 | 0–50 |
| `subscription_enabled` | Boolean | No | True | — |
| `subscription_min_days` | Integer | No | 7 | 7–365 |
| `subscription_max_days` | Integer | No | 365 | 7–365 |
| `subscription_max_per_day` | Integer | No | 1 | 1–5 |
| `publish_start_time` | Time | No | 09:00 | — |
| `publish_end_time` | Time | No | 21:00 | — |
| `break_start_time` | Time | Yes | 14:00 | Перерыв (начало) |
| `break_end_time` | Time | Yes | 15:00 | Перерыв (конец) |
| `auto_accept_enabled` | Boolean | No | False | Авто-принятие заявок |
| `auto_accept_min_price` | Numeric(10,2) | Yes | None | Мин цена для авто-принятия |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Индекс:** owner_id

### 6. ReputationScore (`src/db/models/reputation_score.py`) ✅ Этап 1

Система доверия пользователя. PK = `user_id` (строго one-to-one). **НЕ путать с XP/levels.**

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `user_id` | Integer PK FK→users.id | No | — | CASCADE |
| `advertiser_score` | Float | No | 5.0 | Надёжность как advertiser (0.0–10.0) |
| `owner_score` | Float | No | 5.0 | Надёжность как owner (0.0–10.0) |
| `advertiser_violations` | Integer | No | 0 | Нарушений как advertiser |
| `owner_violations` | Integer | No | 0 | Нарушений как owner |
| `is_advertiser_blocked` | Boolean | No | False | Заблокирован как advertiser |
| `is_owner_blocked` | Boolean | No | False | Заблокирован как owner |
| `advertiser_blocked_until` | DateTime | Yes | None | Срок блокировки advertiser |
| `owner_blocked_until` | DateTime | Yes | None | Срок блокировки owner |
| `block_reason` | String(500) | Yes | None | Причина блокировки |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Ключевые правила:**
- Диапазон: 0.0 – 10.0
- Стартовое значение: 5.0
- После 7-дневного бана: сброс до 2.0
- 5+ нарушений: перманентная блокировка
- Пользователь с двумя ролями (`both`) может быть заблокирован как owner, оставаясь активным как advertiser

### 7. ReputationHistory (`src/db/models/reputation_history.py`) ✅ Этап 1

Полная история изменений репутации.

**Enum ReputationAction (16 значений):**
```python
class ReputationAction(str, Enum):
    PUBLICATION        = "publication"        # +1.0 за успешную публикацию
    REVIEW_5STAR       = "review_5star"        # +2.0
    REVIEW_4STAR       = "review_4star"        # +1.0
    REVIEW_3STAR       = "review_3star"        # 0.0
    REVIEW_2STAR       = "review_2star"        # -1.0
    REVIEW_1STAR       = "review_1star"        # -2.0
    CANCEL_BEFORE      = "cancel_before"       # -5.0  (до подтверждения)
    CANCEL_AFTER       = "cancel_after"        # -20.0 (после подтверждения)
    CANCEL_SYSTEMATIC  = "cancel_systematic"   # -20.0 (3 отмены за 30 дней)
    REJECT_INVALID_1   = "reject_invalid_1"    # -10.0 (1й невалидный отказ)
    REJECT_INVALID_2   = "reject_invalid_2"    # -15.0 (2й)
    REJECT_INVALID_3   = "reject_invalid_3"    # -20.0 + бан 7 дней (3й)
    REJECT_FREQUENT    = "reject_frequent"     # -5.0  (>50% отказов)
    RECOVERY_30DAYS    = "recovery_30days"     # +5.0  (30 дней без нарушений)
    BAN_RESET          = "ban_reset"           # сброс до 2.0 после бана
    INITIAL_MIGRATION  = "initial_migration"   # служебная запись
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `user_id` | Integer FK→users.id | No | — | CASCADE |
| `placement_request_id` | Integer FK→placement_requests.id | Yes | None | SET NULL |
| `action` | ReputationAction | No | — | Тип события |
| `delta` | Float | No | — | Изменение (+/-) |
| `new_score` | Float | No | — | Score после изменения |
| `role` | String(20) | No | — | "advertiser" или "owner" |
| `comment` | String(500) | Yes | None | Контекст |
| `created_at` | DateTime | No | now() | — |

**Индексы:** user_id, placement_request_id, created_at, role

### 8. MailingLog (`src/db/models/mailing_log.py`)

Запись о каждой попытке публикации поста.

**Enum MailingStatus:**
```python
class MailingStatus(str, Enum):
    PENDING    = "pending"
    SENT       = "sent"
    FAILED     = "failed"
    SKIPPED    = "skipped"
    CANCELLED  = "cancelled"
    RETRY      = "retry"
    TIMEOUT    = "timeout"
    BOUNCED    = "bounced"
    BLOCKED    = "blocked"
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `campaign_id` | Integer FK→campaigns.id | No | — | CASCADE |
| `channel_id` | Integer FK→telegram_chats.id | No | — | CASCADE |
| `placement_request_id` | Integer FK→placement_requests.id | Yes | None | SET NULL ✅ Этап 1 |
| `status` | MailingStatus | No | PENDING | — |
| `message_id` | BigInteger | Yes | None | Telegram message_id после отправки |
| `error_message` | Text | Yes | None | Текст ошибки |
| `views_count` | Integer | No | 0 | Просмотры (если доступно) |
| `clicks_count` | Integer | No | 0 | Клики по ссылкам |
| `sent_at` | DateTime | Yes | None | Фактическое время отправки |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

### 9. Transaction (`src/db/models/transaction.py`)

Финансовые операции с балансом.

**Enum TransactionType:**
```python
class TransactionType(str, Enum):
    TOPUP           = "topup"            # Пополнение
    WITHDRAWAL      = "withdrawal"       # Вывод средств
    PAYMENT         = "payment"          # Оплата кампании
    REFUND          = "refund"           # Возврат
    ESCROW_FREEZE   = "escrow_freeze"    # Блокировка для PlacementRequest
    ESCROW_RELEASE  = "escrow_release"   # Разблокировка → владельцу
    COMMISSION      = "commission"       # Комиссия платформы
    BONUS           = "bonus"            # Бонусные кредиты
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `user_id` | Integer FK→users.id | No | — | CASCADE |
| `type` | TransactionType | No | — | — |
| `amount` | Numeric(12,2) | No | — | Сумма (всегда положительная) |
| `balance_before` | Numeric(12,2) | No | — | Баланс до операции |
| `balance_after` | Numeric(12,2) | No | — | Баланс после |
| `description` | String(500) | Yes | None | Описание операции |
| `reference_id` | Integer | Yes | None | ID связанного объекта |
| `reference_type` | String(50) | Yes | None | Тип связанного объекта |
| `created_at` | DateTime | No | now() | — |

### 10. Payout (`src/db/models/payout.py`)

Запрос на выплату для владельца канала.

**Enum PayoutStatus:**
```python
class PayoutStatus(str, Enum):
    PENDING    = "pending"     # Ожидает обработки
    PROCESSING = "processing"  # В обработке
    PAID       = "paid"        # Выплачено
    FAILED     = "failed"      # Ошибка выплаты
    CANCELLED  = "cancelled"   # Отменено
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `owner_id` | Integer FK→users.id | No | — | CASCADE |
| `placement_id` | Integer FK→placement_requests.id | Yes | None | SET NULL |
| `amount` | Numeric(12,2) | No | — | Сумма выплаты |
| `status` | PayoutStatus | No | PENDING | — |
| `payment_method` | String(50) | Yes | None | Метод выплаты |
| `payment_details` | String(500) | Yes | None | Реквизиты |
| `processed_at` | DateTime | Yes | None | Время обработки |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

### 11. Review (`src/db/models/review.py`)

Отзыв после завершения размещения.

**Enum ReviewerRole:**
```python
class ReviewerRole(str, Enum):
    ADVERTISER = "advertiser"
    OWNER      = "owner"
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `reviewer_id` | Integer FK→users.id | No | — | Кто оставил отзыв |
| `reviewed_id` | Integer FK→users.id | No | — | О ком отзыв |
| `placement_id` | Integer FK→placement_requests.id | Yes | None | SET NULL |
| `reviewer_role` | ReviewerRole | No | — | Роль рецензента |
| `stars` | Integer | No | — | 1–5 |
| `comment` | String(1000) | Yes | None | Текст отзыва |
| `created_at` | DateTime | No | now() | — |

### 12. Badge / UserBadge (`src/db/models/badge.py`)

Геймификация: достижения пользователей.

| Поле (Badge) | Тип | Описание |
|-------------|-----|----------|
| `id` | Integer PK | — |
| `code` | String(50) UNIQUE | Код бейджа |
| `name` | String(100) | Название |
| `description` | String(500) | Описание |
| `icon` | String(10) | Эмодзи |
| `xp_reward` | Integer | Награда XP |
| `role` | String(20) | advertiser/owner/both |
| `trigger_type` | String(50) | Тип триггера |
| `trigger_value` | Integer | Порог |

| Поле (UserBadge) | Тип | Описание |
|----------------|-----|----------|
| `id` | Integer PK | — |
| `user_id` | Integer FK→users.id | CASCADE |
| `badge_id` | Integer FK→badges.id | CASCADE |
| `earned_at` | DateTime | Когда получен |

### 13. ChannelRating (`src/db/models/channel_rating.py`)

Рейтинг качества канала (отдельно от репутации владельца).

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `channel_id` | Integer FK→telegram_chats.id UNIQUE | No | — | One-to-one |
| `overall_score` | Float | No | 5.0 | Общий рейтинг (0-10) |
| `content_quality` | Float | No | 5.0 | Качество контента |
| `audience_quality` | Float | No | 5.0 | Качество аудитории |
| `reliability` | Float | No | 5.0 | Надёжность владельца |
| `review_count` | Integer | No | 0 | Количество отзывов |
| `fraud_score` | Float | No | 0.0 | Вероятность накрутки (0-1) |
| `updated_at` | DateTime | No | now() | onupdate |

**⚠️ ChannelRating ≠ ReputationScore:**
- `ChannelRating` — характеристика канала (качество контента, аудитории)
- `ReputationScore` — характеристика пользователя (надёжность контрагента)

### 14. B2BPackage (`src/db/models/b2b_package.py`)

Пакетные предложения для рекламодателей.

| Пакет | Цена | Каналов | Бюджет/канал | Охват | Срок |
|-------|------|---------|--------------|-------|------|
| Стартап | 1500 кр | 5 | 300 кр | ~25K | 7 дней |
| Бизнес | 5000 кр | 10 | 500 кр | ~60K | 14 дней |
| Премиум | 25000 кр | 25 | 1000 кр | ~200K | 30 дней |

---

## Service Layer Contracts

> **Rule:** Handlers NEVER access the DB directly. Always call the appropriate service or repository.

### Repositories

| Repository | Key Methods | Owner |
|------------|-------------|-------|
| `BaseRepository[T]` | `get`, `get_all`, `create`, `update`, `delete`, `exists` | belin |
| `UserRepo` | `get_by_telegram_id`, `get_or_create`, `update_role`, `update_credits`, `ban`, `unban` | belin |
| `CampaignRepo` | `get_by_advertiser`, `get_active_by_advertiser`, `update_status`, `get_scheduled` | belin |
| `LogRepo` | `create_log`, `update_status`, `get_by_campaign`, `get_failed_retryable` | belin |
| `TransactionRepo` | `create_topup`, `create_payment`, `create_refund`, `create_escrow_freeze`, `create_escrow_release` | belin |
| `PayoutRepo` | `create_payout`, `get_pending`, `get_by_owner`, `get_available_amount`, `update_status` | belin |
| `PlacementRequestRepo` | `create`, `get_by_advertiser`, `get_by_channel`, `get_pending_for_owner`, `get_expired`, `accept`, `reject`, `counter_offer`, `set_escrow`, `set_published` | belin ✅ Этап 2 |
| `ChannelSettingsRepo` | `get_by_channel`, `get_or_create_default`, `upsert`, `get_by_owner`, `delete` | belin ✅ Этап 2 |
| `ReputationRepo` | `get_by_user`, `get_or_create`, `update_score`, `set_block`, `increment_violations`, `add_history`, `get_history`, `get_users_with_expired_blocks`, `count_invalid_rejections_streak` | belin ✅ Этап 2 |

### Services

| Service | Key Methods | Owner |
|---------|-------------|-------|
| `BillingService` | `topup`, `charge`, `refund`, `freeze_escrow_for_placement`, `release_escrow_for_placement`, `partial_refund`, `check_balance` | belin |
| `MailingService` | `send_campaign`, `send_to_channel`, `publish_placement`, `retry_failed`, `get_sendstats` | belin |
| `PlacementRequestService` | `create_request`, `owner_accept`, `owner_reject`, `owner_counter_offer`, `advertiser_accept_counter`, `advertiser_cancel`, `process_payment`, `process_publication_success`, `process_publication_failure`, `auto_expire`, `validate_rejection_reason` | belin ✅ Этап 2 |
| `ReputationService` | `on_publication`, `on_review`, `on_advertiser_cancel`, `on_invalid_rejection`, `on_frequent_rejections`, `on_30days_clean`, `check_and_unblock`, `is_blocked`, `get_score`, `_apply_delta` | belin ✅ Этап 2 |
| `PayoutService` | `request_payout`, `request_payout_for_placement`, `process_payout`, `get_available_amount`, `get_history` | belin |
| `NotificationService` | `notify`, `notify_owner_new_request`, `notify_advertiser_accepted`, `notify_advertiser_rejected`, `notify_advertiser_counter`, `notify_publication_success`, `notify_publication_failed`, `notify_plan_expiring`, `get_unread`, `mark_read` | belin |
| `AnalyticsService` | `get_advertiser_stats`, `get_owner_stats`, `get_campaign_stats`, `get_channel_performance`, `calculate_cpm`, `calculate_ctr`, `calculate_roi` | belin |
| `MistralAIService` | `generate_ad_text`, `classify_channel_topic`, `filter_content_level3` | belin |
| `UserRoleService` | `set_role`, `add_role`, `remove_role`, `get_effective_role`, `can_create_campaign`, `can_register_channel` | belin |
| `XPService` | `add_xp`, `get_xp_for_next_level`, `check_level_up` | **НЕ ТРОГАТЬ** |
| `BadgeService` | `check_and_award`, `get_user_badges`, `get_available_badges` | **НЕ ТРОГАТЬ** |

---

## Celery Task Queues

### 3 очереди

| Очередь | Назначение | Приоритет |
|---------|------------|-----------|
| `critical` | Платежи, эскроу, авто-отклонения заявок | Высокий |
| `background` | Рассылки, уведомления, парсинг | Средний |
| `game` | XP, бейджи, геймификация | Низкий |

### Beat Schedule

```python
# Критические
"expire-placements-every-5min": {
    "task": "src.tasks.billing_tasks.expire_pending_placements",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "critical"},
}
"unblock-users-every-hour": {
    "task": "src.tasks.billing_tasks.unblock_expired_users",
    "schedule": crontab(minute=0),
    "options": {"queue": "critical"},
}

# Фоновые
"parse-channels-daily": {
    "task": "src.tasks.parser_tasks.parse_channels",
    "schedule": crontab(hour=3, minute=0),
    "options": {"queue": "background"},
}
"send-scheduled-campaigns": {
    "task": "src.tasks.mailing_tasks.send_scheduled",
    "schedule": crontab(minute="*/10"),
    "options": {"queue": "background"},
}
"publish-scheduled-placements": {
    "task": "src.tasks.mailing_tasks.publish_scheduled_placements",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "background"},
}
"send-plan-expiry-notifications": {
    "task": "src.tasks.notification_tasks.notify_expiring_plans",
    "schedule": crontab(hour=10, minute=0),
    "options": {"queue": "background"},
}

# Геймификация (низкий приоритет)
"check-30days-recovery": {
    "task": "src.tasks.gamification_tasks.check_reputation_recovery",
    "schedule": crontab(hour=1, minute=0),
    "options": {"queue": "game"},
}
"update-channel-ratings": {
    "task": "src.tasks.rating_tasks.update_all_ratings",
    "schedule": crontab(hour=4, minute=0),
    "options": {"queue": "game"},
}
"cleanup-old-logs": {
    "task": "src.tasks.cleanup_tasks.cleanup_old_mailing_logs",
    "schedule": crontab(hour=2, minute=0, day_of_week=1),
    "options": {"queue": "background"},
}
```

---

## FSM States

### CampaignStates (`src/bot/states/campaign.py`) — 9 состояний

```python
class CampaignStates(StatesGroup):
    waiting_name        = State()  # Ввод названия
    waiting_text        = State()  # Ввод текста объявления
    waiting_budget      = State()  # Ввод бюджета
    waiting_category    = State()  # Выбор категории
    waiting_channels    = State()  # Выбор каналов
    waiting_schedule    = State()  # Выбор времени
    waiting_confirm     = State()  # Подтверждение
    waiting_payment     = State()  # Ожидание оплаты
    campaign_active     = State()  # Кампания активна
```

### CampaignCreateState (`src/bot/states/campaign_create.py`) — 13 состояний

**⚠️ НЕ ТРОГАТЬ — AI wizard.**

```python
class CampaignCreateState(StatesGroup):
    choosing_ai_or_manual  = State()
    entering_topic         = State()
    choosing_tone          = State()
    choosing_variant       = State()
    editing_text           = State()
    choosing_category      = State()
    choosing_subcategory   = State()
    choosing_channels      = State()
    setting_budget         = State()
    setting_schedule       = State()
    setting_frequency      = State()
    confirming             = State()
    waiting_payment        = State()
```

### PlacementStates (`src/bot/states/placement.py`) — 9 состояний ✅ Этап 4

```python
class PlacementStates(StatesGroup):
    selecting_category    = State()  # Шаг 1: категория
    selecting_subcategory = State()  # Шаг 2: подкатегория (skip если нет)
    selecting_channels    = State()  # Шаг 3: выбор каналов из каталога
    entering_text         = State()  # Шаг 4: текст (AI/Manual)
    arbitrating           = State()  # Шаг 5: ввод условий (цена, время)
    confirming            = State()  # Шаг 6: подтверждение перед отправкой
    waiting_payment       = State()  # Шаг 7: ожидание оплаты
    escrow                = State()  # Шаг 8: средства заблокированы
    publishing            = State()  # Шаг 9: идёт публикация
```

### ArbitrationStates (`src/bot/states/arbitration.py`) — 5 состояний ✅ Этап 4

```python
class ArbitrationStates(StatesGroup):
    viewing_request    = State()  # Просмотр заявки
    accepting          = State()  # Подтверждение принятия
    rejecting          = State()  # Ввод причины отклонения (мин 10 символов)
    counter_offering   = State()  # Ввод контр-предложения (цена/время)
    waiting_response   = State()  # Ожидание ответа advertiser
```

### ChannelSettingsStates (`src/bot/states/channel_settings.py`) — 6 состояний ✅ Этап 4

```python
class ChannelSettingsStates(StatesGroup):
    editing_price          = State()  # Редактирование цены за пост
    editing_daily_package  = State()  # Настройка дневного пакета
    editing_weekly_package = State()  # Настройка недельного пакета
    editing_subscription   = State()  # Настройка подписки
    editing_schedule       = State()  # Настройка расписания публикаций
    confirming             = State()  # Подтверждение изменений
```

### AddChannelStates (`src/bot/states/channel_owner.py`) — 6 состояний

```python
class AddChannelStates(StatesGroup):
    waiting_username    = State()  # Ввод @username канала
    checking_channel    = State()  # Проверка существования
    waiting_bot_added   = State()  # Ожидание добавления бота
    verifying_admin     = State()  # Верификация прав бота
    waiting_price       = State()  # Ввод цены за пост
    confirming          = State()  # Подтверждение регистрации
```

### OnboardingStates (`src/bot/states/onboarding.py`)

```python
class OnboardingStates(StatesGroup):
    choosing_role    = State()
    confirming_role  = State()
```

### FeedbackStates (`src/bot/states/feedback.py`)

```python
class FeedbackStates(StatesGroup):
    waiting_message  = State()
    waiting_contact  = State()
```

---

## Content Filter — 3 Levels

```
Текст рекламы
    │
    ▼
┌─────────────────────────────────┐
│ Уровень 1: regex_check()        │  < 1ms
│ - Компилированные паттерны      │
│ - stop words из stopwords_ru.json│
│ - HIGH_RISK (≥3) → BLOCK        │
│ - MEDIUM_RISK (1-2) → L2        │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Уровень 2: morph_check()        │  < 10ms
│ - pymorphy3 (все формы слов)   │
│ - Склонения, спряжения          │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Уровень 3: llm_check()          │  1-3 сек
│ - Mistral API (OpenRouter)      │
│ - Контекстный анализ            │
└──────────────┬──────────────────┘
               │
               ▼
         BLOCKED ❌ или PASS ✅
```

**8 заблокированных категорий:**
1. `drugs` — наркотики
2. `terrorism` — терроризм
3. `weapons` — оружие
4. `adult` — контент 18+
5. `fraud` — мошенничество
6. `suicide` — суицид
7. `extremism` — экстремизм
8. `gambling` — азартные игры

---

## API Authentication (FastAPI)

Mini App authenticates via Telegram `initData` HMAC-SHA256:

```python
# src/api/auth_utils.py — verify_telegram_init_data()
# 1. Верифицировать HMAC подпись Telegram
# 2. Вернуть user_data
# 3. create_access_token(user_id) → JWT с exp = now() + ACCESS_TOKEN_EXPIRE_MINUTES
# 4. get_current_user(token) → User ORM object
```

**Token:** В заголовке `Authorization: Bearer <token>`

---

## Environment Variables

> Never commit `.env`. Use `.env.example` as the template.

### Bot

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram Bot token from @BotFather ⚠️ ТРЕБУЕТ РОТАЦИИ |
| `BOT_USERNAME` | @RekHarborBot |

### Database

| Variable | Description |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` |
| `DATABASE_SYNC_URL` | `postgresql://user:pass@host/db` (для Alembic) |

### Redis

| Variable | Description |
|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` |
| `REDIS_FSM_DB` | `1` (отдельная БД для FSM storage) |

### AI

| Variable | Description |
|---|---|
| `AI_MODEL` | `qwen/qwen3-235b-a22b:free` (dev) / `claude-sonnet-4-6` (prod) |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` |

### Payments

| Variable | Description |
|---|---|
| `CRYPTOBOT_TOKEN` | CryptoBot token |
| `CRYPTOBOT_WEBHOOK_URL` | `https://yourdomain.com/billing/cryptobot/webhook` |
| `YUKASSA_SHOP_ID` | YooKassa merchant ID |
| `YUKASSA_SECRET_KEY` | YooKassa secret key |

### Telethon (Parser)

| Variable | Description |
|---|---|
| `TELEGRAM_API_ID` | Telegram API ID |
| `TELEGRAM_API_HASH` | Telegram API Hash |
| `TELEGRAM_SESSION_NAME` | `parser` |

### Admin

| Variable | Description |
|---|---|
| `ADMIN_TELEGRAM_IDS` | `[123456789]` |

### Security

| Variable | Description |
|---|---|
| `API_SECRET_KEY` | JWT secret key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60 * 24 * 7` (7 дней) |

### Platform Defaults

| Variable | Description |
|---|---|
| `PLATFORM_COMMISSION` | `0.20` (20%) |
| `MIN_PRICE_PER_POST` | `100` (кредитов) |
| `MIN_PAYOUT` | `100` (кредитов минимум для вывода) |
| `MIN_TOPUP` | `100` (кредитов минимум для пополнения) |
| `PLACEMENT_TIMEOUT_HOURS` | `24` (таймер ответа владельца) |
| `PAYMENT_TIMEOUT_HOURS` | `24` (таймер оплаты) |
| `MAX_COUNTER_OFFERS` | `3` (максимум раундов арбитража) |
| `PUBLICATION_RETRY_HOURS` | `1` (retry при ошибке публикации) |

---

## Code Quality Rules

### Static Analysis

Запускать после каждого этапа:

```bash
# Linter + автоисправление
ruff check src/ --fix
ruff format src/

# Типизация
mypy src/ --ignore-missing-imports

# Безопасность
bandit -r src/ -ll  # только medium/high

# Стиль
flake8 src/ --max-line-length=120 --extend-ignore=E203,W503

# Проверка миграций
alembic check
```

**Целевые показатели:** Ruff 0, MyPy 0, Bandit High 0, Flake8 0.

### Development Rules

- **No direct DB queries in handlers** — use repositories only
- **No `print()`** — use `logging.getLogger(__name__)`
- **All async functions must use `await`** — no blocking calls in async context
- **Type hints required** on all function signatures
- **No hardcoded secrets** — all from `settings.py` (Pydantic Settings)
- **Max PR size: 400 lines** — split larger changes into multiple PRs
- **Tests required** for all new services and repositories

### Important Constraints

| Правило | Обоснование |
|---------|-------------|
| `xp_service.py` — не трогать | Геймификация работает, изменения сломают уровни пользователей |
| `campaign_create_ai.py` — не трогать | AI wizard (13 состояний), отдельный флоу |
| `User.advertiser_xp/owner_xp` — не трогать | XP ≠ Репутация, разные системы |
| Callback_data без префикса `main:` — не использовать для навигации | Архитектурное решение Этапа 0 |
| aiogram для публикации, Telethon только для парсинга | Публикация требует admin-прав бота |

### Naming Conventions

- Модели: `CamelCase` → файл `snake_case.py`
- Репозитории: `ModelNameRepo` → файл `model_name_repo.py`
- Сервисы: `ModelNameService` → файл `model_name_service.py`
- Handlers: `src/bot/handlers/feature_name.py`
- Keyboards: `src/bot/keyboards/feature_name.py` с функциями `get_*_kb()`
- FSM States: `FeatureNameStates(StatesGroup)` → файл `src/bot/states/feature_name.py`
- Callback_data prefix: `main:` для навигации, `feature:action` для остального

---

## Business Rules Summary

### Arbitration & Timers

| Событие | Таймер | Действие при истечении |
|---------|--------|----------------------|
| Ответ владельца на заявку | 24 часа | Авто-отмена, refund 100%, уведомление advertiser |
| Оплата после принятия | 24 часа | Заявка аннулируется, уведомление owner |
| Контр-предложение | 24 часа | Авто-отмена раунда |
| Максимум раундов контр-предложений | 3 раунда | После 3-го: только принять/отклонить |
| Retry публикации при ошибке | 1 час | После retry: FAILED + refund 100% |

### Refunds

| Сценарий | % возврата | Δ Репутация advertiser |
|----------|------------|----------------------|
| Владелец отклонил | 100% | 0 |
| Advertiser отменил (до эскроу) | 100% | −5 |
| Advertiser отменил (после эскроу) | 50% | −20 |
| 3 отмены за 30 дней | — | ещё −20 + ⚠️ предупреждение |
| Техошибка (бот удалён, канал заблокирован) | 100% | 0 |
| Таймаут ответа владельца | 100% | 0 |
| Таймаут оплаты | 100% | 0 |

### Reputation Penalties (owner)

| Действие | Δ Репутация | Последствия |
|----------|-------------|-------------|
| Невалидный отказ (1й) | −10 | — |
| Невалидный отказ (2й подряд) | −15 | — |
| Невалидный отказ (3й подряд) | −20 | Бан 7 дней |
| Частые отказы (>50%) | −5 | — |
| Отказ с валидной причиной | 0 | — |

### Reputation Recovery

| Событие | Δ Репутация | Кому |
|---------|-------------|------|
| Успешная публикация | +1 | advertiser + owner |
| Отзыв 5⭐ | +2 | получатель отзыва |
| Отзыв 4⭐ | +1 | — |
| Отзыв 3⭐ | 0 | — |
| Отзыв 2⭐ | −1 | — |
| Отзыв 1⭐ | −2 | — |
| 30 дней без нарушений | +5 | — |
| После бана (сброс) | → 2.0 | после окончания бана |

### Blocks

| Условие | Тип блокировки | Продолжительность |
|---------|----------------|-------------------|
| 3й невалидный отказ подряд | owner_blocked | 7 дней |
| Score ≤ 0 | role_blocked | Перманентная |
| violations ≥ 5 | role_blocked | Перманентная |
| is_banned (глобально) | full_ban | Перманентная (admin) |

### Rejection Reason Validation

```python
# Правила валидной причины отклонения:
min_length = 10 символов
must_contain = re.search(r'[а-яёa-z]', reason, re.IGNORECASE)
blacklist = ["asdfgh", "aaaaaa", "123456", "qwerty", "нет", "no", "не хочу"]
# Невалидная причина → ReputationService.on_invalid_rejection()
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
| Celery config | `src/tasks/celery_config.py` |
| PlacementRequestService | `src/core/services/placement_request_service.py` |
| ReputationService | `src/core/services/reputation_service.py` |
| BillingService | `src/core/services/billing_service.py` |
| MailingService | `src/core/services/mailing_service.py` |
| FastAPI entry | `src/api/main.py` |
| API auth utils | `src/api/auth_utils.py` |
| Documentation | `docs/` (DOC_01–05, refactoring_v0.3) |

---

## Testing Conventions

```python
# Unit tests — pure logic, no DB, mock everything external
# tests/unit/test_content_filter.py
# tests/unit/test_reputation_service.py

# Integration tests — real DB via testcontainers
# tests/integration/test_placement_request_repo.py
# tests/integration/test_reputation_repo.py

# Fixtures in tests/conftest.py:
# - async_session (testcontainers PostgreSQL)
# - redis_client (testcontainers Redis)
# - mock_bot (aiogram Bot mock)
```

---

## Documentation

Проектная документация находится в папке `docs/`:

- **DOC_01_overview.md** — Обзор проекта, архитектура, структура
- **DOC_02_data_models.md** — Модели данных (все поля, ограничения, связи)
- **DOC_03_ux_and_flows.md** — UX, меню, клавиатуры, FSM, пользовательские флоу
- **DOC_04_services.md** — Сервисы, репозитории, бизнес-логика
- **DOC_05_infrastructure.md** — Celery, FastAPI, конфигурация, деплой
- **refactoring_v0.3/08_stage2_completion_report.md** — Отчёт о завершении Этапа 2
