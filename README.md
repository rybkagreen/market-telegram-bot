# RekHarborBot — Telegram Advertising Exchange

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![SQLAlchemy 2](https://img.shields.io/badge/SQLAlchemy-2-red.svg)](https://docs.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**RekHarborBot** — Telegram-бот, рекламная биржа для Telegram-каналов. Платформа соединяет рекламодателей (малый и средний бизнес) с владельцами тематических каналов. Весь цикл — от выбора каналов до оплаты, публикации и аналитики — происходит внутри Telegram без перехода на сторонние сайты.

**Конкурентная среда:** Telega.in, Epicstars, TGStat.
**Ключевое отличие:** Telegram-native, простота для МСБ, эскроу-защита, аналитика из коробки.

---

## 📋 Оглавление

- [Ценностное предложение](#-ценностное-предложение)
- [Финансовая модель](#-финансовая-модель)
- [Тарифы](#-тарифы)
- [Роли пользователей](#-роли-пользователей)
- [Архитектура](#-архитектура)
- [Стек технологий](#-стек-технологий)
- [Быстрый старт](#-быстрый-старт)
- [Структура проекта](#-структура-проекта)
- [База данных](#-база-данных)
- [Контент-фильтр](#-контент-фильтр)
- [Система репутации](#-система-репутации)
- [Разработка](#-разработка)
- [Деплой](#-деплой)
- [Мониторинг](#-мониторинг)
- [Лицензия](#-лицензия)

---

## 🆕 Что нового в v4.3

### Юридические профили и договоры

- **LegalProfile** — юридические профили для пользователей (юрлица, ИП, самозанятые, физлица)
- **Contract** — договоры с платформой (оказание услуг, на размещение рекламы, правила платформы)
- **ContractSignature** — подписание договоров (нажатием кнопки, СМС-кодом)
- **Автоматическое подписание** — при смене юридического статуса
- **Хранение документов** — PDF-генерация, шаблоны договоров

### ОРД-регистрация (OrdRegistration)

- **Автоматическая регистрация** — реклама в ОРД (Ordinary Advertising)
- **Статусы регистрации** — pending, registered, token_received, reported, failed
- **Интеграция с оператором** — через API или стаб-провайдер
- **Отчётность** — автоматическая отправка отчётов

### Аудит и безопасность

- **AuditLog** — журнал аудита всех критических операций
- **Field Encryption** — шифрование персональных данных (ИНН, паспортные данные)
- **Gitleaks** — автоматическая проверка на секреты в git
- **SonarQube** — статический анализ кода

### Прочие улучшения

- **Referral Program** — реферальная программа для тарифов Pro/Agency
- **Reviews & Reputation** — расширенная система отзывов и репутации
- **Video Support** — загрузка видео в кампании
- **Link Tracking** — трекинг кликов по ссылкам в кампаниях
- **Admin Panel Mini App** — 7 экранов, 9 API endpoints
- **Feedback System** — полная система обратной связи (пользователь → админ → ответ)

---

## ✨ Ценностное предложение

### Для рекламодателя

**Запустить рекламу в 10 каналах за 5 минут прямо в Telegram.** Деньги заморожены до публикации. После — отчёт с CPM, CTR, ROI.

- ✅ **9-шаговый мастер создания кампании** — категория → каналы → текст → арбитраж → оплата → публикация
- ✅ **ИИ-генерация текстов** — Mistral AI (официальный SDK, 3 варианта)
- ✅ **Таргетинг** — по 11 категориям, размеру чатов, рейтингу
- ✅ **Эскроу-защита** — средства блокируются до публикации
- ✅ **Аналитика** — CPM, CTR, ROI, топ каналов
- ✅ **Юридическая защита** — договоры, ORD-регистрация, видео в кампаниях (v4.3)

### Для владельца канала

**Подключи бота один раз — получай заявки и автоматические выплаты.** Ты контролируешь что публиковать. Деньги поступают только после размещения.

- ✅ **Opt-in регистрация** — владелец сам добавляет бота администратором
- ✅ **Автоматические заявки** — уведомления о новых размещениях
- ✅ **Арбитраж** — принятие/отклонение/контр-предложение (макс 3 раунда)
- ✅ **Настройки монетизации** — цена, пакеты, расписание, авто-принятие
- ✅ **Выплаты 85%** — после публикации 85% владельцу, 15% комиссия платформы (v4.2)
- ✅ **Репутация** — система доверия 0-10, отзывы после размещения
- ✅ **Реферальная программа** — бонусы за приглашённых пользователей (v4.3)

---

## 💰 Финансовая модель v4.2

- **1 кредит = 1 RUB** (виртуальная единица для упрощения расчётов)
- **Комиссия платформы:** 15% с каждого размещения (v4.2)
- **Владелец канала получает:** 85% от суммы размещения (v4.2)
- **Только opt-in каналы:** владелец сам добавляет бота администратором
- **Налог:** ИП УСН 6% (платформа удерживает автоматически)

### Комиссии и сборы

| Сбор | Размер | Кто платит |
|------|--------|------------|
| Комиссия платформы | 15% | Удерживается из размещения |
| ЮKassa fee | 3.5% | Пользователь при пополнении |
| Вывод средств | 1.5% | Владелец при выплате |
| Налог (УСН) | 6% | Платформа (из прибыли) |

### Способы оплаты

- **ЮKassa** — банковская карта, СБП, YooMoney (основной способ v4.2)
- ~~Telegram Stars~~ — отключено
- ~~CryptoBot~~ — отключено

---

## 📦 Тарифы v4.2

| Тариф | Цена | Кампаний/мес | AI запросов/мес | Форматы публикаций | Каналов в кампании | Реферальная программа |
|-------|------|--------------|-----------------|-------------------|-------------------|----------------------|
| **Free** | 0 ₽/мес | 1 | 0 | post_24h | 3 | ❌ |
| **Starter** | 490 ₽/мес | 5 | 3 | post_24h, post_48h | 10 | ❌ |
| **Pro** | 1 490 ₽/мес | 20 | 20 | post_24h, post_48h, post_7d | 50 | ✅ |
| **Agency** | 4 990 ₽/мес | ∞ | ∞ | Все 5 форматов | ∞ | ✅ |

**Форматы публикаций:**
- `post_24h` — обычный пост на 24 часа (×1.0)
- `post_48h` — обычный пост на 48 часов (×1.4)
- `post_7d` — обычный пост на 7 дней (×2.0)
- `pin_24h` — закреплённый пост на 24 часа (×3.0)
- `pin_48h` — закреплённый пост на 48 часов (×4.0)

**v4.3 изменения:**
- ~~B2B-пакеты~~ — удалены (заменены на тарифы Pro/Agency)
- ✅ Реферальная программа — для тарифов Pro/Agency
- ✅ Юридические профили — для владельцев и рекламодателей
- ✅ ORD-регистрация — автоматическая регистрация рекламы в ОРД

---

## 👥 Роли пользователей

| Роль | Код | Как получить | Функционал |
|------|-----|--------------|------------|
| **Новый** | `new` | По умолчанию при /start | Онбординг, выбор роли |
| **Рекламодатель** | `advertiser` | После выбора роли | Создание кампаний, аналитика, юридические профили, ORD |
| **Владелец канала** | `owner` | После регистрации канала | Управление каналами, заявки, выплаты, репутация |
| **Обе роли** | `both` | Если зарегистрирован в обеих | Комбинированное меню |
| **Администратор** | `admin` | Назначается вручную | Полный доступ, модерация, админ-панель (Mini App) |

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            RekHarborBot                                 │
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
│  │  (FSM)       │   │  (3 queues)  │   │  (read-only) │               │
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
│  │  PostgreSQL  │   │    Redis     │   │  Mistral AI  │               │
│  │  (asyncpg)   │   │  (FSM+Cache) │   │  (Mistral)   │               │
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
| **Parser** | Telethon | Поиск и парсинг Telegram каналов (read-only) |
| **Workers** | Celery + Beat | Асинхронные задачи (3 очереди) |
| **DB** | PostgreSQL 16 | Хранение данных (SQLAlchemy 2 async) |
| **Cache** | Redis 7 | FSM storage, rate limiting, AI кэш |
| **AI** | Mistral AI (официальный SDK) | Генерация текстов, классификация |
| **Payments** | ЮKassa | Пополнение баланса (карта, СБП, YooMoney) |

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
| **AI** | mistralai (официальный SDK) | 1.12.4+ |
| **Parser** | Telethon | 1.36+ |
| **Content Filter** | pymorphy3, rapidfuzz | 2.0+, 3.6+ |
| **Payments** | yookassa | 3.2.0 |
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
| **Monitoring** | GlitchTip, Sentry, Grafana, Flower | Ошибки, метрики, Celery dashboard |
| **Code Quality** | SonarQube, Ruff, MyPy | Статический анализ, type checking |
| **Security** | Gitleaks, Field Encryption | Secrets detection, PII protection |
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
# Отредактировать .env (см. шаблон ниже)
```

**Минимальный `.env` для разработки:**

```env
# ══════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=RekHarborBot
ADMIN_IDS=123456789,987654321

# Telethon (парсер чатов)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION_NAME=parser

# ══════════════════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ══════════════════════════════════════════════════════════════
DATABASE_URL=postgresql+asyncpg://rekharbor:password@localhost:5432/rekharbor
DATABASE_SYNC_URL=postgresql://rekharbor:password@localhost:5432/rekharbor

# ══════════════════════════════════════════════════════════════
# REDIS
# ══════════════════════════════════════════════════════════════
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# ══════════════════════════════════════════════════════════════
# AI — Mistral (официальный API)
# Ключ: https://console.mistral.ai → API Keys → Create new key
# ══════════════════════════════════════════════════════════════
MISTRAL_API_KEY=your_mistral_api_key_here
AI_MODEL=mistral-medium-latest
AI_TIMEOUT=60

# ══════════════════════════════════════════════════════════════
# FIELD-LEVEL ENCRYPTION (S6A — required for legal_profiles PII)
# FIELD_ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# SEARCH_HASH_KEY:      python -c "import secrets; print(secrets.token_hex(32))"
# ══════════════════════════════════════════════════════════════
FIELD_ENCRYPTION_KEY=generate_with_fernet_see_above
SEARCH_HASH_KEY=generate_with_secrets_see_above

# ══════════════════════════════════════════════════════════════
# JWT для Mini App аутентификации
# Генерировать: python -c "import secrets; print(secrets.token_hex(32))"
# ══════════════════════════════════════════════════════════════
JWT_SECRET=your_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# ══════════════════════════════════════════════════════════════
# ПЛАТЕЖИ — ЮKassa (v4.2: только ЮKassa, Stars и CryptoBot отключены)
# ══════════════════════════════════════════════════════════════
YOOKASSA_SHOP_ID=your_shop_id_here
YOOKASSA_SECRET_KEY=your_secret_key_here
YOOKASSA_RETURN_URL=https://t.me/YOUR_BOT_USERNAME

# ══════════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ
# ══════════════════════════════════════════════════════════════
ENVIRONMENT=development
DEBUG=true
API_PORT=8001  # Note: port not exposed to host — API accessible only via nginx or docker exec
SENTRY_DSN=your_sentry_dsn_here  # опционально
SONAR_TOKEN=your_sonar_token_here  # опционально

# Platform v4.2
PLATFORM_COMMISSION=0.15
OWNER_SHARE=0.85
MIN_PRICE_PER_POST=1000
MIN_PAYOUT=1000
MIN_TOPUP=500
MIN_CAMPAIGN_BUDGET=2000
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

#### 7. Запустить Celery workers

```bash
# Worker (все очереди)
celery -A src.tasks.celery_app worker -Q critical,background,game -l info

# Отдельные worker'ы по очередям
celery -A src.tasks.celery_app worker -Q critical -l info -c 4
celery -A src.tasks.celery_app worker -Q background -l info -c 8
celery -A src.tasks.celery_app worker -Q game -l info -c 2

# Beat (периодические задачи)
celery -A src.tasks.celery_app beat -l info

# Flower (мониторинг Celery)
celery -A src.tasks.celery_app flower --port=5555
```

#### 8. Запустить Mini App (development, опционально)

```bash
cd mini_app
npm install
npm run dev
# Прокси на /api → http://localhost:8001 (local dev only — not Docker)
```

---

## 📁 Структура проекта

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
│   │   │   │   └── channels_catalog.py  # каталог каналов
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
│   │   │   │   ├── channel_settings.py  # настройки канала
│   │   │   │   ├── placement.py         # заявки на размещение
│   │   │   │   └── arbitration.py       # арбитраж
│   │   │   ├── billing/          # Биллинг
│   │   │   │   ├── __init__.py
│   │   │   │   └── billing.py
│   │   │   └── admin/            # Админка
│   │   │       ├── __init__.py
│   │   │       └── admin.py
│   │   ├── states/               # FSM StatesGroup
│   │   │   ├── campaign.py       # 9 состояний
│   │   │   ├── campaign_create.py  # 13 состояний AI wizard — НЕ ТРОГАТЬ
│   │   │   ├── channel_owner.py  # 6 состояний
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
│   │       ├── billing.py        # POST /billing/topup, /billing/withdraw, /webhooks/yookassa
│   │       ├── placements.py     # ✅ Этап 6: /placements/*
│   │       ├── channel_settings.py  # ✅ Этап 6: /channel-settings/*
│   │       ├── reputation.py     # ✅ Этап 6: /reputation/*
│   │       ├── legal_profile.py  # ✅ v4.3: /legal-profile/*
│   │       ├── contracts.py      # ✅ v4.3: /contracts/*
│   │       ├── ord.py            # ✅ v4.3: /ord/* (ОРД-регистрация)
│   │       ├── reviews.py        # ✅ v4.3: /reviews/*
│   │       ├── categories.py     # ✅ v4.3: /categories/*
│   │       ├── uploads.py        # ✅ v4.3: /uploads/* (видео, изображения)
│   │       ├── feedback.py       # ✅ v4.3: /feedback/*
│   │       ├── admin.py          # ✅ v4.3: /admin/* (7 экранов, 9 endpoints)
│   │       ├── health.py         # GET /health, /health/balances (ESCROW-001)
│   │       └── webhooks.py       # POST /webhooks/*
│   │
│   ├── db/                       # работа с БД
│   │   ├── base.py               # DeclarativeBase
│   │   ├── session.py            # async_sessionmaker, get_db()
│   │   ├── models/               # SQLAlchemy модели (20+ моделей)
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
│   │   │   ├── legal_profile.py  # LegalProfile ✅ v4.3 (юрлица, ИП, самозанятые)
│   │   │   ├── contract.py       # Contract ✅ v4.3 (договоры с платформой)
│   │   │   ├── contract_signature.py  # ContractSignature ✅ v4.3
│   │   │   ├── audit_log.py      # AuditLog ✅ v4.3 (журнал аудита)
│   │   │   ├── publication_log.py  # PublicationLog ✅ v4.3 (лог публикаций)
│   │   │   ├── ord_registration.py  # OrdRegistration ✅ v4.3 (ОРД-регистрация)
│   │   │   ├── platform_account.py  # PlatformAccount ✅ v4.2 (счет платформы)
│   │   │   └── ...
│   │   ├── migrations/           # Alembic миграции (head: 010+)
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
│   │       ├── legal_profile_repo.py      # НОВЫЙ ✅ v4.3
│   │       ├── contract_repo.py           # НОВЫЙ ✅ v4.3
│   │       ├── audit_log_repo.py          # НОВЫЙ ✅ v4.3
│   │       └── ...
│   │
│   ├── core/                     # бизнес-логика
│   │   ├── exceptions.py         # кастомные исключения
│   │   └── services/
│   │       ├── billing_service.py      # платежи, эскроу
│   │       ├── mailing_service.py      # рассылки, публикация placement
│   │       ├── payout_service.py       # выплаты (velocity check, fee calculation)
│   │       ├── notification_service.py # уведомления
│   │       ├── analytics_service.py    # аналитика
│   │       ├── mistral_ai_service.py   # ИИ-генерация (Mistral AI SDK)
│   │       ├── user_role_service.py    # роли пользователей
│   │       ├── xp_service.py           # геймификация (НЕ ТРОГАТЬ)
│   │       ├── badge_service.py        # бейджи (НЕ ТРОГАТЬ)
│   │       ├── placement_request_service.py  # НОВЫЙ ✅ Этап 2
│   │       ├── reputation_service.py       # НОВЫЙ ✅ Этап 2
│   │       ├── legal_profile_service.py    # НОВЫЙ ✅ v4.3 (юр профили)
│   │       ├── contract_service.py         # НОВЫЙ ✅ v4.3 (договоры)
│   │       ├── ord_service.py              # НОВЫЙ ✅ v4.3 (ОРД-регистрация)
│   │       ├── publication_service.py      # НОВЫЙ ✅ Этап 2 (публикация)
│   │       ├── link_tracking_service.py    # НОВЫЙ ✅ v4.3 (трекинг ссылок)
│   │       └── ...
│   │
│   ├── tasks/                    # Celery задачи
│   │   ├── celery_app.py         # Celery instance, 3 очереди (critical, background, monitoring)
│   │   ├── celery_config.py      # Beat расписание
│   │   ├── billing_tasks.py      # expire placements, unblock users
│   │   ├── mailing_tasks.py      # send campaigns, publish placements
│   │   ├── notification_tasks.py # expiry notifications
│   │   ├── parser_tasks.py       # parse channels
│   │   ├── gamification_tasks.py # reputation recovery
│   │   ├── rating_tasks.py       # update channel ratings
│   │   ├── cleanup_tasks.py      # cleanup old logs
│   │   ├── publication_tasks.py  # ✅ Этап 2: publish_placement, delete_published_post
│   │   ├── placement_tasks.py    # ✅ Этап 2: placement workflow
│   │   ├── ord_tasks.py          # ✅ v4.3: ORD registration tasks
│   │   ├── integrity_tasks.py    # ✅ v4.3: data integrity checks
│   │   └── badge_tasks.py        # ✅ v4.3: badge assignments
│   │
│   ├── utils/                    # утилиты
│   │   ├── telegram/
│   │   │   ├── parser.py         # Telethon (read-only)
│   │   │   ├── sender.py         # отправка постов (Bot API)
│   │   │   ├── channel_rules_checker.py  # bot_is_admin проверка
│   │   │   ├── llm_classifier.py # LLM классификация тем
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
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```

---

## 🗄️ База данных

### Основные модели

#### 1. User (Пользователи)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer PK | — |
| `telegram_id` | BigInteger UNIQUE | Telegram user_id |
| `username` | String(64) | @username без @ |
| `first_name` | String(128) | Имя в Telegram |
| `role` | String(20) | new/advertiser/owner/both/admin |
| `credits` | Numeric(12,2) | Баланс кредитов (1 кр = 1₽) |
| `plan` | String(20) | free/start/pro/agency |
| `advertiser_xp` / `owner_xp` | Integer | XP рекламодателя / владельца |
| `advertiser_level` / `owner_level` | Integer | Уровень (0-6) |
| `is_banned` | Boolean | Глобальная блокировка |
| `referral_code` | String(20) UNIQUE | Реферальный код |

**⚠️ XP/levels не связаны с ReputationScore — разные системы.**

#### 2. TelegramChat (Каналы)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer PK | — |
| `telegram_id` | BigInteger UNIQUE | Telegram channel id |
| `username` | String(64) UNIQUE | @handle |
| `title` | String(255) | Название канала |
| `owner_id` | Integer FK→users.id | Владелец (SET NULL) |
| `member_count` | Integer | Подписчиков |
| `avg_views` | Integer | Среднее просмотров |
| `rating` | Float | Рейтинг канала (0-10) |
| `topic` / `subcategory` | String | Тематика (AI классификация) |
| `is_opt_in` | Boolean | Добровольная регистрация |
| `bot_is_admin` | Boolean | Бот — администратор |

#### 3. Campaign (Кампании)

**Enum CampaignStatus:** DRAFT, QUEUED, RUNNING, SCHEDULED, DONE, ERROR, PAUSED, CANCELLED, MODERATION

**Enum CampaignType:** BROADCAST, PLACEMENT

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer PK | — |
| `advertiser_id` | Integer FK→users.id | CASCADE |
| `title` | String(255) | Название |
| `text` | Text | Текст объявления |
| `status` | CampaignStatus | — |
| `type` | CampaignType | broadcast/placement |
| `placement_request_id` | Integer FK | SET NULL ✅ Этап 1 |
| `budget` / `spent` | Numeric(12,2) | Бюджет / потрачено |
| `ctr` | Float | CTR (%) |
| `views_total` / `clicks_total` | Integer | Просмотры / клики |

#### 4. PlacementRequest (Заявки на размещение) ✅ Этап 1

**Enum PlacementStatus:** PENDING_OWNER, COUNTER_OFFER, PENDING_PAYMENT, ESCROW, PUBLISHED, FAILED, REFUNDED, CANCELLED

**Жизненный цикл:**
```
pending_owner ──► counter_offer ──► pending_owner (макс 3 раунда)
     │                                     │
     ▼                                     ▼
pending_payment ◄────────────────────────────
     │
     ▼
  escrow ──► published ──► выплата 80/20
     │
     └──► failed ──► refunded
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer PK | — |
| `advertiser_id` / `channel_id` / `campaign_id` | Integer FK | CASCADE |
| `proposed_price` / `final_price` | Numeric(10,2) | Цена |
| `proposed_schedule` / `final_schedule` | DateTime | Время публикации |
| `final_text` | Text | Финальный текст |
| `status` | PlacementStatus | — |
| `rejection_reason` | String(500) | Мин 10 символов с буквами |
| `counter_offer_count` | Integer | Макс 3 |
| `escrow_transaction_id` | Integer FK | SET NULL |
| `expires_at` | DateTime | Дедлайн +24ч |

#### 5. ChannelSettings (Настройки канала) ✅ Этап 1

PK = `channel_id` (one-to-one с TelegramChat).

**Системные константы:**
- `MIN_PRICE_PER_POST = 1000` (1000 ₽ v4.2)
- `PLATFORM_COMMISSION = 0.15` (15% v4.2)
- `MAX_PACKAGE_DISCOUNT = 50` (%)
- `MAX_POSTS_PER_DAY = 5`, `MAX_POSTS_PER_WEEK = 35`

| Поле | Тип | Описание |
|------|-----|----------|
| `channel_id` | Integer PK FK | CASCADE |
| `owner_id` | Integer FK | CASCADE |
| `price_per_post` | Numeric(10,2) | ≥ 100 |
| `daily_package_enabled` / `weekly_package_enabled` | Boolean | Пакеты |
| `subscription_enabled` | Boolean | Подписка |
| `publish_start_time` / `publish_end_time` | Time | 09:00-21:00 |
| `auto_accept_enabled` | Boolean | Авто-принятие |

#### 6. ReputationScore (Репутация) ✅ Этап 1

PK = `user_id` (one-to-one с User). **НЕ путать с XP/levels.**

| Поле | Тип | Описание |
|------|-----|----------|
| `user_id` | Integer PK FK | CASCADE |
| `advertiser_score` / `owner_score` | Float | 0.0–10.0, старт 5.0 |
| `advertiser_violations` / `owner_violations` | Integer | Счётчик нарушений |
| `is_advertiser_blocked` / `is_owner_blocked` | Boolean | Блокировка |
| `blocked_until` | DateTime | Срок блокировки |

**Ключевые правила:**
- После 7-дневного бана: сброс до 2.0
- 5+ нарушений: перманентная блокировка
- 3 невалидных отказа подряд: бан 7 дней

#### 7. ReputationHistory (История репутации) ✅ Этап 1

**Enum ReputationAction (16 значений):**
- Бонусы: PUBLICATION (+1), REVIEW_5STAR (+2), REVIEW_4STAR (+1), RECOVERY_30DAYS (+5)
- Штрафы: CANCEL_BEFORE (-5), CANCEL_AFTER (-20), REJECT_INVALID_1 (-10), REJECT_INVALID_2 (-15), REJECT_INVALID_3 (-20 + бан)

#### 8. Transaction (Транзакции)

**Enum TransactionType:** TOPUP, REFUND, ESCROW_FREEZE, ESCROW_RELEASE, COMMISSION, PAYOUT_FEE

**Удалены (v4.2):** `SPEND`, `ADJUSTMENT`, `BONUS`, `WITHDRAWAL`

#### 9. MailingLog (Логи рассылок)

**Enum MailingStatus:** PENDING, SENT, FAILED, SKIPPED, CANCELLED, RETRY, TIMEOUT, BOUNCED, BLOCKED

| Поле | Тип | Описание |
|------|-----|----------|
| `campaign_id` / `channel_id` | Integer FK | CASCADE |
| `placement_request_id` | Integer FK | SET NULL ✅ Этап 1 |
| `status` | MailingStatus | — |
| `message_id` | BigInteger | Telegram message_id |
| `views_count` / `clicks_count` | Integer | Метрики |

#### 10. Payout (Выплаты)

**Enum PayoutStatus:** PENDING, PROCESSING, PAID, FAILED, CANCELLED

#### 11. Review (Отзывы)

**Enum ReviewerRole:** ADVERTISER, OWNER

| Поле | Тип | Описание |
|------|-----|----------|
| `reviewer_id` / `reviewed_id` | Integer FK | Кто о ком |
| `placement_id` | Integer FK | SET NULL |
| `stars` | Integer | 1–5 |
| `comment` | String(1000) | Текст |

#### 12. Badge / UserBadge (Бейджи)

Геймификация: достижения пользователей.

#### 13. ChannelRating (Рейтинг канала)

**⚠️ ChannelRating ≠ ReputationScore:**
- `ChannelRating` — характеристика канала (качество контента, аудитории)
- `ReputationScore` — характеристика пользователя (надёжность контрагента)

#### 14. B2BPackage (B2B пакеты)

| Пакет | Цена | Каналов | Бюджет/канал | Охват | Срок |
|-------|------|---------|--------------|-------|------|
| Стартап | 1500 кр | 5 | 300 кр | ~25K | 7 дней |
| Бизнес | 5000 кр | 10 | 500 кр | ~60K | 14 дней |
| Премиум | 25000 кр | 25 | 1000 кр | ~200K | 30 дней |

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
```

**Текущая миграция:** `006_add_type_to_campaigns` (HEAD)

**История миграций:**
```
82cd153da6b8  initial_schema
  ↓
001_create_placement_requests
  ↓
002_create_channel_settings
  ↓
003_create_reputation_scores
  ↓
004_create_reputation_history
  ↓
005_add_placement_request_to_mailing_log
  ↓
006_add_type_to_campaigns  ← HEAD
```

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
│ - HIGH_RISK (≥3) → BLOCK        │
│ - MEDIUM_RISK (1-2) → L2        │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Уровень 2: morph_check()        │  < 10ms
│ - pymorphy3 (все формы слов)   │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Уровень 3: llm_check()          │  1-3 сек
│ - Mistral AI (официальный SDK)  │
│ - Контекстный анализ            │
└──────────────┬──────────────────┘
               │
               ▼
         BLOCKED ❌ или PASS ✅
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

---

## ⭐ Система репутации

### Диапазон и значения

- **Диапазон:** 0.0 – 10.0
- **Стартовое значение:** 5.0
- **После 7-дневного бана:** сброс до 2.0
- **5+ нарушений:** перманентная блокировка

### Бонусы

| Событие | Δ Репутация | Кому |
|---------|-------------|------|
| Успешная публикация | +1 | advertiser + owner |
| Отзыв 5⭐ | +2 | получатель отзыва |
| Отзыв 4⭐ | +1 | — |
| Отзыв 3⭐ | 0 | — |
| Отзыв 2⭐ | -1 | — |
| Отзыв 1⭐ | -2 | — |
| 30 дней без нарушений | +5 | — |

### Штрафы

| Событие | Δ Репутация | Последствия |
|---------|-------------|-------------|
| Отмена до эскроу | -5 | — |
| Отмена после эскроу | -20 | — |
| 3 отмены за 30 дней | -20 | + предупреждение |
| Невалидный отказ (1й) | -10 | — |
| Невалидный отказ (2й) | -15 | — |
| Невалидный отказ (3й) | -20 | Бан 7 дней |
| Частые отказы (>50%) | -5 | — |

### Блокировки

| Условие | Тип | Продолжительность |
|---------|-------|-------------------|
| 3й невалидный отказ подряд | owner_blocked | 7 дней |
| Score ≤ 0 | role_blocked | Перманентная |
| violations ≥ 5 | role_blocked | Перманентная |
| is_banned (глобально) | full_ban | Перманентная (admin) |

### Валидация причины отклонения

```python
# Правила валидной rejection_reason:
min_length = 10 символов
must_contain = re.search(r'[а-яёa-z]', reason, re.IGNORECASE)
blacklist = ["asdfgh", "aaaaaa", "123456", "qwerty", "нет", "no", "не хочу"]
# Невалидная причина → штраф репутации + повтор ввода
```

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
# Worker (все очереди)
celery -A src.tasks.celery_app worker -Q critical,background,game -l info

# Отдельные worker'ы по очередям
celery -A src.tasks.celery_app worker -Q critical -l info -c 4
celery -A src.tasks.celery_app worker -Q background -l info -c 8
celery -A src.tasks.celery_app worker -Q game -l info -c 2

# Beat (периодические задачи)
celery -A src.tasks.celery_app beat -l info

# Flower (мониторинг Celery)
celery -A src.tasks.celery_app flower --port=5555
```

### Запуск Mini App (development)

```bash
cd mini_app
npm install
npm run dev
# Прокси на /api → http://localhost:8001 (local dev only — not Docker)
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

### Статический анализ

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
- `worker-critical` — Celery worker (queue: critical, 4 concurrency)
- `worker-background` — Celery worker (queue: background, 8 concurrency)
- `worker-game` — Celery worker (queue: game, 2 concurrency)
- `beat` — Celery Beat (ТОЛЬКО ОДИН ЭКЗЕМПЛЯР)
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
BOT_USERNAME=RekHarborBot

DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
DATABASE_SYNC_URL=postgresql://user:pass@postgres:5432/db

REDIS_URL=redis://redis:6379/0
REDIS_FSM_DB=1

# AI — Mistral official SDK
MISTRAL_API_KEY=...
AI_MODEL=mistral-medium-latest

# Payments — YooKassa only (v4.2)
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...

TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...

ADMIN_IDS=123456789

API_SECRET_KEY=...

WEBHOOK_URL=https://yourdomain.com/webhook
MINI_APP_URL=https://yourdomain.com/app

SENTRY_DSN=https://...@sentry.io/...
```

---

## 📊 Мониторинг

### Sentry (ошибки)

```python
# src/bot/main.py
import sentry_sdk

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
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
- Очереди (critical, background, game)
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
- **Support:** @rekharbor_support (Telegram)

---

## 📚 Дополнительная документация

Документация проекта находится в папке `docs/`:

- **[DOC_01_overview.md](docs/DOC_01_overview.md)** — Обзор проекта, архитектура, структура
- **[DOC_02_data_models.md](docs/DOC_02_data_models.md)** — Модели данных (все поля, ограничения, связи)
- **[DOC_03_ux_and_flows.md](docs/DOC_03_ux_and_flows.md)** — UX, меню, клавиатуры, FSM, пользовательские флоу
- **[DOC_04_services.md](docs/DOC_04_services.md)** — Сервисы, репозитории, бизнес-логика
- **[DOC_05_infrastructure.md](docs/DOC_05_infrastructure.md)** — Celery, FastAPI, конфигурация, деплой
- **[refactoring_v0.3/08_stage2_completion_report.md](docs/refactoring_v0.3/08_stage2_completion_report.md)** — Отчёт о завершении Этапа 2

**Другие документы:**
- [LOCAL_CHECKS.md](LOCAL_CHECKS.md) — локальные проверки кода
- [DOCKER_README.md](DOCKER_README.md) — Docker инструкция
- [CLOUDFLARE_SETUP.md](CLOUDFLARE_SETUP.md) — настройка Cloudflare Tunnel
- [QWEN.md](QWEN.md) — контекст проекта для Qwen Code
