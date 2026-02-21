---
name: docker-compose
description: >
  Creates and edits Docker Compose configurations, Dockerfiles, and Nginx
  configs for this project. Use when adding new services, modifying container
  resources, configuring Nginx routing, or updating production docker-compose.prod.yml.
  Enforces: multi-stage Python builds with Poetry, healthchecks for postgres and redis,
  restart: unless-stopped in prod, resource limits, named volumes.
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# Docker Compose Conventions

Управляет контейнерной инфраструктурой проекта: 7 сервисов в Docker Compose.
Local — для разработки, Production — с restart policies и resource limits.

## When to Use
- Добавление нового сервиса в `docker-compose.yml` или `docker-compose.prod.yml`
- Изменение resource limits для существующих сервисов
- Редактирование `nginx/conf.d/default.conf`
- Написание или обновление `Dockerfile.bot`
- Настройка healthcheck для сервисов
- Создание `docker-compose.override.yml` для локальной разработки

## Services Overview

| Сервис | Порт | Назначение |
|---|---|---|
| `postgres` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 — кэш + брокер |
| `bot` | — | aiogram бот |
| `celery_worker` | — | Celery workers (concurrency=4) |
| `celery_beat` | — | Планировщик задач |
| `fastapi` | 8000 | API для Mini App |
| `flower` | 5555 | Мониторинг Celery |
| `nginx` | 80 | Reverse proxy |

## Rules
- Local: `docker-compose.yml` — postgres + redis с открытыми портами
- Production: `docker-compose.prod.yml` — все сервисы, restart policies, resource limits
- Все Python-образы: `python:3.13-slim`, multi-stage с `poetry install --only=main`
- Всегда добавлять `healthcheck` для postgres и redis
- Именованные volumes для данных postgres
- Nginx: upstream-блоки для bot (8000) и api (8001)

## Instructions

1. При добавлении нового сервиса — сначала проверь зависимости через `depends_on`
2. Для Python-сервисов — используй многоступенчатую сборку
3. Healthcheck обязателен для `postgres` и `redis`
4. В production — всегда `restart: unless-stopped` и `deploy.resources.limits`
5. Секреты — только через `env_file: .env`, никогда в `docker-compose.yml`

## Examples

### Service Template (production)
```yaml
services:
  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile.bot
      target: production
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512m
          cpus: "0.5"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### Healthchecks
```yaml
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
```

### Multi-stage Dockerfile
```dockerfile
# docker/Dockerfile.bot
FROM python:3.13-slim AS builder
WORKDIR /app
RUN pip install poetry==1.8.0
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --without dev -o requirements.txt

FROM python:3.13-slim AS production
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["python", "-m", "src.bot.main"]
```

### Nginx Upstream Config
```nginx
# nginx/conf.d/default.conf
upstream fastapi {
    server fastapi:8000;
}

server {
    listen 80;
    server_name _;

    location /api/ {
        proxy_pass http://fastapi/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        root /var/www;
        expires 30d;
    }
}
```
