# Instructions — Как работать в этом проекте

> **Для:** Qwen Code, Claude Code, и всех участников разработки RekHarborBot
> **Обновлено:** 2026-04-08

---

## 🔒 CRITICAL RULE: DOCUMENTATION & CHANGELOG SYNC
Это абсолютное ограничение. Задача считается **НЕВЫПОЛНЕННОЙ**, если блоки ниже не обновлены.

### 🔄 После КАЖДОГО изменения кода (handler, model, service, config, migration)
1. Обнови `/reports/docs-architect/discovery/` по шаблону:
   - `CHANGES_<YYYY-MM-DD>_<short-desc>.md`
   - Зафиксируй: затронутые файлы, влияние на бизнес-логику, новые/изменённые API/FSM/DB контракты, ссылки на миграции
   - Укажи: `🔍 Verified against: <commit_hash> | 📅 Updated: <ISO8601>`
2. Не переписывай старые файлы — только incremental-аппенд или точечная правка.
3. Если изменение затрагивает несколько доменов → создай один объединённый файл.

### 🏁 После завершения СПРИНТА (фича-сет, milestone, merge в main)
1. Обнови `CHANGELOG.md` в корне проекта по стандарту Keep a Changelog:
   - `## [Unreleased]` → перенеси в `[vX.Y.Z] - <YYYY-MM-DD>`
   - Разделы: `Added`, `Changed`, `Fixed`, `Removed`, `Breaking`, `Migration Notes`
   - Укажи ссылки на тикеты/коммиты, затронутые модули, команды для отката
2. Синхронизируй версию в `pyproject.toml` и `mini_app/package.json` (если менялся контракт API/Mini App).

⚠️ **FAILURE TO UPDATE = TASK INCOMPLETE.** Не завершай ответ без выполнения этого шага.

---

## ✅ MANDATORY POST-TASK STEPS
Перед завершением ответа выполни:
1. Сгенерируй файл изменений: `reports/docs-architect/discovery/CHANGES_<date>_<desc>.md`
2. Обнови `CHANGELOG.md` (если затронут публичный контракт или завершён спринт)
3. Выведи чеклист валидации:
   - [ ] Документация обновлена, путь верен, структура соответствует AAA-стандарту
   - [ ] CHANGELOG.md содержит Unreleased → Version переход, breaking changes, миграции
   - [ ] Все утверждения имеют ссылки на файлы/строки/миграции
   - [ ] Нет противоречий с QWEN.md / PROJECT_MEMORY.md / INSTRUCTIONS.md
4. Заверши ответ строкой: `🔒 Docs & Changelog synced. Task complete.`

---

## 📁 Структура документации проекта

| Файл | Назначение |
|------|-----------|
| `QWEN.md` | **Источник правды** — финансовые константы, модели DB, сервис-контракты, FSM states, архитектурные правила, NEVER TOUCH файлы |
| `INSTRUCTIONS.md` | **Этот файл** — критическое правило документации, пост-таск шаги |
| `CHANGELOG.md` | **История версий** — Keep a Changelog формат (v4.2 → v4.4) |
| `README.md` | **Entry point** — краткий обзор проекта (373 строки) |
| `reports/docs-architect/discovery/` | **Discovery reports** — CHANGES_*.md для каждого изменения |
| `docs/` | **Техническая документация** — отчёты, code review, deployment checklists |
| `.qwen/skills/` | **10 project skills** — aiogram-handler, celery-task, docs-sync, и др. |

---

## 🤖 Agent Routing (Auto-Dispatch)

При получении задачи автоматически вызывай нужного суб-агента:

| Агент | Зона ответственности |
|-------|---------------------|
| `@backend-core` | aiogram handlers, SQLAlchemy 2 async repos, Celery tasks, Alembic migrations, FastAPI routers |
| `@frontend-miniapp` | React/TS Mini App, Zustand stores, TanStack Query, API контракты, UI/UX |
| `@devops-sre` | Docker Compose, Nginx, CI/CD, Xray/Privoxy, healthchecks, secrets, monitoring |
| `@qa-analysis` | pytest + testcontainers, ruff, mypy, bandit, flake8, coverage gates ≥80% |
| `@prompt-orchestrator` | Многошаговые задачи: research → implementation → verification |
| `@docs-architect-aaa` | Документация: Diátaxis framework, Mermaid, AAA структура |

---

## 🛠️ Основные правила разработки

### Перед началом задачи
1. Прочитай `QWEN.md` — это источник правды для всех констант и контрактов
2. Проверь `CHANGELOG.md` — понимай контекст последних изменений
3. Определи нужного агента из таблицы выше

### После завершения задачи
1. Создай `reports/docs-architect/discovery/CHANGES_<date>_<desc>.md`
2. Обнови `CHANGELOG.md` [Unreleased] раздел
3. Выведи чеклист валидации
4. Заверши: `🔒 Docs & Changelog synced. Task complete.`

### Code Quality Gates
```bash
ruff check src/ --fix && ruff format src/
mypy src/ --ignore-missing-imports
bandit -r src/ -ll
flake8 src/ --max-line-length=120 --extend-ignore=E203,W503
alembic check && alembic current
```
**Target:** Ruff 0, MyPy 0, Bandit High 0, Flake8 0.

### NEVER TOUCH Files
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

### v4.3 Protected Files (DO NOT MODIFY)
```
src/core/security/field_encryption.py
src/api/middleware/audit_middleware.py
src/api/middleware/log_sanitizer.py
src/db/models/audit_log.py
src/db/models/legal_profile.py
src/db/models/contract.py
src/db/models/ord_registration.py
```

---

## 📦 Skills System (.qwen/skills/)

Проект использует 10 специализированных skills. Вызывай их через `skill: "<name>"` перед работой:

| Skill | Когда использовать |
|-------|-------------------|
| `aiogram-handler` | Работа с handlers, FSM states, callback routing, keyboards, middlewares |
| `celery-task` | Celery tasks, retry policies, Beat schedules, background jobs |
| `content-filter` | Модерация контента: 3-level pipeline (regex → pymorphy3 → LLM) |
| `docker-compose` | Docker Compose, multi-stage builds, healthchecks, nginx, proxy |
| `docs-sync` | **ОБЯЗАТЕЛЬНО** после любых изменений кода — обновление документации |
| `fastapi-router` | FastAPI routers, JWT auth, Pydantic v2 schemas, Mini App endpoints |
| `pytest-async` | Async testing, testcontainers, coverage gates, mocking external APIs |
| `python-async` | asyncio patterns, async context managers, error propagation |
| `react-mini-app` | Telegram Mini App: React 19, TS, Vite, glassmorphism, Zustand |
| `sqlalchemy-repository` | SQLAlchemy 2.0 async, repository pattern, session management |

---

## 🔁 Передача контекста между AI моделями

При передаче задачи от Qwen Code → Claude Code (или наоборот):

1. **Передай файлы:**
   - Последние 2 файла из `reports/docs-architect/discovery/`
   - Актуальный `CHANGELOG.md`
   - `QWEN.md` (если изменились константы/модели)

2. **Модель получит:**
   - Точную карту изменений (что changed, why, impact)
   - Историю версий (что было в каждом релизе)
   - Полный контекст проекта (константы, модели, правила)

3. **Модель продолжит работу:**
   - Создаст свой `CHANGES_*.md`
   - Обновит `CHANGELOG.md`
   - Соблюдёт тот же формат документации

---

## ⚠️ Critical Enforcement

Если модель пропускает обновление документации:
- Добавь в промпт: `⚠️ CRITICAL: Отказ от обновления документации = немедленное прекращение задачи. Перезапусти с выполнением POST-TASK STEPS.`
- Или вызови skill напрямую: `skill: "docs-sync"`

---

*INSTRUCTIONS.md v1.0 | 2026-04-08 | RekHarborBot*
