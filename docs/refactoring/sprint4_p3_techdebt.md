# QWEN CODE — СПРИНТ 4: ТЕХНИЧЕСКИЙ ДОЛГ (P3)

## ⚠️ ПРАВИЛА ВЫПОЛНЕНИЯ — ЧИТАЙ ПЕРЕД СТАРТОМ

1. **Все предыдущие спринты должны быть завершены**
2. **Этот спринт — исключительно рефакторинг** — никакой новой функциональности
3. **Каждое изменение** — минимально инвазивное. Не переписывай то что работает
4. **Тесты (задача 5)** — единственная задача где создаётся новый функциональный код
5. **Коммить по задачам** — каждая задача = отдельный логический блок изменений

---

## ЗАДАЧА 1 — Удалить закомментированный код и мёртвые константы

### Файлы:
```
src/core/services/billing_service.py — эскроу-заглушки
src/utils/content_filter/filter.py — убедиться что старый L3 код удалён (после Спринта 1)
src/api/constants/celery.py — дублирует celery_config.py
src/api/constants/content_filter.py — пустой/минимальный
src/api/constants/limits.py — дублирует tariffs.py
```

### Алгоритм

**Шаг 1.1 — Эскроу-методы в `billing_service.py`:**
```python
# Найти методы:
# - freeze_funds()
# - release_funds_for_placement()
# - refund_frozen_funds()

# Проверить: используются ли они где-нибудь?
grep -rn "freeze_funds\|release_funds_for_placement\|refund_frozen_funds" src/

# Если нигде не используются → УДАЛИТЬ методы полностью
# Если используются → оставить, добавить NotImplementedError с комментарием:
raise NotImplementedError(
    "Escrow механика запланирована в будущем спринте. "
    "Не использовать в production до реализации."
)
```

**Шаг 1.2 — Дублирующие константы:**
```python
# Для каждого файла-кандидата:
# 1. Проверить что в нём есть
# 2. Найти аналоги в других файлах
# 3. Если полный дубль → удалить файл, обновить импорты
# 4. Если частичный дубль → перенести уникальное, удалить файл

# Проверить импорты перед удалением:
grep -rn "from src.api.constants.celery" src/
grep -rn "from src.api.constants.content_filter" src/
grep -rn "from src.api.constants.limits" src/
```

**Шаг 1.3 — Закомментированный код:**
```bash
# Найти закомментированный код (строки начинающиеся с # и содержащие код):
grep -rn "^[[:space:]]*#.*=\|^[[:space:]]*#.*def \|^[[:space:]]*#.*await " \
  src/core/services/ src/tasks/ src/bot/handlers/
# Рассмотреть каждый результат — удалить если это мёртвый код, не TODO и не документация
```

### Критерии готовности
- [ ] Эскроу-методы либо удалены, либо имеют `NotImplementedError`
- [ ] Файлы-дубли констант удалены (или объединены)
- [ ] Проект импортирует без ошибок после удалений
- [ ] Закомментированный мёртвый код удалён

---

## ЗАДАЧА 2 — Вынести тарифные константы в `settings.py`

### Файл: `src/api/constants/tariffs.py` → `src/config/settings.py`

### Контекст
Стоимости тарифов хардкожены в `tariffs.py`. Их нельзя менять без деплоя.

### Что читать перед правкой
```
1. src/api/constants/tariffs.py — все константы
2. src/config/settings.py — текущая структура Pydantic Settings
3. grep -rn "from src.api.constants.tariffs\|TARIFF_" src/ — все места использования
```

### Что реализовать

**В `settings.py` добавить секцию:**
```python
class Settings(BaseSettings):
    # ... существующие поля ...
    
    # === Тарифные планы ===
    PLAN_PRO_PRICE_RUB: int = 990
    PLAN_BUSINESS_PRICE_RUB: int = 2990
    PLAN_PRO_AI_CREDITS_MONTHLY: int = 50
    PLAN_BUSINESS_AI_CREDITS_MONTHLY: int = 200
    PLAN_PRO_CAMPAIGNS_LIMIT: int = 10
    PLAN_BUSINESS_CAMPAIGNS_LIMIT: int = -1  # безлимит
    # ... и все остальные константы из tariffs.py
```

**В `tariffs.py`** — оставить как thin wrapper для обратной совместимости:
```python
# src/api/constants/tariffs.py
# DEPRECATED: используйте src.config.settings напрямую
# Оставлено для обратной совместимости, будет удалено в следующем спринте

from src.config.settings import settings

PLAN_PRO_PRICE = settings.PLAN_PRO_PRICE_RUB
# ... и т.д.
```

### Критерии готовности
- [ ] Все тарифные значения вынесены в `settings.py`
- [ ] Берутся из `.env` если переменная задана
- [ ] `tariffs.py` обновлён как thin wrapper
- [ ] Нигде не используются хардкоженные числа напрямую

---

## ЗАДАЧА 3 — Стандартизировать обработку ошибок

### Контекст
В проекте смешаны `ValueError`, `HTTPException`, и молчаливые `except: pass`. Нужно привести к единому стандарту.

### Что читать перед правкой
```
1. src/api/main.py — exception handlers (если есть)
2. src/core/services/ — все except блоки
3. src/bot/handlers/ — обработка ошибок в хендлерах
4. src/tasks/ — обработка ошибок в Celery задачах
```

### Стандарт обработки ошибок (следовать строго)

**API (FastAPI):**
```python
# Всегда использовать HTTPException с detail
raise HTTPException(status_code=404, detail="Campaign not found")
raise HTTPException(status_code=400, detail="Insufficient balance")
raise HTTPException(status_code=403, detail="Access denied")
```

**Services (core/services/):**
```python
# Бизнес-ошибки — кастомные исключения (создать если нет):
# src/core/exceptions.py
class InsufficientBalanceError(Exception): pass
class CampaignNotFoundError(Exception): pass
class PayoutError(Exception): pass

# В сервисе:
raise InsufficientBalanceError(f"Balance {user.balance} < required {amount}")
```

**Bot handlers:**
```python
# Перехватывать бизнес-ошибки, показывать пользователю:
try:
    result = await billing_service.deduct_credits(...)
except InsufficientBalanceError:
    await callback.answer("❌ Недостаточно средств", show_alert=True)
    return
```

**Celery tasks:**
```python
# Логировать ошибку, НЕ прерывать задачу из-за одного элемента:
for item in items:
    try:
        await process(item)
    except Exception as e:
        logger.error(f"Failed to process {item}: {e}", exc_info=True)
        continue  # продолжить с следующим элементом
```

### Что делать

**Шаг 3.1 — Создать `src/core/exceptions.py`:**
```python
# Кастомные исключения для бизнес-логики
class RekHarborError(Exception): """Базовый класс"""
class InsufficientBalanceError(RekHarborError): pass
class CampaignNotFoundError(RekHarborError): pass
class PayoutError(RekHarborError): pass
class ContentFilterError(RekHarborError): pass
class AIServiceError(RekHarborError): pass
class RateLimitError(RekHarborError): pass
```

**Шаг 3.2 — Найти и исправить `except: pass` или `except Exception: pass` без логирования:**
```bash
grep -rn "except.*pass\|except Exception.*:\s*$\|except.*:\s*$" src/core/services/ src/tasks/
# Для каждого найденного — добавить logger.error() или использовать кастомное исключение
```

**Шаг 3.3 — Добавить exception handler в FastAPI:**
```python
# src/api/main.py
@app.exception_handler(RekHarborError)
async def rekharbor_error_handler(request: Request, exc: RekHarborError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": type(exc).__name__}
    )
```

### Критерии готовности
- [ ] Файл `src/core/exceptions.py` создан с базовыми классами
- [ ] Нет `except: pass` без логирования в `core/services/` и `tasks/`
- [ ] FastAPI имеет handler для `RekHarborError`
- [ ] Bot handlers показывают пользователю понятные сообщения при ошибках

---

## ЗАДАЧА 4 — Типизировать CallbackData классы

### Контекст
Некоторые callback-хендлеры используют строковое разбиение `callback.data.split(":")` вместо типизированных `CallbackData`. Это источник багов.

### Что читать перед правкой
```bash
# Найти все места с split по callback.data:
grep -rn "callback\.data\.split\|callback_data\.split" src/bot/handlers/
grep -rn "callback\.data ==" src/bot/handlers/
```

### Что реализовать

Для каждого найденного `split`:

**БЫЛО:**
```python
if callback.data.startswith("campaign_action:"):
    parts = callback.data.split(":")
    campaign_id = int(parts[1])
    action = parts[2]
```

**ДОЛЖНО СТАТЬ:**
```python
# В src/bot/keyboards/campaign.py добавить:
class CampaignActionCallback(CallbackData, prefix="campaign_action"):
    campaign_id: int
    action: str

# В хендлере:
@router.callback_query(CampaignActionCallback.filter())
async def handle_campaign_action(
    callback: CallbackQuery,
    callback_data: CampaignActionCallback
):
    campaign_id = callback_data.campaign_id
    action = callback_data.action
```

### ⚠️ Правило: не трогать CallbackData которые уже типизированы — только те что используют split/==

### Критерии готовности
- [ ] Нет `callback.data.split(":")` в хендлерах
- [ ] Нет `callback.data == "string"` для сложных данных (простые флаги допустимы)
- [ ] Все новые CallbackData классы имеют типы

---

## ЗАДАЧА 5 — Базовое тестовое покрытие

### Контекст
Покрытие тестами ~15%. Нужно покрыть критические сервисы минимальными тестами.

### Что создать

**Структура:**
```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── test_xp_service.py
│   ├── test_content_filter.py
│   ├── test_billing_service.py
│   └── test_analytics_service.py
└── integration/
    └── test_api_auth.py
```

**`tests/conftest.py`:**
```python
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.telegram_id = 123456789
    user.credits = Decimal("100.00")
    user.plan = "FREE"
    user.advertiser_xp = 0
    user.owner_xp = 0
    return user
```

**`tests/unit/test_xp_service.py`** — минимум тестов:
```python
# test: get_level_for_xp(0) == 1
# test: get_level_for_xp(999) == 1
# test: get_level_for_xp(1000) == 2  (или какой порог в коде)
# test: get_level_discount(1) == 0
# test: get_level_discount(7) == максимальная скидка
# test: add_xp возвращает LevelUpEvent при переходе уровня
# test: add_xp возвращает None если уровень не изменился
```

**`tests/unit/test_content_filter.py`:**
```python
# test: явный запрещённый текст → passed=False
# test: чистый рекламный текст → passed=True
# test: пустая строка → passed=True (не падает)
# test: очень длинный текст (10000 символов) → не таймаутит
```

**`tests/unit/test_billing_service.py`:**
```python
# test: deduct_credits с достаточным балансом → True
# test: deduct_credits с недостаточным балансом → False или InsufficientBalanceError
# test: deduct_credits обновляет баланс пользователя
```

**`tests/integration/test_api_auth.py`:**
```python
# test: POST /api/auth/login с невалидным initData → 401
# test: GET /api/auth/me без токена → 401
# test: GET /api/auth/me с валидным токеном → 200
```

### Как запускать:
```bash
pytest tests/ -v --tb=short
pytest tests/unit/ -v  # только unit
```

### Критерии готовности
- [ ] `pytest tests/` запускается без ошибок конфигурации
- [ ] Минимум 20 тестов написано
- [ ] XPService протестирован полностью (все публичные методы)
- [ ] ContentFilter протестирован на базовых кейсах
- [ ] `pytest --co` показывает все тесты без collection errors

---

## ФИНАЛЬНАЯ ПРОВЕРКА СПРИНТА 4

```bash
# 1. Финальная проверка импортов
python -c "
from src.core.exceptions import RekHarborError, InsufficientBalanceError
from src.config.settings import settings
from src.bot.main import main
from src.api.main import app
print('All imports OK')
"

# 2. Проверить отсутствие мёртвого кода
grep -rn "except.*:\s*pass" src/core/services/ src/tasks/
# Должно быть пусто или только явно обоснованные случаи

# 3. Проверить отсутствие split по callback.data
grep -rn "callback\.data\.split" src/bot/handlers/
# Должно быть пусто

# 4. Запустить тесты
pytest tests/ -v --tb=short
# Должно быть: X passed, 0 errors

# 5. Финальный линтер по всему проекту
ruff check src/
# Должно быть 0 ошибок (предупреждения допустимы)

# 6. Проверить что нет импортов удалённых файлов
python -c "import src; print('Package OK')"
```

**Спринт считается завершённым** когда:
- Все 5 задач выполнены
- `pytest tests/` проходит без ошибок
- `ruff check src/` — 0 ошибок
- Бот и API стартуют без исключений
