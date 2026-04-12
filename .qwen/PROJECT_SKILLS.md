# RekHarborBot — Quick Skills Reference

> Быстрые ссылки на команды, MCP-инструменты и часто используемые паттерны.
> Для онбординга и снижения когнитивной нагрузки.

---

## 🔧 Команды качества кода

| Команда | Описание |
|---------|----------|
| `ruff check src/ --fix && ruff format src/` | Линтинг + форматирование |
| `mypy src/ --ignore-missing-imports` | Проверка типов |
| `bandit -r src/ -ll` | Security audit (HIGH+) |
| `flake8 src/ --max-line-length=120` | Flake8 lint |
| `pytest tests/ -v --cov=src` | Тесты + coverage |

**Alias:** `/lint-fix` — запускает всё выше в одной команде.

---

## 🗄️ База данных

| Команда | Описание |
|---------|----------|
| `alembic current` | Текущая ревизия БД |
| `alembic upgrade head` | Применить все миграции |
| `alembic revision --autogenerate -m "msg"` | Сгенерировать миграцию |
| `alembic check` | Проверить consistency моделей/миграций |
| `alembic upgrade head --sql` | Показать SQL без выполнения |

**Alias:** `/check-migrations` — current + heads + check.

---

## 🐳 Docker

| Команда | Описание |
|---------|----------|
| `docker compose up -d` | Запустить все сервисы |
| `docker compose logs api --tail=50` | Логи FastAPI |
| `docker compose logs bot --tail=50` | Логи бота |
| `docker compose logs celery_worker --tail=50` | Логи Celery |
| `docker compose exec bot bash` | Shell в контейнере бота |
| `docker compose exec postgres pg_isready` | Проверка PostgreSQL |
| `docker compose down -v` | Остановить + удалить volumes |

---

## 🤖 Sub-Agents (Auto-Dispatch)

| Агент | Когда вызывать |
|-------|---------------|
| `@backend-core` | aiogram handlers, SQLAlchemy repos, Celery tasks, Alembic, сервисы |
| `@frontend-miniapp` | React/TS Mini App, Zustand, API контракты, UI/UX |
| `@devops-sre` | Docker, Nginx, CI/CD, proxy, healthchecks |
| `@qa-analysis` | pytest, ruff, mypy, bandit, coverage gates |
| `@prompt-orchestrator` | Многошаговые задачи: research → implementation → verification |
| `@docs-architect-aaa` | Документация, диаграммы, AAA структура |

---

## 📦 Skills (Auto-Trigger)

| Skill | Триггер | Файлы |
|-------|---------|-------|
| `aiogram-handler` | handlers, FSM, callback routing, keyboards | `src/bot/handlers/`, `src/bot/states/` |
| `celery-task` | background tasks, retry, Beat schedule | `src/tasks/`, `celery_config.py` |
| `content-filter` | moderation, stop-words, policy | `src/core/services/content_filter*` |
| `docker-compose` | compose, Dockerfile, nginx configs | `docker-compose.yml`, `Dockerfile*` |
| `fastapi-router` | API endpoints, JWT auth, Pydantic schemas | `src/api/routers/`, `src/api/schemas/` |
| `pytest-async` | тесты, fixtures, testcontainers | `tests/`, `conftest.py` |
| `python-async` | async def, asyncio patterns | `src/core/services/`, `src/tasks/` |
| `react-mini-app` | React components, Zustand stores | `mini_app/src/` |
| `sqlalchemy-repository` | models, repos, async queries | `src/db/models/`, `src/db/repositories/` |

---

## 🔑 Ключевые файлы проекта

| Путь | Назначение |
|------|-----------|
| `QWEN.md` | Главный контекст проекта (авто-подгрузка) |
| `.qwen/settings.json` | Настройки Qwen Code (permissions, skills) |
| `src/constants/payments.py` | Финансовые константы (15/85, MIN_TOPUP, etc.) |
| `src/config/settings.py` | Настройки приложения, тарифы, секреты |
| `src/db/models/` | SQLAlchemy модели |
| `src/db/repositories/` | Repository паттерн |
| `src/core/services/` | Бизнес-логика |
| `src/bot/handlers/` | Telegram handlers |
| `src/tasks/` | Celery задачи |
| `src/api/routers/` | FastAPI эндпоинты |

---

## 🚫 NEVER TOUCH (Protected Files)

```
src/core/services/xp_service.py
src/bot/handlers/advertiser/campaign_create_ai.py
src/bot/keyboards/advertiser/campaign_ai.py
src/bot/keyboards/shared/main_menu.py
src/bot/states/campaign_create.py
src/db/migrations/versions/  ← только читать
src/utils/telegram/llm_classifier.py
src/utils/telegram/llm_classifier_prompt.py
```

---

## 🔐 Security Rules

- Никогда не логируй токены/ключи/PII
- `FIELD_ENCRYPTION_KEY` для шифрования PII полей
- MCP-серверы с доступом к БД: `trust: false`
- `.env` файлы — только через `env_file` в docker-compose
- Gitleaks проверяет коммиты автоматически

---

## 🔴 КРИТИЧЕСКОЕ: DEPLOYMENT (ОБЯЗАТЕЛЬНО после изменений)

| Тип изменений | Команда | Почему |
|--------------|---------|--------|
| **Фронтенд** (mini_app, web_portal, landing) или **nginx конфиги** | `docker compose build --no-cache nginx && docker compose up -d nginx` | Vite кэширует билды, обычный `up -d` НЕ применит изменения |
| **Backend** (src/) | `docker compose up -d --build api worker_critical worker_background worker_game` | Python файлы на volumes, кэш не проблема |
| **Модели БД** | `docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head` | Применить миграции |

**ЗАПОМНИ:** Изменил файл → выполнил команду → изменения применились. Иначе пользователь будет говорить одно и то же каждый раз.
