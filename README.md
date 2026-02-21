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
| `main` | Production релизы | 🔒 PR + 1 review + CI (lint, typecheck, test) |
| `develop` | Интеграция фич | 🔒 PR + 1 review + CI (lint, typecheck, test) |
| `developer/*` | Ветки разработчиков | ⚠️ CI при PR (lint, typecheck) |
| `feature/*` | Временные фичи | ⚠️ CI при PR (lint, typecheck, test) |

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

# Запуск вручную
pre-commit run --all-files
```

### CI/CD Pipeline

При создании PR автоматически запускаются:

- **lint** — ruff check + ruff format
- **typecheck** — mypy
- **test** — pytest

Все чеки должны проходить зелёным перед мёржем.

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

## 📄 Лицензия

MIT
