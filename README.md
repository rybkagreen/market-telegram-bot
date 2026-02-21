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
git clone https://github.com/your-org/market-telegram-bot.git
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

## 📝 Лицензия

MIT
