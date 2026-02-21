# BELIN — Ведущий разработчик
## Market Telegram Bot — Пошаговое руководство по реализации

---

| Параметр | Значение |
|---|---|
| **Роль** | Ведущий разработчик (backend-core, инфраструктура, архитектура) |
| **Личная ветка** | `developer/belin` |
| **Рабочие ветки** | `feature/*` создаются от `developer/belin`, мержатся в `develop` |
| **Стек** | Python 3.13 · aiogram 3 · SQLAlchemy 2 · Celery · Redis · FastAPI · Docker |
| **Инструмент** | Qwen Code (промпты к каждому шагу) |
| **Всего шагов** | 18 шагов, 5 спринтов, 10 недель |

### Правило ветвления для каждого шага

```bash
git checkout develop && git pull origin develop
git checkout developer/belin && git merge develop
git checkout -b feature/название-шага
# ... работаешь, коммитишь ...
git push origin feature/название-шага
# Открываешь PR в develop → tsaguria делает review → Squash Merge
```

### Конвенция коммитов

```
feat(db): add UserRepository with atomic balance update
feat(parser): implement Telethon chat search with topic classification
fix(mailing): handle FloodWait with exponential backoff
test(filter): add 50 unit tests for content filter categories
```

---

## 🚀 SPRINT 0 — НАСТРОЙКА ИНФРАСТРУКТУРЫ

---

### Шаг 1 — Клонирование репозитория и инициализация окружения
> 🌿 **Ветка:** `developer/belin`

Это первое, что делаешь — настраиваешь локальное окружение и Docker-инфраструктуру для всего проекта.

```bash
git clone https://github.com/your-org/market-telegram-bot.git
cd market-telegram-bot
git checkout developer/belin
pyenv install 3.13.7 && pyenv local 3.13.7
pip install poetry && poetry install
cp .env.example .env  # заполнить BOT_TOKEN, DATABASE_URL, REDIS_URL
```

✅ **ЧЕКПОИНТ** — Python 3.13 установлен, `poetry install` прошёл без ошибок, `.env` заполнен

---

### Шаг 2 — Docker Compose — полная инфраструктура
> 🌿 **Ветка:** `developer/belin` → `feature/docker-infra`

Создаёшь `docker-compose.yml` и все Dockerfile-ы. tsaguria будет поднимать инфраструктуру этой командой.

1. Создать `docker-compose.yml` с сервисами: `postgres:16`, `redis:7-alpine`, `bot`, `worker`, `api`, `flower`, `nginx`
2. Создать `docker/Dockerfile.bot`: `python:3.13-slim`, multi-stage, `poetry install --no-dev`
3. Создать `docker/Dockerfile.worker`: аналогично bot, `entrypoint = celery worker`
4. Создать `docker/Dockerfile.api`: `entrypoint = uvicorn src.api.main:app`
5. Создать `docker/nginx.conf`: upstream bot, api, static mini_app
6. Добавить healthcheck для postgres и redis контейнеров
7. Проверить: `docker compose up -d && docker compose ps` — все контейнеры healthy

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай docker-compose.yml для проекта market-telegram-bot со следующими сервисами:
> PostgreSQL 16, Redis 7, bot (aiogram), celery worker, FastAPI, Flower (мониторинг Celery),
> Nginx. Добавь healthcheck для postgres и redis. Также создай multi-stage Dockerfile.bot
> для Python 3.13 с Poetry.
> ```

✅ **ЧЕКПОИНТ** — `docker compose up -d` поднимает все контейнеры, flower доступен на `:5555`

---

### Шаг 3 — CI/CD — GitHub Actions
> 🌿 **Ветка:** `developer/belin` → `feature/ci-cd`

Настраиваешь автоматическую проверку кода и деплой. Это нужно до первого PR.

1. Создать `.github/workflows/ci.yml`: триггер на PR в `develop`
2. Jobs в CI: `ruff check`, `ruff format --check`, `mypy src/`, `pytest tests/ --tb=short`
3. Создать `.github/workflows/deploy.yml`: триггер на push в `main`
4. Deploy job: SSH на timeweb.cloud → `git pull` → `docker compose -f docker-compose.prod.yml up -d --no-deps`
5. Добавить secrets в GitHub: `SSH_HOST`, `SSH_USER`, `SSH_KEY`, `SSH_PORT`
6. Создать `.github/PULL_REQUEST_TEMPLATE.md`: описание, тесты, скриншоты, Issues
7. Создать `.pre-commit-config.yaml`: ruff, mypy, detect-secrets, end-of-file-fixer
8. Создать `Makefile`: `make run`, `make test`, `make lint`, `make migrate`, `make shell`

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай .github/workflows/ci.yml для Python 3.13 проекта с Poetry. Шаги: установка
> зависимостей, ruff check, ruff format --check, mypy src/, pytest tests/. Также создай
> Makefile с командами run, test, lint, migrate.
> ```

✅ **ЧЕКПОИНТ** — CI проходит на пустом проекте, pre-commit хуки установлены (`pre-commit install`)

---

### Шаг 4 — Модели SQLAlchemy и первая миграция
> 🌿 **Ветка:** `developer/belin` → `feature/db-models`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Docker Compose запущен (Шаг 2 завершён)
> - ✓ PostgreSQL контейнер healthy
> - ✓ `DATABASE_URL` прописан в `.env`

1. Создать `src/config/settings.py`: Pydantic `BaseSettings`, читает из `.env`
2. Создать `src/db/session.py`: `async_engine`, `async_sessionmaker`, `get_session` dependency
3. Создать `src/db/base.py`: `DeclarativeBase`, `TimestampMixin` (created_at, updated_at)
4. Создать `src/db/models/user.py`: `User` — `telegram_id` BigInt PK, `username`, `balance` Numeric, `plan` Enum, `referral_code`, `is_banned`
5. Создать `src/db/models/campaign.py`: `Campaign` — `id`, `user_id` FK, `title`, `text`, `status` Enum (draft/queued/running/done/error), `filters_json` JSONB, `scheduled_at`
6. Создать `src/db/models/chat.py`: `Chat` — `telegram_id` BigInt UNIQUE, `title`, `username`, `member_count`, `topic`, `is_active`, `rating` Float, `last_checked`
7. Создать `src/db/models/mailing_log.py`: `MailingLog` — `campaign_id` FK, `chat_id` FK, `status` Enum, `error_msg`, `sent_at`
8. Создать `src/db/models/transaction.py`: `Transaction` — `user_id` FK, `amount` Numeric, `type` Enum (topup/spend), `payment_id`, `meta_json`
9. Создать `src/db/models/content_flag.py`: `ContentFlag` — `campaign_id` FK, `categories` ARRAY, `flagged_fragments` JSONB, `decision` Enum, `reviewed_by`
10. `alembic init src/db/migrations` && настроить `env.py` на async engine
11. `alembic revision --autogenerate -m "initial_models"`
12. `alembic upgrade head` — применить миграцию
13. Написать тест: `test_db_models.py` — создать запись каждой модели, убедиться что FK работают

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай SQLAlchemy 2.0 async модели для Telegram рекламного бота. Модели:
> User (telegram_id BigInteger PK, username, balance Numeric(12,2), plan Enum[free/starter/pro/business],
> referral_code, is_banned bool), Campaign (id, user_id FK→User, title, text,
> status Enum[draft/queued/running/done/error], filters_json JSONB, scheduled_at),
> Chat (telegram_id BigInt UNIQUE, title, username, member_count, topic, is_active, rating Float,
> last_checked timestamp), MailingLog (campaign_id FK, chat_id FK,
> status Enum[sent/failed/skipped], error_msg, sent_at),
> Transaction (user_id FK, amount Numeric, type Enum[topup/spend], payment_id str, meta_json JSONB).
> Используй DeclarativeBase, TimestampMixin, asyncpg драйвер.
> ```

✅ **ЧЕКПОИНТ** — `alembic upgrade head` прошёл без ошибок, тест `test_db_models.py` зелёный

---

### Шаг 5 — Merge Sprint 0 в develop
> 🌿 **Ветка:** `feature/*` → `develop`

1. `git checkout develop && git pull origin develop`
2. Создать PR каждой feature-ветки в `develop`
3. Убедиться что CI зелёный
4. После самопроверки — merge (squash and merge)
5. Уведомить tsaguria: инфраструктура готова, можно поднимать `docker compose up -d`

✅ **ЧЕКПОИНТ** — Все Sprint 0 ветки смержены в `develop`, tsaguria поднял инфраструктуру успешно

---

## ⚙️ SPRINT 1 — РЕПОЗИТОРИИ БД, ПАРСЕР ЧАТОВ, ФИЛЬТР КОНТЕНТА

---

### Шаг 6 — Слой репозиториев — паттерн Repository
> 🌿 **Ветка:** `feature/db-repositories`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 0 полностью завершён и смержен в `develop`
> - ✓ Все модели SQLAlchemy созданы (Шаг 4)
> - ✓ `alembic upgrade head` прошёл

1. Создать `src/db/repositories/base.py`: `Generic[T] BaseRepository` — методы `get(id)`, `get_all()`, `create(obj)`, `update(id, **kwargs)`, `delete(id)`, `paginate(page, size)`
2. Создать `src/db/repositories/user_repo.py`:
   - `get_by_telegram_id(telegram_id) → User | None`
   - `create_or_update(telegram_id, **data) → User`
   - `update_balance(user_id, delta: Decimal)` — атомарный UPDATE с RETURNING
   - `get_with_stats(user_id) → UserWithStats` (джойн с Campaign)
3. Создать `src/db/repositories/campaign_repo.py`:
   - `create(user_id, data) → Campaign`
   - `get_by_user(user_id, status=None, page=1) → List[Campaign]`
   - `update_status(campaign_id, status, error_msg=None)`
   - `get_scheduled_due() → List[Campaign]` — где `scheduled_at <= now()` и `status=queued`
4. Создать `src/db/repositories/chat_repo.py`:
   - `upsert_batch(chats: List[ChatData]) → int`
   - `get_active_filtered(topics, min_members, max_members, exclude_ids) → List[Chat]`
   - `update_rating(chat_id, new_rating)`
5. Создать `src/db/repositories/log_repo.py`:
   - `bulk_insert(logs: List[LogData]) → None`
   - `get_stats_by_campaign(campaign_id) → CampaignStats`
6. Написать интеграционные тесты с testcontainers (реальная PostgreSQL в Docker):
   - `test_user_repo.py` — создание, `get_by_telegram_id`, `update_balance` (атомарность)
   - `test_campaign_repo.py` — CRUD, пагинация, `get_scheduled_due`
   - `test_chat_repo.py` — `upsert_batch` с дублями, фильтрация

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай Generic BaseRepository[T] для SQLAlchemy 2.0 async с методами: get(id), get_all(),
> create(obj), update(id, **kwargs), delete(id), paginate(page, size). Затем создай
> UserRepository с методами get_by_telegram_id, create_or_update, update_balance
> (атомарный UPDATE balance = balance + delta с RETURNING).
> Используй asyncpg, тесты через pytest-asyncio + testcontainers.
> ```

✅ **ЧЕКПОИНТ** — `pytest tests/integration/test_*_repo.py` — все тесты зелёные

---

### Шаг 7 — Парсер открытых Telegram-чатов
> 🌿 **Ветка:** `feature/chat-parser`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 6 завершён (репозитории готовы)
> - ✓ `chat_repo.upsert_batch()` работает
> - ✓ Telethon установлен (добавить в `pyproject.toml`)
> - ✓ Получен `API_ID` и `API_HASH` от my.telegram.org

Парсер использует Telethon (user-account API) для поиска открытых чатов. Дополнительно — HTTP-парсинг tgstat.ru как источника готовых каталогов.

1. Создать `src/utils/telegram/parser.py`:
   - `class TelegramParser`: инициализация Telethon `TelegramClient`
   - `search_public_chats(query: str, limit=50) → List[ChatInfo]`
     - `client.get_entity(username)`, проверка типа (Channel)
     - `client(GetFullChannelRequest)`: `linked_chat_id`, можно ли писать
   - `resolve_and_validate(username: str) → ChatDetails | None`
     - проверка: `channel.username` не None, `not channel.restricted`
     - `full_channel.can_view_participants` or members > 100
   - `batch_validate(usernames: List[str]) → List[ChatDetails]`
2. Создать `src/utils/telegram/tgstat_parser.py`:
   - `async def fetch_tgstat_catalog(topic: str) → List[str]` — список @username
   - `httpx.AsyncClient` + `BeautifulSoup` для парсинга страниц каталога
   - Уважать robots.txt, задержка 2-3 сек между запросами
3. Создать `src/utils/telegram/topic_classifier.py`:
   - `classify_topic(title: str, description: str) → str`
   - Использовать `rapidfuzz` для matching по словарю тематик
   - Словарь тематик: бизнес, IT, новости, мода, авто, спорт, крипта, маркетинг, другое
4. Создать `src/tasks/parser_tasks.py`: `@app.task refresh_chat_database()`
   - Запускать 24 популярных поисковых запроса параллельно через `asyncio.gather`
   - Сохранить результат через `chat_repo.upsert_batch()`
5. Написать тест: `test_parser.py` — мок TelegramClient, проверить фильтрацию

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай TelegramParser класс с Telethon. Методы: search_public_chats(query, limit) —
> ищет каналы, проверяет что канал публичный (username не None, not restricted, members >= 100).
> resolve_and_validate(username) — полная проверка через GetFullChannelRequest.
> Также создай Celery задачу refresh_chat_database() с Celery Beat расписанием раз в сутки.
> ```

✅ **ЧЕКПОИНТ** — Парсер находит 100+ чатов по тестовым запросам, `upsert_batch` сохраняет без дублей

---

### Шаг 8 — Фильтр контента — 3 уровня проверки
> 🌿 **Ветка:** `feature/content-filter`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 6 завершён (репозитории готовы)
> - ✓ ContentFlag модель и репозиторий готовы
> - ✓ `pymorphy3` установлен в `pyproject.toml`

1. Создать `src/utils/content_filter/stopwords_ru.json` — 8 категорий:
   - `drugs`: [нарко, героин, амфет, закладка, …]
   - `terrorism`: [джихад, взрыв, теракт, …]
   - `weapons`: [автомат, оружие, ствол купить, …]
   - `adult`: [порно, эротика, 18+, …]
   - `fraud`: [лохотрон, пирамида, обнал, …]
   - `suicide`: [суицид, самоубийство, как покончить, …]
   - `extremism`: [нацист, экстремизм, …]
   - `gambling`: [казино, ставки, букмекер, …]
2. Создать `src/utils/content_filter/filter.py`:
   - `FilterResult` dataclass: `passed: bool`, `score: float`, `categories: List[str]`, `flagged_fragments: List[str]`
   - `class ContentFilter`:
     - **Уровень 1** — `regex_check(text)`: скомпилированные re паттерны (< 1 мс)
     - **Уровень 2** — `morph_check(text)`: pymorphy3, нормализация словоформ (чтобы "наркотики", "наркотика", "наркотиков" — все ловились)
     - **Уровень 3** — `llm_check(text)`: Claude API с системным промптом модератора (вызывается только если score L1+L2 > 0.3)
     - `check(text) → FilterResult`: последовательно L1 → L2 → (L3 если нужно)
3. Создать `src/core/services/moderation_service.py`:
   - `submit_for_review(campaign_id, result)` → сохранить ContentFlag, уведомить admin
4. Написать 100+ тестов `tests/unit/test_content_filter.py`:
   - Каждая категория: 5+ позитивных кейсов (должны блокироваться)
   - 10+ негативных кейсов (легитимный текст не должен блокироваться)
   - Тест словоформ: "наркотиках", "наркотикам" — все находятся

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай ContentFilter класс с 3 уровнями проверки. Уровень 1: regex по стоп-словам из JSON.
> Уровень 2: pymorphy3 нормализация и проверка нормальных форм. Уровень 3: Claude API с
> промптом "Ты модератор. Определи содержит ли текст запрещённый контент по законодательству РФ".
> FilterResult: passed, score 0-1, categories list, flagged_fragments list. Напиши 20 unit тестов.
> ```

✅ **ЧЕКПОИНТ** — 100+ тестов зелёные, precision > 95%, false-positive < 2%

---

## 📬 SPRINT 2 — CELERY, РАССЫЛКА, ПЛАНИРОВЩИК

---

### Шаг 9 — Celery — инициализация и конфигурация
> 🌿 **Ветка:** `feature/celery-setup`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 1 полностью смержен в `develop`
> - ✓ Redis контейнер запущен и healthy
> - ✓ Все репозитории БД готовы (Шаг 6)

1. Создать `src/tasks/celery_app.py`:
   - `app = Celery("market_bot", broker=settings.REDIS_URL, backend=settings.REDIS_URL)`
   - Конфиг: `task_serializer=json`, `result_expires=3600`, `worker_concurrency=4`
   - `task_routes`: `mailing.*` → `queue="mailing"`, `parser.*` → `queue="parser"`
   - `task_acks_late=True`, `task_reject_on_worker_lost=True` — надёжность
2. Создать `src/tasks/celery_config.py` — beat_schedule:
   - `refresh-chats`: `parser_tasks.refresh_chat_database` — каждые 24 часа
   - `check-scheduled`: `mailing_tasks.check_scheduled_campaigns` — каждые 5 минут
   - `cleanup-logs`: `cleanup_tasks.delete_old_logs` — каждое воскресенье в 3:00
3. Проверить запуск: `celery -A src.tasks.celery_app worker --loglevel=info`
4. Проверить beat: `celery -A src.tasks.celery_app beat --loglevel=info`

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай конфигурацию Celery 5 с Redis broker для Python 3.13. Настрой: task_routes
> (mailing и parser в отдельные очереди), task_acks_late=True,
> task_reject_on_worker_lost=True. Celery Beat расписание: обновление БД чатов раз в сутки,
> проверка запланированных кампаний каждые 5 минут, очистка старых логов каждое воскресенье.
> ```

✅ **ЧЕКПОИНТ** — celery worker стартует без ошибок, flower показывает воркер online

---

### Шаг 10 — Сервис рассылки — mailing_service + sender
> 🌿 **Ветка:** `feature/mailing-service`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 9 завершён (Celery работает)
> - ✓ `chat_repo.get_active_filtered()` готов
> - ✓ `log_repo.bulk_insert()` готов
> - ✓ Bot instance доступен через singleton

1. Создать `src/utils/telegram/sender.py`:
   - `async send_message(bot, chat_id, text, parse_mode=HTML) → SendResult`
   - Обработка ошибок Telegram:
     - `FloodWait(e)`: `asyncio.sleep(e.value + 5)`, затем retry
     - `ChatNotFound / ChannelInvalid`: статус=skipped, деактивировать чат в БД
     - `Forbidden / UserBannedInChannel`: статус=failed, записать в лог
     - `MigratedToChat(e)`: обновить `telegram_id` в БД, retry с новым id
   - Экспоненциальный retry: 3 попытки, задержки 1s / 4s / 9s
2. Создать `src/core/services/mailing_service.py`:
   - `select_chats(campaign) → List[Chat]`
   - `apply_blacklist(chats, user_id) → List[Chat]`
   - `check_rate_limit(chat_id) → bool`: Redis ZSET sliding window (1 msg/chat/24h)
   - `run_campaign(campaign_id) → CampaignResult`:
     - загрузить кампанию и чаты
     - разбить на батчи по 20 чатов (`asyncio.gather`)
     - для каждого чата: rate_limit → content_filter → send → log
     - `bulk_insert` логов каждые 20 отправок
     - обновить статус кампании по завершении
3. Создать `src/tasks/mailing_tasks.py`:
   - `@app.task(bind=True, max_retries=3) send_campaign(self, campaign_id)`
   - `@app.task check_scheduled_campaigns()`
4. Написать тест: `test_mailing_service.py` — мок sender, проверить логику батчей и rate limit

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай async mailing_service для Telegram бота. Функция run_campaign(campaign_id):
> 1) загрузить Campaign из БД, 2) получить подходящие чаты через фильтры,
> 3) проверить rate limit через Redis ZSET (1 сообщение в чат за 24 часа),
> 4) отправить через aiogram Bot с обработкой FloodWait (asyncio.sleep),
> ChatNotFound (пометить чат неактивным), Forbidden.
> 5) записать результат в MailingLog. Батчи по 20, asyncio.gather параллельно.
> ```

✅ **ЧЕКПОИНТ** — тестовая рассылка в 5 чатов проходит, FloodWait обрабатывается, логи пишутся

---

### Шаг 11 — Уведомления пользователя и cleanup задачи
> 🌿 **Ветка:** `feature/notifications-cleanup`

1. Создать `src/core/services/notification_service.py`:
   - `notify_campaign_started(user_id, campaign)`
   - `notify_campaign_done(user_id, stats: CampaignStats)`
   - `notify_campaign_error(user_id, campaign, error_msg)`
   - `notify_low_balance(user_id, balance)` — при балансе < 50₽
2. Создать `src/tasks/cleanup_tasks.py`:
   - `@app.task delete_old_logs()` — DELETE mailing_log WHERE sent_at < now()-90days
   - `@app.task archive_to_s3(date)` — опционально: дамп в Object Storage

✅ **ЧЕКПОИНТ** — после тестовой кампании пользователь получает уведомление с итогами

---

## 🤖 SPRINT 3 — ИИ-ГЕНЕРАЦИЯ И АНАЛИТИКА

---

### Шаг 12 — ИИ-сервис — Claude API, A/B, кэширование
> 🌿 **Ветка:** `feature/ai-service`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 2 смержен в `develop`
> - ✓ `billing_service.deduct_balance()` реализован tsaguria (Sprint 2)
> - ✓ `ANTHROPIC_API_KEY` прописан в `.env`
> - ✓ Redis доступен для кэширования

1. Создать `src/core/services/ai_service.py`:
   - `_get_cache_key(prompt_hash)`: `"ai_cache:{md5(prompt)}"`
   - `_check_cache(key) → str | None`: GET из Redis, TTL=3600
   - `_call_claude(system, user_msg, max_tokens=1000) → str`:
     - `anthropic.AsyncAnthropic().messages.create(...)`
     - retry 3 раза при APIError, timeout 30s
     - fallback на OpenAI GPT-4o при `anthropic.RateLimitError`
   - `generate_ad_text(description, tone, length, audience) → str`
     - Списание баланса ПЕРЕД вызовом API (атомарно: check → deduct → call)
   - `generate_ab_variants(description, count=3) → List[str]`
     - Один вызов API, парсинг ответа по разделителю `---`
   - `improve_text(original, improvement_type) → str`
     - improvement_type: `shorter / more_engaging / formal / casual`
   - `generate_hashtags(text) → List[str]` — 5-10 хэштегов
2. Написать тест: `test_ai_service.py` — мок anthropic client, проверить кэш, списание баланса

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай async AIService для Anthropic Claude API. Методы:
> generate_ad_text(description, tone="нейтральный", length="средний", audience="широкая аудитория")
> — промпт + кэш в Redis TTL=1h по MD5 промпта.
> generate_ab_variants(description, count=3) — один вызов API, парсинг по "---" разделителю.
> improve_text(text, mode) где mode=[shorter/engaging/formal/casual].
> Fallback на OpenAI при RateLimitError. Атомарное списание баланса перед вызовом.
> ```

✅ **ЧЕКПОИНТ** — генерация работает, кэш сохраняет повторные запросы, баланс списывается

---

### Шаг 13 — Сервис аналитики и PDF-отчёты
> 🌿 **Ветка:** `feature/analytics-service`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Шаг 10 завершён (логи рассылок пишутся)
> - ✓ `log_repo.get_stats_by_campaign()` готов
> - ✓ `reportlab` установлен в `pyproject.toml`

1. Создать `src/core/services/analytics_service.py`:
   - `CampaignStats` dataclass: `total_sent`, `total_failed`, `total_skipped`, `success_rate`, `reach_estimate`
   - `get_campaign_stats(campaign_id) → CampaignStats` — кэш Redis TTL=300
   - `get_user_summary(user_id, days=30) → UserAnalytics`
   - `get_top_performing_chats(user_id, limit=10) → List[ChatPerformance]`
   - `compare_campaigns(ids: List[int]) → ComparisonReport`
2. Создать `src/utils/pdf_report.py`:
   - `generate_campaign_report(stats, campaign) → bytes` (PDF через reportlab)
   - Содержимое: заголовок, таблица отправок, pie chart, дата

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай AnalyticsService: get_campaign_stats(campaign_id) — агрегация из mailing_log
> (sent/failed/skipped counts, success_rate), кэш Redis TTL=5min.
> get_user_summary(user_id, days=30) — сводка по всем кампаниям.
> Также pdf_report.py с reportlab: таблица статистики + круговая диаграмма.
> Возвращать bytes для отправки через aiogram send_document.
> ```

✅ **ЧЕКПОИНТ** — PDF генерируется за < 2 сек, цифры сходятся с логами

---

## 🏗️ SPRINT 4 — FASTAPI, DEVOPS, PRODUCTION

---

### Шаг 14 — FastAPI — backend для Mini App
> 🌿 **Ветка:** `feature/fastapi-backend`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 3 смержен в `develop`
> - ✓ `analytics_service` готов
> - ✓ `billing_service` готов (tsaguria)
> - ✓ `campaign_repo.paginate()` готов

1. Создать `src/api/main.py`: FastAPI app, lifespan (пул БД), CORS для Mini App
2. Создать `src/api/dependencies.py`:
   - `get_db()` — yield async session
   - `get_current_user(x_init_data: Header) → User`: валидация Telegram `initData` через HMAC-SHA256, кэш Redis TTL=600
3. Создать `src/api/routers/auth.py`: POST `/auth/login` → JWT access + refresh tokens
4. Создать `src/api/routers/campaigns.py`: GET/POST/DELETE `/campaigns`
5. Создать `src/api/routers/analytics.py`: GET `/analytics/summary`, `/analytics/campaign/{id}`, `/analytics/top-chats`
6. Создать `src/api/routers/billing.py`: GET `/billing/balance`, `/billing/history`
7. Написать тест: `test_api.py` — TestClient, мок `get_current_user`

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай FastAPI приложение с JWT авторизацией через Telegram initData (HMAC-SHA256 валидация).
> Роутеры: /campaigns (CRUD), /analytics (summary, campaign stats, top chats),
> /billing (balance, history). Pydantic v2 схемы. CORS для Mini App.
> Тесты через httpx AsyncClient.
> ```

✅ **ЧЕКПОИНТ** — GET /campaigns возвращает 200, JWT валидация работает

---

### Шаг 15 — Production DevOps — Nginx, SSL, мониторинг
> 🌿 **Ветка:** `feature/devops-production`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Аккаунт timeweb.cloud, VPS Ubuntu 22.04 2vCPU/4GB запущен
> - ✓ Домен куплен, A-запись указывает на IP VPS
> - ✓ GitHub Secrets: `SSH_HOST`, `SSH_USER`, `SSH_KEY`, `SSH_PORT` добавлены

1. Создать `docker/nginx.conf`: upstream bot/api, proxy_pass, gzip, SSL
2. Создать `docker-compose.prod.yml`: `restart: unless-stopped`, volumes, resource limits
3. Настроить SSL: `certbot --nginx -d yourdomain.com`
4. Создать `src/utils/metrics.py`: prometheus_client счётчики (`campaigns_sent_total`, `mailing_errors_total`, `queue_size`, `api_request_duration_seconds`)
5. Создать `docker/grafana/dashboard.json`: дашборд с 6 панелями
6. Интегрировать Sentry: `sentry_sdk.init()` в bot, api, celery_app
7. Создать `.github/workflows/deploy.yml`: SSH → git pull → docker compose up --no-deps
8. Настроить pg_dump cron: каждые 6 часов, хранить 7 дней
9. Написать `DEPLOY.md` и `ARCHITECTURE.md`

> 🤖 **Промпт для Qwen Code:**
> ```
> Создай docker-compose.prod.yml для production: Nginx с SSL (certbot), PostgreSQL с volume,
> Redis, bot и Celery worker с resource limits (memory). GitHub Actions deploy.yml:
> SSH подключение, git pull, docker compose up --no-deps для zero-downtime деплоя.
> ```

✅ **ЧЕКПОИНТ** — деплой на timeweb прошёл, бот отвечает через HTTPS webhook, Grafana работает

---

### Шаг 16 — Нагрузочное тестирование
> 🌿 **Ветка:** `feature/load-testing`

1. `pip install locust`
2. Создать `tests/load/locustfile.py`: сценарии /api/campaigns, /api/analytics
3. `locust -f tests/load/locustfile.py --users 100 --spawn-rate 10`
4. Целевые метрики: p95 latency < 500мс, error rate < 1% при 100 RPS
5. По результатам: EXPLAIN ANALYZE медленных запросов, добавить индексы
6. Проверить graceful shutdown: `kill -SIGTERM` → worker завершает текущую задачу

✅ **ЧЕКПОИНТ** — 100 RPS, p95 < 500мс, error rate < 1%

---

## 🏁 SPRINT 5 — ФИНАЛ И ЗАПУСК

---

### Шаг 17 — Production-аудит безопасности
> 🌿 **Ветка:** `feature/security-audit`

> ⚠️ **ПЕРЕД НАЧАЛОМ:**
> - ✓ Sprint 4 смержен в `develop` и задеплоен на timeweb
> - ✓ tsaguria завершил Mini App (Sprint 4)

1. Проверить все API: нет публичного доступа без JWT
2. Проверить HMAC-валидацию: поддельный hash → 401
3. Проверить rate limiting: > 100 req/min → 429
4. Проверить content_filter: 20 тестовых запрещённых текстов → все блокируются
5. Проверить что .env не попал в git: `git log --all -- .env`
6. Проверить backup: восстановить БД из последнего дампа в тестовом контейнере
7. Code review всего кода tsaguria

✅ **ЧЕКПОИНТ** — все уязвимости закрыты, backup восстанавливается успешно

---

### Шаг 18 — Merge develop → main и production release
> 🌿 **Ветка:** `develop` → `main`

1. `git checkout main && git pull origin main`
2. `git merge develop` (или через PR в GitHub)
3. GitHub Actions deploy.yml запускается автоматически
4. Проверить все контейнеры: `docker compose -f docker-compose.prod.yml ps`
5. Установить Webhook: `POST https://api.telegram.org/bot{TOKEN}/setWebhook`
6. Провести финальное сквозное тестирование совместно с tsaguria
7. Написать `CHANGELOG.md` для версии 1.0.0

✅ **ЧЕКПОИНТ** — 🚀 Бот в production! Webhook установлен, пользователи могут регистрироваться

---

> **ТВОЯ РАБОТА — ФУНДАМЕНТ ВСЕГО ПРОЕКТА. УДАЧИ, belin! 🚀**
