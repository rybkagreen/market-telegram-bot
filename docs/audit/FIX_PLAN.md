# 📋 ПЛАН ИСПРАВЛЕНИЙ — RACE CONDITIONS & FSM LEAKS

**Проект:** Market Telegram Bot (RekHarborBot)  
**Дата:** 2026-03-10  
**На основе аудита:** `docs/audit/reports/RACE_CONDITIONS_AUDIT.md`  
**Всего задач:** 11 (3 P0 + 4 P1 + 4 P2)

---

## 🔴 ПРИОРИТЕТ P0 — КРИТИЧЕСКИЕ (НЕДЕЛЯ 1)

### P0.1 — RC1: Добавить `with_for_update()` в `xp_service.py` и `badge_service.py`

**Проблема:** Прямое изменение `user.credits` без блокировки → потеря обновлений при гонке.

**Файлы для изменения:**
1. `src/core/services/xp_service.py` (строка 546)
2. `src/core/services/badge_service.py` (строка 206)

**Изменения:**

#### xp_service.py

**Было (строки 540-560):**
```python
async def award_daily_login_bonus(self, user_id: int) -> dict[str, Any]:
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if not user:
            return {"error": "User not found"}

        # Начисляем XP
        user.xp_points += earned_bonus["xp"]

        # Начисляем кредиты
        user.credits += earned_bonus["credits"]  # ❌ RACE CONDITION

        # Выдаём значок если есть
        badge_awarded = None
        if earned_bonus.get("badge_code"):
            result = await badge_service.award_badge(user_id, earned_bonus["badge_code"])
            if result.get("success"):
                badge_awarded = result

        await session.commit()
```

**Стало:**
```python
async def award_daily_login_bonus(self, user_id: int) -> dict[str, Any]:
    async with async_session_factory() as session, session.begin():
        # ✅ Блокировка строки для предотвращения гонки
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return {"error": "User not found"}

        # Начисляем XP
        user.xp_points += earned_bonus["xp"]

        # Начисляем кредиты
        user.credits += earned_bonus["credits"]  # ✅ Теперь безопасно

        # Выдаём значок если есть
        badge_awarded = None
        if earned_bonus.get("badge_code"):
            result = await badge_service.award_badge(user_id, earned_bonus["badge_code"])
            if result.get("success"):
                badge_awarded = result

        # session.begin() автоматически commit
```

#### badge_service.py

**Было (строки 195-215):**
```python
async def _award_badge_and_rewards(
    self,
    user_id: int,
    badge_id: int,
    session: AsyncSession,
) -> dict[str, Any]:
    # Находим значок
    badge = await session.get(Badge, badge_id)
    if not badge:
        return {"error": "Badge not found"}

    user = await session.get(User, user_id)
    if not user:
        return {"error": "User not found"}

    rewards = {"xp": 0, "credits": 0}

    if badge:
        user = await session.get(User, user_id)
        if user:
            if badge.xp_reward > 0:
                user.xp_points += badge.xp_reward  # ❌ RACE CONDITION
                rewards["xp"] = badge.xp_reward

            if badge.credits_reward > 0:
                user.credits += badge.credits_reward  # ❌ RACE CONDITION
                rewards["credits"] = badge.credits_reward
```

**Стало:**
```python
async def _award_badge_and_rewards(
    self,
    user_id: int,
    badge_id: int,
    session: AsyncSession,
) -> dict[str, Any]:
    # Находим значок
    badge = await session.get(Badge, badge_id)
    if not badge:
        return {"error": "Badge not found"}

    # ✅ Блокировка пользователя для предотвращения гонки
    stmt = select(User).where(User.id == user_id).with_for_update()
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return {"error": "User not found"}

    rewards = {"xp": 0, "credits": 0}

    if badge.xp_reward > 0:
        user.xp_points += badge.xp_reward  # ✅ Теперь безопасно
        rewards["xp"] = badge.xp_reward

    if badge.credits_reward > 0:
        user.credits += badge.credits_reward  # ✅ Теперь безопасно
        rewards["credits"] = badge.credits_reward
```

**Тесты:**
```python
# tests/unit/test_xp_service.py
async def test_award_daily_login_bonus_no_race():
    """Проверка что начисление кредитов атомарное."""
    # Запустить 2 параллельных начисления
    task1 = xp_service.award_daily_login_bonus(user_id)
    task2 = xp_service.award_daily_login_bonus(user_id)
    results = await asyncio.gather(task1, task2)
    # Убедиться что оба начисления прошли без потерь
```

**Время:** 2 часа  
**Исполнитель:** belin  
**Проверка:** Запустить тесты на гонки с `pytest-asyncio` + `pytest-race`

---

### P0.2 — FSM1: Добавить FSM timeout middleware

**Проблема:** Нет автоматического сброса состояния после timeout → пользователи застревают в FSM.

**Файлы для создания:**
1. `src/bot/middlewares/fsm_timeout.py` (новый)
2. `src/bot/middlewares/__init__.py` (обновить)

#### fsm_timeout.py (новый файл)

```python
"""
Middleware для автоматического сброса FSM состояния после timeout.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.state import State
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

# Timeout в секундах (5 минут)
FSM_TIMEOUT = 300


class FSMTimeoutMiddleware(BaseMiddleware):
    """
    Middleware проверяет время последнего сообщения в FSM диалоге.
    Если прошло больше FSM_TIMEOUT секунд — сбрасывает состояние.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from aiogram.fsm.context import FSMContext

        state = data.get("state")
        if state is None:
            return await handler(event, data)

        # Проверяем текущее состояние
        current_state = await state.get_state()
        if not current_state or current_state == "-":
            return await handler(event, data)

        # Получаем данные FSM
        fsm_data = await state.get_data()
        last_activity = fsm_data.get("_last_activity")

        now = datetime.now(UTC).timestamp()

        if last_activity:
            elapsed = now - last_activity
            if elapsed > FSM_TIMEOUT:
                # Timeout истёк — сбрасываем состояние
                logger.info(
                    f"FSM timeout for user {data.get('event_from_user', {}).get('id')}: "
                    f"{elapsed:.0f}s > {FSM_TIMEOUT}s"
                )
                await state.clear()
                return await handler(event, data)

        # Обновляем время активности
        await state.update_data(_last_activity=now)

        return await handler(event, data)
```

#### Обновление `__init__.py`

**Было:**
```python
from src.bot.middlewares.throttling import ThrottlingMiddleware

__all__ = ["ThrottlingMiddleware"]
```

**Стало:**
```python
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.bot.middlewares.fsm_timeout import FSMTimeoutMiddleware

__all__ = ["ThrottlingMiddleware", "FSMTimeoutMiddleware"]
```

#### Регистрация в `src/bot/main.py`

**Найти (строка ~100):**
```python
dp.update.middleware(ThrottlingMiddleware(redis=redis_client))
```

**Добавить после:**
```python
dp.update.middleware(FSMTimeoutMiddleware())
```

**Тесты:**
```python
# tests/unit/test_fsm_timeout.py
async def test_fsm_timeout_clears_state():
    """Проверка что состояние сбрасывается после timeout."""
    # Установить состояние
    await state.set_state(CampaignStates.waiting_topic)
    await state.update_data(_last_activity=datetime.now(UTC).timestamp() - 400)
    
    # Отправить событие
    await handler(event, data)
    
    # Проверить что состояние сброшено
    assert await state.get_state() is None
```

**Время:** 3 часа  
**Исполнитель:** tsaguria  
**Проверка:** Создать FSM состояние → подождать 5 минут → отправить сообщение → убедиться что состояние сброшено

---

### P0.3 — CR1: Добавить проверку duplicate task_id в `send_campaign()`

**Проблема:** Двойной запуск кампании → дублирование отправок.

**Файл:** `src/tasks/mailing_tasks.py` (строка 30)

**Было (строки 26-60):**
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
def send_campaign(self, campaign_id: int) -> dict[str, Any]:
    """Отправить кампанию по чатам."""
    logger.info(f"Starting campaign {campaign_id}")

    async def _send_async() -> dict[str, Any]:
        async with async_session_factory() as session:
            campaign_repo = CampaignRepository(session)
            campaign = await campaign_repo.get_by_id(campaign_id)

            if not campaign:
                return {"error": "Campaign not found"}

            if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.QUEUED]:
                return {"skipped": "Campaign not in running/queued state"}
```

**Стало:**
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
def send_campaign(self, campaign_id: int) -> dict[str, Any]:
    """Отправить кампанию по чатам."""
    logger.info(f"Starting campaign {campaign_id}")

    # ✅ ПРОВЕРКА НА ДУБЛИКАТ
    task_key = f"campaign_running:{campaign_id}"
    existing_task_id = redis_client.get(task_key)
    
    if existing_task_id:
        logger.warning(f"Campaign {campaign_id} already running (task: {existing_task_id})")
        return {"skipped": "Already running"}
    
    # Установить блокировку на 2 часа (максимальное время кампании)
    redis_client.setex(task_key, 7200, self.request.id)

    try:
        return _execute_campaign(campaign_id)
    finally:
        # Очистить блокировку после завершения
        redis_client.delete(task_key)


def _execute_campaign(campaign_id: int) -> dict[str, Any]:
    """Основная логика кампании."""
    async def _send_async() -> dict[str, Any]:
        async with async_session_factory() as session:
            campaign_repo = CampaignRepository(session)
            campaign = await campaign_repo.get_by_id(campaign_id)

            if not campaign:
                return {"error": "Campaign not found"}

            if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.QUEUED]:
                return {"skipped": "Campaign not in running/queued state"}
```

**Дополнительно:** Добавить импорт redis в начало файла:
```python
from redis.asyncio import Redis
from src.config.settings import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
```

**Тесты:**
```python
# tests/unit/test_mailing_tasks.py
async def test_send_campaign_duplicate_prevented():
    """Проверка что дубликат кампании блокируется."""
    # Запустить первую кампанию
    task1 = send_campaign.delay(campaign_id)
    
    # Попытаться запустить вторую (должна вернуться сразу)
    result = send_campaign.delay(campaign_id)
    assert result.get()["skipped"] == "Already running"
```

**Время:** 3 часа  
**Исполнитель:** belin  
**Проверка:** Запустить 2 параллельных задачи send_campaign → убедиться что вторая вернула "Already running"

---

## 🟠 ПРИОРИТЕТ P1 — ВАЖНЫЕ (НЕДЕЛЯ 2)

### P1.1 — FSM2: Добавить `state.clear()` в `start.py` (else ветка)

**Файл:** `src/bot/handlers/start.py` (строка 220)

**Было (строки 200-230):**
```python
if user_context.has_channels or user_context.has_campaigns:
    await state.clear()
    # Продолжаем обычную логику ниже
else:
    # Пользователь всё ещё в онбординге — показываем меню без онбординга
    plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan
    text = f"👋 <b>С возвращением...</b>"
    await send_banner_with_menu(...)
    return  # ❌ state не сброшен!
```

**Стало:**
```python
if user_context.has_channels or user_context.has_campaigns:
    await state.clear()
else:
    # ✅ Сбросить состояние перед показом меню
    await state.clear()
    
    # Пользователь всё ещё в онбординге — показываем меню без онбординга
    plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan
    text = f"👋 <b>С возвращением...</b>"
    await send_banner_with_menu(...)
    return
```

**Время:** 30 минут  
**Исполнитель:** tsaguria  
**Проверка:** Создать FSM состояние → `/start` → убедиться что состояние сброшено

---

### P1.2 — FSM3: Добавить глобальный `/cancel` handler

**Файл:** `src/bot/handlers/start.py` (добавить после строки 867)

**Добавить в конец файла:**
```python
# ─────────────────────────────────────────────
# Глобальный /cancel handler (Спринт 11)
# ─────────────────────────────────────────────

@router.message(Command("cancel"))
async def cancel_fsm_handler(message: Message, state: StateProxy) -> None:
    """
    Глобальная команда для сброса любого FSM состояния.
    Работает из любого состояния.
    """
    current_state = await state.get_state()
    
    if current_state and current_state != "-":
        await state.clear()
        await message.answer(
            "❌ <b>Диалог отменён</b>\n\n"
            "Выберите действие в меню:",
            reply_markup=get_main_menu(...),
        )
        logger.info(f"FSM cancelled for user {message.from_user.id}")
    else:
        # Нет активного состояния — показать справку
        await message.answer(
            "ℹ️ <b>Нет активного диалога</b>\n\n"
            "Используйте команды:\n"
            "/start — Главное меню\n"
            "/help — Помощь\n"
            "/cabinet — Личный кабинет"
        )
```

**Время:** 1 час  
**Исполнитель:** tsaguria  
**Проверка:** Войти в любой FSM диалог → `/cancel` → убедиться что состояние сброшено

---

### P1.3 — CR2: Добавить дедупликацию в `notify_user()`

**Файл:** `src/tasks/notification_tasks.py` (строка 180)

**Было (строки 180-220):**
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")
def notify_user(
    self,
    user_id: int,
    message: str,
    notification_type: str = "system",
    title: str | None = None,
    campaign_id: int | None = None,
) -> bool:
    """Отправить уведомление пользователю."""
    logger.info(f"Sending notification to user {user_id}")

    async def _notify_async() -> bool:
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            
            if not user:
                return False

            bot = Bot(token=settings.bot_token)
            await bot.send_message(chat_id=user.telegram_id, text=message)
```

**Стало:**
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")
def notify_user(
    self,
    user_id: int,
    message: str,
    notification_type: str = "system",
    title: str | None = None,
    campaign_id: int | None = None,
) -> bool:
    """Отправить уведомление пользователю."""
    
    # ✅ ПРОВЕРКА НА ДУБЛИКАТ (кэш в Redis на 5 минут)
    dedup_key = f"notification:{user_id}:{hash(message)}:{notification_type}"
    if redis_client.exists(dedup_key):
        logger.debug(f"Duplicate notification skipped: {dedup_key}")
        return False
    
    redis_client.setex(dedup_key, 300, "1")  # 5 минут

    logger.info(f"Sending notification to user {user_id}")

    async def _notify_async() -> bool:
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            
            if not user:
                return False

            bot = Bot(token=settings.bot_token)
            await bot.send_message(chat_id=user.telegram_id, text=message)
```

**Добавить импорт:**
```python
from redis.asyncio import Redis
from src.config.settings import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
```

**Время:** 2 часа  
**Исполнитель:** belin  
**Проверка:** Запустить 2 параллельных `notify_user.delay()` с одинаковыми аргументами → второе должно вернуть False

---

### P1.4 — CB1: Добавить защиту от double-click для критических кнопок

**Файлы:**
1. `src/bot/handlers/cabinet.py` (запуск кампании)
2. `src/bot/handlers/billing.py` (оплата)

#### cabinet.py (строка ~1050)

**Было:**
```python
@router.callback_query(CampaignCB.filter(F.action == "launch"))
async def launch_campaign_callback(...):
    # Запуск кампании
    task = send_campaign.delay(campaign.id)
    meta["celery_task_id"] = task.id
    await callback.answer("Кампания запущена")
```

**Стало:**
```python
@router.callback_query(CampaignCB.filter(F.action == "launch"))
async def launch_campaign_callback(...):
    # ✅ ПРОВЕРКА: не запущена ли уже кампания
    if campaign.status == CampaignStatus.RUNNING:
        await callback.answer("⚠️ Кампания уже запущена", show_alert=True)
        return
    
    if campaign.status == CampaignStatus.DONE:
        await callback.answer("⚠️ Кампания уже завершена", show_alert=True)
        return

    # Запуск кампании
    task = send_campaign.delay(campaign.id)
    meta["celery_task_id"] = task.id
    await callback.answer("✅ Кампания запущена")
```

**Время:** 2 часа  
**Исполнитель:** tsaguria  
**Проверка:** Двойной клик на "Запустить кампанию" → второе нажатие должно вернуть "Кампания уже запущена"

---

## 🟡 ПРИОРИТЕТ P2 — СРЕДНИЕ (НЕДЕЛЯ 3-4)

### P2.1 — RC2: Использовать явный `update()` вместо прямого изменения атрибутов

**Файлы:**
- `src/core/services/billing_service.py` (строки 325, 557, 664, 777)

**Было:**
```python
user.credits -= plan_price
```

**Стало:**
```python
from sqlalchemy import update

await session.execute(
    update(User)
    .where(User.id == user_id)
    .values(credits=User.credits - plan_price)
)
```

**Время:** 4 часа  
**Исполнитель:** belin

---

### P2.2 — RC3: Добавить `with_for_update()` при изменении статуса кампании

**Файл:** `src/db/repositories/campaign_repo.py` (строка 146)

**Время:** 2 часа  
**Исполнитель:** belin

---

### P2.3 — CR3: Добавить `expires=60` для периодических задач Beat

**Файл:** `src/tasks/celery_config.py`

**Было:**
```python
"check-low-balance": {
    "task": "src.tasks.notification_tasks.check_low_balance",
    "schedule": crontab(minute=0),
},
```

**Стало:**
```python
"check-low-balance": {
    "task": "src.tasks.notification_tasks.check_low_balance",
    "schedule": crontab(minute=0),
    "options": {"expires": 60},  # Истекнет через 1 минуту
},
```

**Время:** 1 час  
**Исполнитель:** belin

---

### P2.4 — RR1: Использовать `INCR` для счётчиков rate limiting

**Файл:** `src/bot/middlewares/throttling.py` (строка 74)

**Было:**
```python
await self.redis.setex(key, 1, "1")
```

**Стало:**
```python
# Использовать INCR для атомарного счётчика
ttl = await self.redis.ttl(key)
if ttl == -1:  # Ключ не существует
    await self.redis.setex(key, 1, 1)
else:
    await self.redis.incr(key)
```

**Время:** 2 часа  
**Исполнитель:** tsaguria

---

### P2.5 — TX1: Унифицировать использование `with_for_update()`

**Аудит всех сервисов:**
- `src/core/services/*.py`

**Время:** 4 часа  
**Исполнитель:** belin

---

## 📊 ГРАФИК ВЫПОЛНЕНИЯ

| Неделя | Задачи | Исполнители | Часы |
|--------|--------|-------------|------|
| **Неделя 1 (P0)** | P0.1, P0.2, P0.3 | belin, tsaguria | 8 |
| **Неделя 2 (P1)** | P1.1, P1.2, P1.3, P1.4 | tsaguria, belin | 7.5 |
| **Неделя 3 (P2)** | P2.1, P2.2, P2.3 | belin | 7 |
| **Неделя 4 (P2)** | P2.4, P2.5 | tsaguria, belin | 6 |
| **ИТОГО** | **11 задач** | | **28.5 часов** |

---

## ✅ КРИТЕРИИ ПРИЁМКИ

### Для каждой задачи:

1. **Код изменён** согласно спецификации
2. **Тесты написаны** и проходят
3. **Ручная проверка** выполнена (описание в задаче)
4. **Git commit** с описанием изменений
5. **PR создан** и approved другим разработчиком

### Финальная проверка:

```bash
# Запустить все тесты
make test

# Проверить покрытие
make coverage

# Запустить линтеры
make lint

# Проверить миграции
make migrate
```

---

## 📝 ШАБЛОН GIT COMMIT

```bash
git commit -m "fix(race): add with_for_update() to xp_service.award_daily_login_bonus

P0.1 — RC1: Race condition при начислении кредитов

Изменения:
- src/core/services/xp_service.py: добавить with_for_update()
- src/core/services/badge_service.py: добавить with_for_update()

Тесты:
- tests/unit/test_xp_service.py: test_award_daily_login_bonus_no_race

Fixes: #16 (Race Conditions Audit P0.1)"
```

---

**ПЛАН УТВЕРЖДЁН:** 2026-03-10  
**СЛЕДУЮЩИЙ АУДИТ:** После завершения всех исправлений (4 недели)
