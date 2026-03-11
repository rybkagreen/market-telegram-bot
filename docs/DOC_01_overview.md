# DOC-01: Обзор проекта, архитектура и структура

**RekHarborBot — Техническая документация v3.0**  
**Дата:** 2026-03-10 | **Статус:** Актуально

---

## 1. Что такое RekHarborBot

RekHarborBot — Telegram-бот, рекламная биржа для Telegram-каналов. Платформа соединяет рекламодателей (малый и средний бизнес) с владельцами тематических каналов. Весь цикл — от выбора каналов до оплаты, публикации и аналитики — происходит внутри Telegram без перехода на сторонние сайты.

**Конкурентная среда:** Telega.in, Epicstars, TGStat.  
**Ключевое отличие:** Telegram-native, простота для МСБ, эскроу-защита, аналитика из коробки.

### 1.1 Ценностное предложение

**Для рекламодателя:** запустить рекламу в 10 каналах за 5 минут прямо в Telegram. Деньги заморожены до публикации. После — отчёт с CPM, CTR, ROI.

**Для владельца канала:** подключи бота один раз — получай заявки и автоматические выплаты. Ты контролируешь что публиковать. Деньги поступают только после размещения.

### 1.2 Финансовая модель

- 1 кредит = 1 RUB
- Комиссия платформы: **20%** с каждого размещения
- Владелец канала получает: **80%** от суммы размещения
- Только opt-in каналы: владелец сам добавляет бота администратором

### 1.3 Тарифные планы

| Тариф | Цена | Особенности |
|-------|------|-------------|
| Free | 0 кр/мес | Базовый функционал, лимиты |
| Start | 299 кр/мес | Расширенные лимиты |
| Pro | 990 кр/мес | Полный функционал |
| Agency | 2999 кр/мес | B2B, белый лейбл, API |

---

## 2. Роли пользователей

| Роль | Код | Как получить | Функционал |
|------|-----|--------------|------------|
| Новый | `new` | По умолчанию при /start | Онбординг, выбор роли |
| Рекламодатель | `advertiser` | После выбора роли | Создание кампаний, аналитика, B2B |
| Владелец канала | `owner` | После регистрации канала | Управление каналами, заявки, выплаты |
| Обе роли | `both` | Если зарегистрирован в обеих | Комбинированное меню |
| Администратор | `admin` | Назначается вручную | Полный доступ, модерация |

---

## 3. Технический стек

### 3.1 Основные компоненты

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| Язык | Python | 3.13 | — |
| Bot Framework | aiogram | 3.x | Telegram Bot API |
| Web Framework | FastAPI | — | REST API, Mini App backend |
| ORM | SQLAlchemy | 2.0 async | Работа с БД |
| БД | PostgreSQL | — | Основное хранилище |
| Миграции | Alembic | — | Версионирование схемы |
| Очереди | Celery + Redis | — | Фоновые задачи |
| Кэш | Redis | — | FSM storage, кэш |
| AI | Mistral via OpenRouter | — | Генерация текстов, классификация |
| Telegram | Telethon | — | Парсинг каналов (read-only) |

### 3.2 AI-конфигурация

Переключается через `.env` переменную `AI_MODEL`:

| Среда | Модель | Стоимость |
|-------|--------|-----------|
| Dev / CI | `qwen/qwen3-235b-a22b:free` | Бесплатно (rate limit ~20 rps) |
| Production | `claude-sonnet-4-6` / Mistral | Платно |

### 3.3 Способы оплаты

- Telegram Stars
- CryptoBot (крипта)
- Банковская карта (ЮKassa)
- СБП

---

## 4. Структура проекта

```
src/
├── api/                          ← FastAPI REST API
│   ├── auth_utils.py             ← JWT авторизация
│   ├── dependencies.py           ← DI: get_db, get_current_user
│   ├── main.py                   ← FastAPI app, router registration
│   └── routers/
│       ├── analytics.py          ← GET /analytics/*
│       ├── auth.py               ← POST /auth/telegram
│       ├── billing.py            ← POST /billing/topup, /billing/withdraw
│       ├── campaigns.py          ← CRUD /campaigns/*
│       └── channels.py           ← GET /channels/catalog, /channels/{id}
│
├── bot/                          ← aiogram Telegram Bot
│   ├── main.py                   ← Dispatcher, middleware registration, router include
│   ├── assets/images/            ← banner.jpg, main_512x512.jpg
│   ├── data/
│   │   └── templates.py          ← Текстовые шаблоны сообщений
│   ├── filters/
│   │   └── admin.py              ← IsAdmin filter
│   ├── handlers/                 ← Обработчики входящих сообщений и callback
│   │   ├── admin/                ← Панель администратора
│   │   │   ├── ai.py             ← Управление AI-моделями
│   │   │   ├── analytics.py      ← Статистика платформы
│   │   │   ├── campaigns.py      ← Модерация кампаний
│   │   │   └── users.py          ← Управление пользователями
│   │   ├── analytics.py          ← Аналитика (advertiser + owner, раздельно)
│   │   ├── analytics_chats.py    ← Аналитика каналов
│   │   ├── b2b.py                ← B2B-пакеты
│   │   ├── billing.py            ← Пополнение баланса, тарифы
│   │   ├── cabinet.py            ← Личный кабинет (профиль, XP, репутация)
│   │   ├── callback_schemas.py   ← CallbackData схемы (MainMenuCB и др.)
│   │   ├── campaign_analytics.py ← Аналитика по конкретной кампании
│   │   ├── campaign_create_ai.py ← AI-wizard создания кампании (13 FSM состояний)
│   │   ├── campaigns.py          ← Управление кампаниями (список, детали, пауза)
│   │   ├── channel_owner.py      ← Управление каналами владельца, выплаты
│   │   ├── channels_db.py        ← Каталог каналов, фильтрация
│   │   ├── channels_db_mediakit.py ← Медиакит канала
│   │   ├── comparison.py         ← Сравнение каналов
│   │   ├── feedback.py           ← Обратная связь
│   │   ├── help.py               ← Помощь
│   │   ├── monitoring.py         ← Системный мониторинг (admin)
│   │   ├── notifications.py      ← Уведомления пользователя
│   │   ├── start.py              ← /start, онбординг, меню навигация ✅ Этап 0
│   │   ├── stats.py              ← /stats команда (публичный дашборд)
│   │   └── templates.py          ← Шаблоны постов
│   ├── keyboards/                ← InlineKeyboardMarkup builders
│   │   ├── admin.py
│   │   ├── billing.py
│   │   ├── cabinet.py
│   │   ├── campaign_ai.py        ← AI-wizard клавиатуры
│   │   ├── campaign_analytics.py
│   │   ├── campaign.py
│   │   ├── channels.py
│   │   ├── comparison.py
│   │   ├── feedback.py
│   │   ├── main_menu.py          ← Главное меню + роль-меню ✅ Этап 0
│   │   ├── mediakit.py
│   │   └── pagination.py
│   ├── middlewares/
│   │   ├── fsm_timeout.py        ← Таймаут FSM состояний
│   │   └── throttling.py         ← Rate limiting пользователей
│   ├── states/                   ← FSM StatesGroup
│   │   ├── admin.py
│   │   ├── campaign_create.py    ← AI wizard (13 состояний) — НЕ ТРОГАТЬ
│   │   ├── campaign.py           ← 9 состояний управления кампанией
│   │   ├── channel_owner.py      ← 6 состояний добавления канала
│   │   ├── channels.py
│   │   ├── comparison.py
│   │   ├── feedback.py
│   │   ├── mediakit.py
│   │   └── onboarding.py
│   └── utils/
│       ├── message_utils.py      ← Утилиты для работы с сообщениями
│       └── safe_callback.py      ← Безопасная обработка callback
│
├── config/
│   └── settings.py               ← Pydantic Settings: BOT_TOKEN, DB_URL, REDIS_URL, AI_MODEL...
│
├── constants/
│   ├── ai.py                     ← Промпты, лимиты токенов
│   ├── content_filter.py         ← Стоп-слова, пороги
│   ├── parser.py                 ← Настройки парсера
│   ├── payments.py               ← MIN_TOPUP, тарифы платежей
│   └── tariffs.py                ← Лимиты по тарифам
│
├── core/
│   ├── exceptions.py             ← Кастомные исключения
│   └── services/                 ← Бизнес-логика
│       ├── analytics_service.py
│       ├── b2b_package_service.py
│       ├── badge_service.py
│       ├── billing_service.py
│       ├── campaign_analytics_ai.py
│       ├── category_classifier.py
│       ├── comparison_service.py
│       ├── cryptobot_service.py
│       ├── link_tracking_service.py
│       ├── mailing_service.py
│       ├── mediakit_service.py
│       ├── mistral_ai_service.py
│       ├── notification_service.py
│       ├── payout_service.py
│       ├── placement_request_service.py ← НОВЫЙ (Этап 2)
│       ├── rating_service.py
│       ├── reputation_service.py        ← НОВЫЙ (Этап 2)
│       ├── review_service.py
│       ├── timing_service.py
│       ├── token_logger.py
│       ├── user_role_service.py
│       └── xp_service.py               ← НЕ ТРОГАТЬ
│
├── db/
│   ├── base.py                   ← DeclarativeBase
│   ├── session.py                ← async_sessionmaker, get_db()
│   ├── models/                   ← SQLAlchemy модели
│   │   ├── analytics.py          ← TelegramChat, ChatSnapshot
│   │   ├── b2b_package.py
│   │   ├── badge.py              ← Badge, UserBadge
│   │   ├── campaign.py           ← Campaign, CampaignStatus, CampaignType
│   │   ├── category.py           ← Category, Subcategory
│   │   ├── channel_mediakit.py
│   │   ├── channel_rating.py     ← ChannelRating (рейтинг канала)
│   │   ├── channel_settings.py   ← ChannelSettings (настройки владельца) ✅ Этап 1
│   │   ├── content_flag.py
│   │   ├── crypto_payment.py
│   │   ├── mailing_log.py        ← MailingLog, MailingStatus
│   │   ├── notification.py
│   │   ├── payout.py
│   │   ├── placement_request.py  ← PlacementRequest, PlacementStatus ✅ Этап 1
│   │   ├── reputation_history.py ← ReputationHistory, ReputationAction ✅ Этап 1
│   │   ├── reputation_score.py   ← ReputationScore ✅ Этап 1
│   │   ├── review.py
│   │   ├── transaction.py
│   │   └── user.py
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/             ← ~30 миграций Alembic
│   └── repositories/             ← Паттерн Repository
│       ├── base.py               ← BaseRepository
│       ├── campaign_repo.py
│       ├── category_repo.py
│       ├── channel_settings_repo.py ← НОВЫЙ (Этап 2)
│       ├── chat_analytics.py
│       ├── log_repo.py
│       ├── notification_repo.py
│       ├── payout_repo.py
│       ├── placement_request_repo.py ← НОВЫЙ (Этап 2)
│       ├── reputation_repo.py    ← НОВЫЙ (Этап 2)
│       ├── transaction_repo.py
│       └── user_repo.py
│
├── tasks/                        ← Celery задачи
│   ├── celery_app.py             ← Celery instance, 3 очереди
│   ├── celery_config.py          ← Beat расписание
│   ├── badge_tasks.py
│   ├── billing_tasks.py
│   ├── cleanup_tasks.py
│   ├── gamification_tasks.py
│   ├── mailing_tasks.py
│   ├── notification_tasks.py
│   ├── parser_tasks.py
│   └── rating_tasks.py
│
└── utils/
    ├── categories.py             ← Дерево категорий (11 топ-уровней)
    ├── content_filter/
    │   ├── filter.py             ← 3-уровневый фильтр
    │   └── stopwords_ru.json
    ├── mediakit_pdf.py
    ├── pdf_report.py
    └── telegram/
        ├── channel_rules_checker.py ← Проверка bot_is_admin
        ├── llm_classifier.py     ← LLM классификация тематики
        ├── llm_classifier_prompt.py
        ├── parser.py             ← Telethon парсер (read-only)
        ├── russian_lang_detector.py
        ├── sender.py             ← Отправка постов через Bot API
        └── topic_classifier.py
```

---

## 5. Архитектурные принципы

### 5.1 Паттерны

**Repository Pattern** — вся работа с БД через репозитории, handlers не знают о SQLAlchemy напрямую.

**Service Layer** — бизнес-логика в `core/services/`, репозитории инжектируются в сервисы через конструктор.

**FSM (Finite State Machine)** — многошаговые диалоги через aiogram FSM с Redis storage.

**Dependency Injection** — FastAPI DI для сессий БД и авторизации; в handlers — через `bot.get_session()`.

### 5.2 Важные ограничения

| Правило | Обоснование |
|---------|-------------|
| `xp_service.py` — не трогать | Геймификация работает, изменения сломают уровни пользователей |
| `campaign_create_ai.py` — не трогать | AI wizard (13 состояний), отдельный флоу |
| `User.advertiser_xp/owner_xp` — не трогать | XP ≠ Репутация, разные системы |
| Callback_data без префикса `main:` — не использовать для навигации | Архитектурное решение Этапа 0 |
| aiogram для публикации, Telethon только для парсинга | Публикация требует admin-прав бота |

### 5.3 Соглашения по именованию

- Модели: `CamelCase` → файл `snake_case.py`
- Репозитории: `ModelNameRepo` → файл `model_name_repo.py`
- Сервисы: `ModelNameService` → файл `model_name_service.py`
- Handlers: `src/bot/handlers/feature_name.py`
- Keyboards: `src/bot/keyboards/feature_name.py` с функциями `get_*_kb()`
- FSM States: `FeatureNameStates(StatesGroup)` → файл `src/bot/states/feature_name.py`
- Callback_data prefix: `main:` для навигации, `feature:action` для остального

### 5.4 Celery очереди (3 штуки)

| Очередь | Назначение | Приоритет |
|---------|------------|-----------|
| `critical` | Платежи, эскроу, авто-отклонения заявок | Высокий |
| `background` | Рассылки, уведомления, парсинг | Средний |
| `game` | XP, бейджи, геймификация | Низкий |

---

## 6. Статус реализации

### Завершено (Спринты 1–5.5 + Этапы 0–1)

| Компонент | Статус |
|-----------|--------|
| Статический анализ (Ruff, MyPy, Bandit, Flake8) | ✅ Все 0 |
| Архитектура меню v3.0 | ✅ Этап 0 |
| RT-001: main:analytics ≠ main:owner_analytics | ✅ Исправлен |
| 4 новых модели + 6 миграций | ✅ Этап 1 |
| Celery: 3 очереди, без дублей Beat | ✅ |
| ContentFilter: пороги, стоп-слова | ✅ |
| Геймификация: XP, уровни, бейджи | ✅ |
| Медиакит каналов | ✅ |
| Система выплат (модели) | ✅ |
| B2B пакеты | ✅ |
| Система отзывов (модели) | ✅ |
| opt-in регистрация каналов | ✅ |

### В работе (Этап 2)

| Компонент | Статус |
|-----------|--------|
| PlacementRequestRepo, ChannelSettingsRepo, ReputationRepo | 🔄 |
| PlacementRequestService, ReputationService | 🔄 |
| Модификации BillingService, MailingService, PayoutService | 🔄 |

### Не начато (Этапы 3–7)

| Компонент | Этап |
|-----------|------|
| placement.py handler (9-шаговый флоу) | 3 |
| arbitration.py handler | 3 |
| channel_settings.py handler | 3 |
| FSM States: Placement, Arbitration, ChannelSettings | 4 |
| Keyboards: placement, arbitration, channel_settings | 5 |
| API routers: placements, channel_settings, reputation | 6 |
| Тесты (6 файлов) | 7 |
| Ротация BOT_TOKEN | ⚠️ Срочно |
