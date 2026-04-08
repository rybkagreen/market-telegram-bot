---
name: aiogram-handler
description: "MUST BE USED for aiogram 3.x handlers, FSM states, callback routing with F.data.regexp(), keyboard builders, middlewares, throttling. Use when editing src/bot/handlers/, src/bot/states/, implementing Telegram UI flows, command handlers, inline callbacks, or CallbackData factories. Enforces: no DB access in handlers, call services only, ParseMode.HTML."
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# aiogram 3 Handler Conventions

Создаёт обработчики Telegram-бота на aiogram 3.x с FSM, инлайн-клавиатурами и
middlewares согласно архитектуре проекта. Хендлеры не обращаются к БД напрямую.

## When to Use
- Написание обработчиков команд (`/start`, `/help`, etc.)
- Создание FSM-машин состояний (wizard-флоу)
- Написание callback-хендлеров для инлайн-клавиатур
- Создание `CallbackData` фабрик для кнопок
- Написание middlewares (throttling, auth, logging)
- Работа с `InlineKeyboardBuilder`

## Rules
- Хендлеры НИКОГДА не обращаются к БД напрямую — только через `service.method()` или `repo.method()`
- Все хендлеры — `async def`
- Регистрация через `@router.message()` или `@router.callback_query()`
- Использовать `CallbackData` factory для всех инлайн-callback'ов
- Форматирование сообщений — `ParseMode.HTML`, никогда Markdown
- Обрабатывать ошибки gracefully: ловить исключения, сообщать пользователю понятный текст

## Instructions

1. Создай `Router` в начале файла
2. Определи `CallbackData` классы если нужны кнопки
3. Напиши FSM `StatesGroup` если нужен многошаговый флоу
4. Каждый хендлер — отдельная `async def` функция с типизированными параметрами
5. Зарегистрируй роутер в `src/bot/main.py`

## Examples

### FSM Pattern
```python
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

router = Router()

class CampaignStates(StatesGroup):
    enter_title = State()
    enter_budget = State()
    confirm = State()

@router.message(CampaignStates.enter_title)
async def handle_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await state.set_state(CampaignStates.enter_budget)
    await message.answer("Введите бюджет:", reply_markup=get_budget_kb(back=True))

@router.callback_query(CampaignStates.enter_budget, F.data == "back")
async def handle_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CampaignStates.enter_title)
    await callback.message.edit_text("Введите название:", reply_markup=get_title_kb())
    await callback.answer()
```

### CallbackData + Keyboard
```python
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

class CampaignActionCB(CallbackData, prefix="campaign"):
    action: str
    campaign_id: int

def get_campaign_kb(campaign_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="▶️ Запустить",
        callback_data=CampaignActionCB(action="start", campaign_id=campaign_id)
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=CampaignActionCB(action="delete", campaign_id=campaign_id)
    )
    builder.adjust(2)
    return builder.as_markup()
```

### Throttling Middleware
```python
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis
from typing import Any, Awaitable, Callable

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, rate_limit: float = 0.5) -> None:
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = data.get("event_from_user").id
        key = f"throttle:{user_id}"
        if await self.redis.exists(key):
            return
        await self.redis.setex(key, int(self.rate_limit), 1)
        return await handler(event, data)
```
