# Docker Infrastructure — Инструкция по развертыванию

## Быстрый старт

### 1. Исправить .env

Файл `.env` должен содержать правильные URL для Docker-сети:

```env
DATABASE_URL=postgresql+asyncpg://market_bot:market_bot_pass@postgres:5432/market_bot_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

⚠️ **Важно:** Используйте `postgres` и `redis` (имена сервисов), а не `localhost`!

### 2. Очистить окружение (если нужно)

```bash
docker compose down --volumes --remove-orphans
```

### 3. Собрать образы

```bash
docker compose build
```

### 4. Запустить инфраструктуру

```bash
# Запустить PostgreSQL и Redis
docker compose up -d postgres redis

# Дождаться пока сервисы станут healthy (15-30 секунд)
docker compose ps postgres redis
```

### 5. Применить миграции

```bash
# Создать первую миграцию
docker compose run --rm bot poetry run alembic -c src/db/migrations/env_sync.py revision --autogenerate -m "initial schema"

# Применить миграции
docker compose run --rm bot poetry run alembic upgrade head
```

### 6. Проверить таблицы

```bash
docker compose exec postgres psql -U market_bot -d market_bot_db -c "\dt"
```

### 7. Запустить все сервисы

```bash
docker compose up -d
```

### 8. Проверить доступность

```bash
# API health check (via docker exec — port not exposed to host)
docker exec market_bot_api curl -sf http://localhost:8001/health

# Nginx health check (through reverse proxy)
curl http://localhost/health

# API through nginx proxy
curl http://localhost/api/health  # if endpoint exists

# Flower UI
open http://localhost:5555
```

---

## Структура Docker-образов

```
docker/
├── Dockerfile.api      # FastAPI backend (production, --only main)
├── Dockerfile.bot      # aiogram bot (production, --only main)
└── Dockerfile.worker   # Celery worker (production, --only main)
```

Все Dockerfile используют multi-stage сборку:
1. **builder** — установка Poetry и зависимостей
2. **final** — минимальный образ с готовыми пакетами

---

## Конфигурация nginx

nginx использует каноническую структуру:

```
nginx/
├── nginx.conf          # Только events + http + include
└── conf.d/
    └── default.conf    # Upstreams и server блоки
```

**Upstreams:**
- `api_backend` → `api:8001`
- `flower_backend` → `flower:5555`

**Location blocks:**
- `/app/` — Mini App статика
- `/api/` — FastAPI API
- `/flower/` — Flower мониторинг
- `/health` — Health check

---

## Redis Architecture

All services share a single Redis instance on `redis:6379`, using different DB indices for isolation:

| Service Group | Redis URL | Purpose |
|--------------|-----------|---------|
| Main app (api, bot, workers, beat) | `redis://redis:6379/0` | Celery broker, caching, sessions |
| Main app (Celery results) | `redis://redis:6379/1` | Celery result backend |
| GlitchTip (monitoring) | `valkey://redis:6379/2` | Django vtasks queue, async features |

**Reason:** Separating GlitchTip into DB `/2` prevents `ReadOnly: You can't write against a read only replica` errors caused by Redis connection conflicts with the main application.

---

## Healthchecks

| Сервис | Healthcheck |
|---|---|
| postgres | `pg_isready -U market_bot -d market_bot_db` |
| redis | `redis-cli ping` |
| worker | `celery inspect ping` |

---

## Переменные окружения

Все переменные берутся из `.env` файла:

| Переменная | Значение по умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | Telegram Bot token |
| `DATABASE_URL` | — | PostgreSQL URL (используйте `postgres` как хост) |
| `REDIS_URL` | — | Redis URL (используйте `redis` как хост) |
| `CELERY_BROKER_URL` | — | Celery broker URL |
| `CELERY_RESULT_BACKEND` | — | Celery result backend |
| `API_ID` | — | Telegram API ID |
| `API_HASH` | — | Telegram API Hash |
| `ANTHROPIC_API_KEY` | — | Claude API key |
| `OPENAI_API_KEY` | — | OpenAI API key (fallback) |

---

## Интеграционное тестирование

### Создать тестовую БД

```bash
docker compose exec postgres psql -U market_bot -c "CREATE DATABASE market_bot_test_db;"
```

### Запустить тесты

```bash
# Локально (требуется poetry install)
poetry run pytest tests/ -v --tb=short --cov=src

# В Docker контейнере
docker compose run --rm bot poetry run pytest tests/ -v --tb=short
```

---

## Отладка

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f worker
```

### Зайти в контейнер

```bash
# Bot контейнер
docker compose exec bot bash

# PostgreSQL
docker compose exec postgres psql -U market_bot -d market_bot_db

# Redis
docker compose exec redis redis-cli
```

### Перезапустить сервис

```bash
docker compose restart api
docker compose up -d --build api  # Пересобрать и перезапустить
cd /opt/market-telegram-bot && docker compose build --no-cache nginx && docker compose up -d --force-recreate nginx  # Пересобрать nginx чтобы применились изменения по фронтенду и mini app
```

---

## Production заметки

1. **Не используйте `.env` в production** — передавайте переменные через secrets
2. **Измените пароли** по умолчанию в docker-compose.yml
3. **Настройте SSL** в nginx для production
4. **Используйте external volumes** для персистентности данных
5. **Настройте мониторинг** через Flower и Prometheus
