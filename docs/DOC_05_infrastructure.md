# DOC-05: Инфраструктура, API, Celery и Конфигурация

**RekHarborBot — Техническая документация v3.0**  
**Дата:** 2026-03-10 | Celery задачи, FastAPI роутеры, конфигурация, деплой

---

## 1. Конфигурация (`src/config/settings.py`)

Pydantic `BaseSettings`. Все значения — из переменных окружения или `.env` файла.

```python
class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str          # ⚠️ Требует ротации
    BOT_USERNAME: str       # @RekHarborBot

    # Database
    DATABASE_URL: str       # postgresql+asyncpg://user:pass@host/db
    DATABASE_SYNC_URL: str  # postgresql://... (для Alembic)

    # Redis
    REDIS_URL: str          # redis://localhost:6379/0
    REDIS_FSM_DB: int = 1   # отдельная БД для FSM storage

    # AI
    AI_MODEL: str = "qwen/qwen3-235b-a22b:free"   # dev
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Payments
    CRYPTOBOT_TOKEN: str
    CRYPTOBOT_WEBHOOK_URL: str
    YUKASSA_SHOP_ID: str
    YUKASSA_SECRET_KEY: str

    # Platform
    PLATFORM_COMMISSION: float = 0.20     # 20%
    MIN_PRICE_PER_POST: int = 100         # кр
    MIN_PAYOUT: int = 100                 # кр минимум для вывода
    MIN_TOPUP: int = 100                  # кр минимум для пополнения
    PLACEMENT_TIMEOUT_HOURS: int = 24     # таймер ответа владельца
    PAYMENT_TIMEOUT_HOURS: int = 24       # таймер оплаты
    MAX_COUNTER_OFFERS: int = 3           # максимум раундов арбитража
    PUBLICATION_RETRY_HOURS: int = 1      # retry при ошибке публикации

    # Telethon (парсер)
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_SESSION_NAME: str = "parser"

    # Admin
    ADMIN_TELEGRAM_IDS: list[int] = []

    # FastAPI
    API_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## 2. База данных (`src/db/session.py`)

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=False,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## 3. Alembic миграции (`src/db/migrations/`)

### Порядок миграций (актуальный head — 006)

```
82cd153da6b8  initial_schema
  ↓
[множество миграций Sprint 1-5]
  ↓
9de36b5c6cd5  последняя до Sprint 6
  ↓
001_create_placement_requests     (PlacementRequest + ENUM PlacementStatus)
  ↓
002_create_channel_settings       (ChannelSettings)
  ↓
003_create_reputation_scores      (ReputationScore)
  ↓
004_create_reputation_history     (ReputationHistory + ENUM ReputationAction)
  ↓
005_add_placement_request_to_mailing_log
  ↓
006_add_type_to_campaigns         (CampaignType + ENUM)  ← HEAD
```

### Команды

```bash
alembic upgrade head      # применить все миграции
alembic downgrade -1      # откатить на 1 шаг
alembic history           # история миграций
alembic current           # текущая ревизия
alembic check             # проверить что модели в sync с миграциями
```

### Соглашение по именованию файлов миграций

```
YYYYMMDD_HHMMSS_revision_id_description.py
```

---

## 4. Celery (`src/tasks/`)

### 4.1 Приложение (`src/tasks/celery_app.py`)

```python
celery_app = Celery("rekharbor")

celery_app.config_from_object("src.tasks.celery_config")

# 3 очереди
CELERY_TASK_ROUTES = {
    "src.tasks.billing_tasks.*":       {"queue": "critical"},
    "src.tasks.mailing_tasks.*":       {"queue": "background"},
    "src.tasks.notification_tasks.*":  {"queue": "background"},
    "src.tasks.cleanup_tasks.*":       {"queue": "background"},
    "src.tasks.parser_tasks.*":        {"queue": "background"},
    "src.tasks.badge_tasks.*":         {"queue": "game"},
    "src.tasks.gamification_tasks.*":  {"queue": "game"},
    "src.tasks.rating_tasks.*":        {"queue": "game"},
}
```

### 4.2 Конфигурация Beat (`src/tasks/celery_config.py`)

```python
beat_schedule = {
    # Критические
    "expire-placements-every-5min": {
        "task": "src.tasks.billing_tasks.expire_pending_placements",
        "schedule": crontab(minute="*/5"),  # каждые 5 минут
        "options": {"queue": "critical"},
    },
    "unblock-users-every-hour": {
        "task": "src.tasks.billing_tasks.unblock_expired_users",
        "schedule": crontab(minute=0),  # каждый час
        "options": {"queue": "critical"},
    },

    # Фоновые
    "parse-channels-daily": {
        "task": "src.tasks.parser_tasks.parse_channels",
        "schedule": crontab(hour=3, minute=0),  # в 03:00
        "options": {"queue": "background"},
    },
    "send-scheduled-campaigns": {
        "task": "src.tasks.mailing_tasks.send_scheduled",
        "schedule": crontab(minute="*/10"),  # каждые 10 минут
        "options": {"queue": "background"},
    },
    "publish-scheduled-placements": {
        "task": "src.tasks.mailing_tasks.publish_scheduled_placements",
        "schedule": crontab(minute="*/5"),  # каждые 5 минут
        "options": {"queue": "background"},
    },
    "send-plan-expiry-notifications": {
        "task": "src.tasks.notification_tasks.notify_expiring_plans",
        "schedule": crontab(hour=10, minute=0),  # в 10:00
        "options": {"queue": "background"},
    },

    # Геймификация (низкий приоритет)
    "check-30days-recovery": {
        "task": "src.tasks.gamification_tasks.check_reputation_recovery",
        "schedule": crontab(hour=1, minute=0),  # в 01:00
        "options": {"queue": "game"},
    },
    "update-channel-ratings": {
        "task": "src.tasks.rating_tasks.update_all_ratings",
        "schedule": crontab(hour=4, minute=0),  # в 04:00
        "options": {"queue": "game"},
    },
    "cleanup-old-logs": {
        "task": "src.tasks.cleanup_tasks.cleanup_old_mailing_logs",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # по понедельникам в 02:00
        "options": {"queue": "background"},
    },
}
```

### 4.3 Задачи Celery по файлам

#### `src/tasks/billing_tasks.py` (очередь: critical)

```python
@celery_app.task
async def expire_pending_placements():
    """
    Находит PlacementRequest с expires_at < now() и статусом PENDING_OWNER/COUNTER_OFFER.
    Для каждой: placement_request_service.auto_expire(placement_id).
    """

@celery_app.task
async def unblock_expired_users():
    """
    Находит ReputationScore с is_owner_blocked=True и owner_blocked_until < now().
    Для каждого: reputation_service.check_and_unblock(user_id).
    Аналогично для advertiser_blocked.
    """

@celery_app.task
async def process_pending_payouts():
    """Обрабатывает Payout со статусом PENDING."""
```

#### `src/tasks/mailing_tasks.py` (очередь: background)

```python
@celery_app.task
async def send_scheduled():
    """Отправляет Campaign.status=SCHEDULED с scheduled_at <= now()."""

@celery_app.task
async def publish_scheduled_placements():
    """
    Находит PlacementRequest.status=ESCROW с final_schedule <= now().
    Для каждой: placement_request_service.process_publication_success() если успешно,
                placement_request_service.process_publication_failure() если нет.
    """

@celery_app.task
async def retry_failed_mailings():
    """Повторяет MailingLog.status=RETRY."""
```

#### `src/tasks/notification_tasks.py` (очередь: background)

```python
@celery_app.task
async def notify_expiring_plans():
    """
    Находит пользователей с plan_expires_at в течение 3 дней.
    Отправляет уведомление если plan_expiry_notified_at is None или > 24ч назад.
    """

@celery_app.task
async def notify_placement_payment_timeout():
    """
    Находит PlacementRequest.status=PENDING_PAYMENT с expires_at < now().
    Уведомляет владельца об отмене заявки по таймауту оплаты.
    """
```

#### `src/tasks/gamification_tasks.py` (очередь: game)

```python
@celery_app.task
async def check_reputation_recovery():
    """
    Находит пользователей у которых 30+ дней нет нарушений в ReputationHistory.
    Применяет RECOVERY_30DAYS (+5) через reputation_service.on_30days_clean().
    """

@celery_app.task
async def update_login_streaks():
    """Обнуляет login_streak у тех, кто не заходил вчера."""
```

#### `src/tasks/parser_tasks.py` (очередь: background)

```python
@celery_app.task
async def parse_channels():
    """
    Использует Telethon (read-only) для парсинга метрик каналов:
    member_count, avg_views, last_er.
    Обновляет TelegramChat.last_parsed_at.
    """

@celery_app.task
async def classify_unclassified_channels():
    """Вызывает LLM classifier для каналов без topic."""
```

#### `src/tasks/rating_tasks.py` (очередь: game)

```python
@celery_app.task
async def update_all_ratings():
    """
    Пересчитывает ChannelRating.overall_score на основе:
    - отзывов (Review)
    - fraud_score
    - надёжности владельца (ReputationScore.owner_score)
    """
```

### 4.4 Запуск Celery

```bash
# Worker для всех очередей
celery -A src.tasks.celery_app worker -Q critical,background,game -l info

# Отдельные worker'ы по очередям
celery -A src.tasks.celery_app worker -Q critical -l info -c 4
celery -A src.tasks.celery_app worker -Q background -l info -c 8
celery -A src.tasks.celery_app worker -Q game -l info -c 2

# Beat scheduler (только один экземпляр!)
celery -A src.tasks.celery_app beat -l info
```

---

## 5. FastAPI (`src/api/`)

### 5.1 Приложение (`src/api/main.py`)

```python
app = FastAPI(title="RekHarborBot API", version="3.0")

# CORS для Mini App
app.add_middleware(CORSMiddleware, allow_origins=["https://t.me"])

# Роутеры
app.include_router(auth_router, prefix="/auth")
app.include_router(analytics_router, prefix="/analytics")
app.include_router(campaigns_router, prefix="/campaigns")
app.include_router(channels_router, prefix="/channels")
app.include_router(billing_router, prefix="/billing")
```

### 5.2 Авторизация (`src/api/auth_utils.py`)

JWT авторизация через Telegram Login (initData). Токен в заголовке `Authorization: Bearer <token>`.

```python
async def verify_telegram_init_data(init_data: str) -> dict
    # Верифицировать HMAC подпись Telegram
    # Вернуть user_data

async def create_access_token(user_id: int) -> str
    # JWT с exp = now() + ACCESS_TOKEN_EXPIRE_MINUTES

async def get_current_user(token: str) -> User
    # Dependency для защищённых эндпоинтов
```

### 5.3 Эндпоинты (`src/api/routers/`)

#### auth.py
```
POST /auth/telegram        — Авторизация через Telegram initData → JWT токен
POST /auth/refresh         — Обновление токена
```

#### analytics.py
```
GET  /analytics/advertiser          — Статистика рекламодателя
GET  /analytics/owner               — Статистика владельца
GET  /analytics/campaigns/{id}      — Детали кампании
GET  /analytics/platform            — Публичная статистика платформы (без auth)
```

#### campaigns.py
```
GET  /campaigns/                    — Список кампаний текущего пользователя
POST /campaigns/                    — Создать кампанию
GET  /campaigns/{id}                — Детали кампании
PATCH /campaigns/{id}/status        — Изменить статус (pause/cancel/resume)
```

#### channels.py
```
GET  /channels/catalog              — Каталог каналов с фильтрами (без auth)
GET  /channels/{id}                 — Детали канала
GET  /channels/{id}/mediakit        — Медиакит канала
```

#### billing.py
```
GET  /billing/balance               — Текущий баланс
POST /billing/topup                 — Создать платёж на пополнение
GET  /billing/transactions          — История транзакций
POST /billing/cryptobot/webhook     — Вебхук от CryptoBot
```

#### Новые роутеры (Этап 6):
```
GET  /placements/                   — Список заявок пользователя
POST /placements/                   — Создать заявку
GET  /placements/{id}               — Детали заявки
PATCH /placements/{id}/accept       — Принять (owner)
PATCH /placements/{id}/reject       — Отклонить (owner)
PATCH /placements/{id}/counter      — Контр-предложение (owner)
PATCH /placements/{id}/pay          — Оплатить (advertiser)
PATCH /placements/{id}/cancel       — Отменить (advertiser)

GET  /channel-settings/{channel_id} — Настройки канала
PATCH /channel-settings/{channel_id} — Обновить настройки

GET  /reputation/                   — Репутация текущего пользователя
GET  /reputation/history            — История изменений репутации
```

---

## 6. Bot (`src/bot/main.py`)

### 6.1 Структура запуска

```python
async def main():
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=RedisStorage(redis_url=settings.REDIS_URL))

    # Middleware
    dp.update.middleware(ThrottlingMiddleware())
    dp.message.middleware(FSMTimeoutMiddleware())
    dp.callback_query.middleware(FSMTimeoutMiddleware())

    # Роутеры (порядок важен!)
    dp.include_router(admin_router)       # Первым — только для admin
    dp.include_router(start_router)       # /start и главное меню
    dp.include_router(cabinet_router)
    dp.include_router(analytics_router)
    dp.include_router(campaigns_router)
    dp.include_router(channel_owner_router)
    dp.include_router(b2b_router)
    dp.include_router(billing_router)
    dp.include_router(feedback_router)
    dp.include_router(help_router)
    dp.include_router(comparison_router)
    dp.include_router(channels_db_router)
    dp.include_router(notifications_router)
    # Новые (Этап 3):
    dp.include_router(placement_router)
    dp.include_router(arbitration_router)
    dp.include_router(channel_settings_router)

    await dp.start_polling(bot, skip_updates=True)
```

### 6.2 Паттерн обработки callback в handler'ах

```python
@router.callback_query(MainMenuCB.filter(F.action == "analytics"))
async def show_advertiser_analytics(
    callback: CallbackQuery,
    callback_data: MainMenuCB,
    session: AsyncSession,
):
    user_repo = UserRepo(session)
    analytics_service = AnalyticsService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    stats = await analytics_service.get_advertiser_stats(user.id)

    await callback.message.edit_text(
        text=format_advertiser_stats(stats),
        reply_markup=get_back_to_advertiser_menu_kb(),
    )
    await callback.answer()
```

---

## 7. Утилиты Telegram (`src/utils/telegram/`)

### sender.py
```python
async def send_post(bot: Bot, channel_id: int, text: str, parse_mode=ParseMode.HTML) -> int | None
    # Отправить пост через Bot API
    # Вернуть message_id или None при ошибке
```

### parser.py (Telethon — read-only)
```python
async def parse_channel_info(username: str) -> dict | None
    # Получить: title, member_count, description, avg_views через Telethon
    # НЕ использовать для публикации — только чтение

async def get_recent_posts(channel_id: int, limit: int = 10) -> list[dict]
    # Для анализа активности и ER
```

### channel_rules_checker.py
```python
async def check_bot_is_admin(bot: Bot, channel_id: int) -> bool
    # Проверить права бота в канале через getChatMember

async def verify_opt_in(channel_id: int) -> bool
    # Полная проверка: канал существует + бот-администратор
```

### llm_classifier.py
```python
async def classify_topic(channel_title: str, description: str) -> tuple[str, float]
    # Вернуть (topic, confidence)
    # topic из 11 категорий: IT, Бизнес, Финансы, Lifestyle, ...
```

---

## 8. Статический анализ

После каждого этапа запускать:

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

## 9. Переменные окружения (`.env` шаблон)

```env
# Bot
BOT_TOKEN=          # ⚠️ ТРЕБУЕТ РОТАЦИИ — текущий токен скомпрометирован
BOT_USERNAME=RekHarborBot

# Database
DATABASE_URL=postgresql+asyncpg://rekharbor:password@localhost:5432/rekharbor
DATABASE_SYNC_URL=postgresql://rekharbor:password@localhost:5432/rekharbor

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_FSM_DB=1

# AI
AI_MODEL=qwen/qwen3-235b-a22b:free
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Payments
CRYPTOBOT_TOKEN=
CRYPTOBOT_WEBHOOK_URL=https://yourdomain.com/billing/cryptobot/webhook
YUKASSA_SHOP_ID=
YUKASSA_SECRET_KEY=

# Telethon
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_NAME=parser

# Admin
ADMIN_TELEGRAM_IDS=[123456789]

# Security
API_SECRET_KEY=

# Platform defaults
PLATFORM_COMMISSION=0.20
MIN_PRICE_PER_POST=100
MIN_PAYOUT=100
MIN_TOPUP=100
PLACEMENT_TIMEOUT_HOURS=24
PAYMENT_TIMEOUT_HOURS=24
MAX_COUNTER_OFFERS=3
```

---

## 10. Docker Compose (рекомендуемая структура)

```yaml
version: "3.9"
services:
  bot:
    build: .
    command: python -m src.bot.main
    env_file: .env
    depends_on: [postgres, redis]

  api:
    build: .
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    env_file: .env
    depends_on: [postgres, redis]

  worker-critical:
    build: .
    command: celery -A src.tasks.celery_app worker -Q critical -l info -c 4
    env_file: .env

  worker-background:
    build: .
    command: celery -A src.tasks.celery_app worker -Q background -l info -c 8
    env_file: .env

  worker-game:
    build: .
    command: celery -A src.tasks.celery_app worker -Q game -l info -c 2
    env_file: .env

  beat:
    build: .
    command: celery -A src.tasks.celery_app beat -l info   # ТОЛЬКО ОДИН ЭКЗЕМПЛЯР
    env_file: .env

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: rekharbor
      POSTGRES_USER: rekharbor
      POSTGRES_PASSWORD: password
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

## 11. Контрольный список для нового разработчика

### Первый запуск

```bash
git clone <repo>
cd rekharbor-bot
cp .env.example .env
# Заполнить .env

pip install -r requirements.txt

alembic upgrade head        # применить все миграции
python -m src.db.seed_badges  # заполнить таблицу бейджей

# Запустить:
python -m src.bot.main      # бот
uvicorn src.api.main:app    # API
celery ... beat             # scheduler
celery ... worker           # worker
```

### Добавление нового handler'а

1. Создать `src/bot/handlers/feature.py` с Router
2. Создать `src/bot/keyboards/feature.py` с функциями `get_*_kb()`
3. Если нужны состояния — `src/bot/states/feature.py` с StatesGroup
4. Зарегистрировать роутер в `src/bot/main.py`
5. Запустить `ruff check` + `mypy`

### Добавление новой модели

1. Создать `src/db/models/model_name.py`
2. Добавить импорт в `src/db/models/__init__.py`
3. Создать миграцию: `alembic revision --autogenerate -m "description"`
4. Проверить: `alembic check`
5. Применить: `alembic upgrade head`
6. Создать `src/db/repositories/model_repo.py`
7. Добавить импорт в `src/db/repositories/__init__.py`
