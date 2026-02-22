# Market Telegram Bot

Telegram-бот для управления рекламными кампаниями в Telegram-чатах.

## 📋 Описание

Market Telegram Bot — это платформа для запуска рекламных кампаний в Telegram-чатах. Бот позволяет:

- Создавать и запускать рекламные кампании
- Использовать ИИ для генерации текстов
- Выбирать целевую аудиторию по тематикам и размеру чатов
- Планировать рассылки
- Отслеживать статистику и аналитику
- Управлять балансом и тарифами

## 🛠️ Стек

### Backend
- **Python 3.13** — основной язык
- **aiogram 3** — Telegram Bot API
- **SQLAlchemy 2** — ORM
- **PostgreSQL** — база данных
- **Redis** — кэш и брокер для Celery
- **Celery** — асинхронные задачи
- **FastAPI** — API для Mini App

### Frontend (Mini App)
- **React 19** — UI библиотека
- **TypeScript** — типизация
- **Vite** — сборщик
- **TailwindCSS** — стили
- **Recharts** — графики
- **Zustand** — state manager

## 🚀 Быстрый старт

### Требования

- Python 3.13
- Poetry
- Docker Desktop
- Node.js 20+ (для Mini App)

### Установка

1. Клонировать репозиторий:
```bash
git clone https://github.com/rybkagreen/market-telegram-bot.git
cd market-telegram-bot
```

2. Установить зависимости:
```bash
poetry install
```

3. Скопировать и заполнить `.env`:
```bash
cp .env.example .env
# Заполнить BOT_TOKEN, DATABASE_URL, REDIS_URL
```

4. Запустить инфраструктуру:
```bash
docker compose up -d postgres redis
```

5. Установить pre-commit хуки:
```bash
pre-commit install
```

## 📁 Структура проекта

```
market-telegram-bot/
├── src/
│   ├── bot/              # aiogram бот
│   │   ├── handlers/     # обработчики команд
│   │   ├── keyboards/    # inline клавиатуры
│   │   ├── states/       # FSM состояния
│   │   └── middlewares/  # middleware
│   ├── db/               # работа с БД
│   │   ├── models/       # SQLAlchemy модели
│   │   ├── repositories/ # репозитории
│   │   └── migrations/   # Alembic миграции
│   ├── api/              # FastAPI для Mini App
│   └── config/           # настройки
├── mini_app/             # Telegram Mini App
│   ├── src/              # React компоненты
│   └── public/           # статика
├── tests/                # тесты
├── docker-compose.yml    # Docker инфраструктура
└── pyproject.toml        # зависимости
```

## 🧪 Тестирование

```bash
poetry run pytest
```

## 🔀 Git Workflow

Проект использует **Git Flow** упрощённую модель:

```
main ────────────────●───────────────→ production (стабильные релизы)
                      ╲
develop ──────────────●──────────────→ integration (фичи сливаются сюда)
                       ╲
feature/* ─────────────●─────────────→ временные ветки для задач
```

### Ветки и их назначение

| Ветка | Назначение | Защита |
|-------|------------|--------|
| `main` | Production релизы | 🔒 PR + 1 review |
| `develop` | Интеграция фич | 🔒 PR + 1 review |
| `developer/*` | Ветки разработчиков | ⚠️ CI при PR |
| `feature/*` | Временные фичи | ⚠️ CI при PR |

> **Важно:** GitHub Actions CI отключен из-за блокировки платежного аккаунта. Все проверки выполняются **локально** через pre-commit хуки. См. [LOCAL_CHECKS.md](LOCAL_CHECKS.md) для деталей.

### Процесс разработки

1. **Создайте ветку от `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Вносите изменения и делайте коммиты:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. **Отправьте ветку и создайте PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

   Создайте Pull Request на GitHub: `feature/*` → `develop`

4. **Пройдите Code Review:**
   - Минимум 1 approval от ревьюера
   - Все CI чеки должны проходить (lint, typecheck, test)

5. **После мержа в `develop`:**
   - Протестируйте изменения
   - При готовности создайте PR `develop` → `main` для релиза

## 📋 Contributing

### Требования к коду

- **Code style:** ruff (PEP 8 + project rules)
- **Type hints:** mypy strict mode
- **Tests:** pytest с покрытием критических путей

### Пре-коммит хуки

Проект использует pre-commit для автоматических проверок:

```bash
# Установка
pre-commit install

# Запуск вручную (полная проверка)
make check

# Или через pre-commit
pre-commit run --all-files
```

**Проверяется при каждом коммите:**
- ✅ ruff (lint + format)
- ✅ mypy (typecheck)
- ✅ pytest (tests)
- ✅ detect-secrets (секреты)
- ✅ pre-commit-hooks (YAML, пробелы, концовки файлов)

Подробности в [LOCAL_CHECKS.md](LOCAL_CHECKS.md).

### CI/CD Pipeline

> ⚠️ **GitHub Actions CI отключен** из-за блокировки платежного аккаунта GitHub.

Все проверки выполняются **локально** через pre-commit хуки:

```bash
# Полная проверка перед коммитом
make check

# Или установить pre-commit для автоматических проверок
make pre-commit-install
```

**Deploy workflow** (`deploy.yml`) продолжает работать для `main` ветки — деплой на timeweb.cloud при пуше.

### Code Owners

| Путь | Владелец |
|------|----------|
| `src/bot/` | @rybkagreen |
| `src/api/` | @rybkagreen |
| `src/db/` | @rybkagreen |
| `docker-compose.yml`, `Dockerfile*` | @rybkagreen |
| `.github/` | @rybkagreen |

См. [`.github/CODEOWNERS`](.github/CODEOWNERS) для деталей.

### Применение правил защиты веток

Для настройки branch protection rules (требуется admin доступ):

```bash
# Через Makefile
make protect-branches

# Или напрямую
./scripts/apply_branch_protection.sh
```

⚠️ **Важно:** Не вносите изменения напрямую в `main` или `develop` — это нарушит правила защиты.

## 📝 Лицензия

MIT
