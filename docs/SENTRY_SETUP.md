# 🔍 Настройка Sentry для Market Telegram Bot

Sentry — система мониторинга ошибок в реальном времени. Помогает отслеживать исключения, ошибки и проблемы в production.

---

## 📋 Содержание

1. [Регистрация и получение DSN](#1-регистрация-и-получение-dsn)
2. [Настройка проекта](#2-настройка-проекта)
3. [Интеграция с ботом](#3-интеграция-с-ботом)
4. [Проверка работы](#4-проверка-работы)
5. [Бесплатный тариф и лимиты](#5-бесплатный-тариф-и-лимита)
6. [Альтернативы](#6-альтернативы)

---

## 1. Регистрация и получение DSN

### Шаг 1: Создай аккаунт

1. Перейди на [https://sentry.io](https://sentry.io)
2. Нажми **Sign Up**
3. Зарегистрируйся через GitHub, Google или email

### Шаг 2: Создай проект

1. После входа нажми **Create Project**
2. Выбери платформу: **Python**
3. Назови проект: `market-telegram-bot`
4. Выбери организацию (или создай новую)

### Шаг 3: Получи DSN

1. В настройках проекта перейди в **Settings → Client Keys (DSN)**
2. Скопируй DSN (выглядит как URL)

Пример DSN:
```
https://a1b2c3d4e5f6g7h8i9j0@o123456.ingest.sentry.io/7890123
```

### Шаг 4: Добавь DSN в `.env`

Открой файл `.env` и добавь:

```bash
# Sentry (для production)
SENTRY_DSN=https://a1b2c3d4e5f6g7h8i9j0@o123456.ingest.sentry.io/7890123
```

---

## 2. Настройка проекта

### В файле `src/config/settings.py`

DSN уже читается из переменных окружения:

```python
# Sentry
sentry_dsn: str | None = Field(None, alias="SENTRY_DSN")
```

### В файле `src/bot/main.py`

Sentry инициализируется при запуске бота:

```python
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from src.config.settings import settings

def setup_sentry() -> None:
    """Инициализация Sentry."""
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,  # 10% транзакций
            profiles_sample_rate=0.1,  # 10% профилей
            integrations=[
                AsyncioIntegration(),
            ],
            # Не отправлять ошибки в development
            send_default_pii=settings.is_production,
        )
        logger.info("Sentry initialized")
    else:
        logger.warning("Sentry DSN not configured")
```

---

## 3. Интеграция с ботом

### Автоматический перехват ошибок

Sentry автоматически перехватывает:
- Необработанные исключения
- Ошибки в handlers
- Ошибки в Celery задачах
- Ошибки в API endpoints

### Ручная отправка ошибок

```python
from sentry_sdk import capture_exception, capture_message

# Отправить исключение
try:
    risky_operation()
except Exception as e:
    capture_exception(e)
    logger.error(f"Error: {e}")

# Отправить сообщение
capture_message("Something happened", level="warning")
```

### С контекстом пользователя

```python
from sentry_sdk import set_user, set_tag, set_context

# Установить пользователя
set_user({"telegram_id": user.telegram_id, "username": user.username})

# Установить тег
set_tag("campaign_id", campaign_id)

# Установить контекст
set_context("bot", {"version": "1.0.0", "environment": settings.environment})
```

---

## 4. Проверка работы

### Тестовая ошибка

Добавь в код на 5 секунд после запуска:

```python
# Только для тестирования! Удалить после проверки
if settings.debug:
    raise ValueError("Test Sentry error — можно удалить")
```

### Проверь в Sentry

1. Открой [Sentry Dashboard](https://sentry.io)
2. Выбери проект `market-telegram-bot`
3. Должна появиться тестовая ошибка

### Удали тестовую ошибку

После проверки удали тестовый код из production!

---

## 5. Бесплатный тариф и лимиты

### Free тариф (Developer)

| Параметр | Значение |
|---|---|
| **Ошибок в месяц** | 5000 |
| **Хранение данных** | 30 дней |
| **Пользователи** | Неограниченно |
| **Проекты** | 1 |
| **Команда** | 1 человек |

### Для бота этого хватит на:

- **~166 ошибок в день**
- При 1000 пользователей в день — 5 ошибок на пользователя
- Достаточно для старта и роста до 10k пользователей

### Платные тарифы

| Тариф | Цена | Ошибок/мес |
|---|---|---|
| **Team** | $26/мес | 50 000 |
| **Business** | $80/мес | 200 000 |
| **Enterprise** | Индивидуально | Неограниченно |

---

## 6. Альтернативы

### GlitchTip (Self-hosted)

Открытый аналог Sentry. Можно развернуть на своём сервере.

```bash
# Docker Compose для GlitchTip
git clone https://github.com/glitchtip/glitchtip.git
cd glitchtip
docker compose up -d
```

**Плюсы:**
- Бесплатно (свой сервер)
- Нет лимитов
- Полный контроль

**Минусы:**
- Нужно администрировать
- Меньше функций

### Highlight.io

Full-stack мониторинг с бесплатным тарифом.

| Параметр | Значение |
|---|---|
| **Сессий в месяц** | 1000 |
| **Ошибок** | Неограниченно |
| **Хранение** | 7 дней |

### Axo

Новый сервис с простым интерфейсом.

| Параметр | Значение |
|---|---|
| **Ошибок в месяц** | 5000 |
| **Хранение** | 30 дней |
| **Цена** | Бесплатно |

---

## 🔧 Конфигурация для production

### `docker-compose.prod.yml`

```yaml
services:
  bot:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
      - DEBUG=false

  worker:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production

  api:
    environment:
      - SENTRY_DSN=${SENTRY_DSN}
      - ENVIRONMENT=production
```

### `.env.production`

```bash
# Sentry для production
SENTRY_DSN=https://your-production-dsn@sentry.io/project-id

# Не отправлять персональные данные
SENTRY_SEND_PII=false

# Sample rate для production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

---

## 📊 Что отслеживать в Sentry

### Критические ошибки

- ❌ `DatabaseConnectionError` — проблемы с БД
- ❌ `TelegramAPIError` — проблемы с Telegram API
- ❌ `PaymentError` — ошибки платежей
- ❌ `CeleryTaskError` — упавшие задачи

### Предупреждения

- ⚠️ `LowBalanceWarning` — низкий баланс пользователя
- ⚠️ `RateLimitWarning` — превышение лимитов
- ⚠️ `ContentFilterWarning` — подозрительный контент

### Информация

- ℹ️ `CampaignStarted` — запуск кампании
- ℹ️ `UserRegistered` — новый пользователь
- ℹ️ `PaymentSuccess` — успешная оплата

---

## 🚨 Alerts и уведомления

### Настрой уведомления в Sentry

1. **Settings → Alerts → Create Alert**
2. Выбери условие:
   - `Error Count` > 100 за 5 минут
   - `New Issue` detected
3. Выбери канал:
   - Email
   - Slack
   - Telegram (через webhook)
   - PagerDuty

### Пример alert для Telegram

```python
# Отправить alert в Telegram при критической ошибке
from src.bot.handlers.admin import notify_admin

@sentry_sdk.set_context("alert")
def on_critical_error(event, hint):
    """Обработчик критических ошибок."""
    if event.get("level") == "error":
        notify_admin(
            admin_id=settings.admin_ids[0],
            message=f"🚨 Critical error in Sentry!\n\n{event.get('message')}",
        )
```

---

## 📈 Метрики и дашборды

### Создай дашборд в Sentry

1. **Dashboards → Create Dashboard**
2. Добавь виджеты:
   - Error Count over time
   - Top Issues
   - User Impact
   - Performance Metrics

### Рекомендуемые метрики

| Метрика | Описание |
|---|---|
| `errors.per_minute` | Ошибок в минуту |
| `users.affected` | Пользователей затронуто |
| `transactions.failure_rate` | Процент неудачных транзакций |
| `releases.crash_free_users` | Пользователей без крэшей |

---

## ✅ Чек-лист перед запуском

- [ ] Зарегистрирован аккаунт Sentry
- [ ] Создан проект `market-telegram-bot`
- [ ] Получен и добавлен DSN в `.env`
- [ ] Sentry инициализируется в `main.py`
- [ ] Протестирована отправка ошибок
- [ ] Настроены alerts для критических ошибок
- [ ] Создан дашборд с основными метриками
- [ ] Удалены тестовые ошибки из кода
- [ ] Настроены sample rate для production

---

## 📞 Поддержка

- [Документация Sentry](https://docs.sentry.io)
- [Python SDK](https://docs.sentry.io/platforms/python/)
- [Telegram канал Sentry](https://t.me/sentryio)
- [GitHub Issues](https://github.com/getsentry/sentry/issues)

---

**Готово!** 🎉 Теперь все ошибки бота будут отслеживаться в Sentry.
