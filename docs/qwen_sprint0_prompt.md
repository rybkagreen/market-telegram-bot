# Qwen Code Промт: Спринт 0 — Технический фундамент и публичный дашборд

## Твоя роль и контекст

Ты реализуешь **Спринт 0** проекта RekHarborBot согласно дорожной карте.

Перед любой работой выполни ориентацию — прочитай ключевые документы проекта:

```powershell
# 1. Дорожная карта — обязательно прочитать целиком
cat ROADMAP.md 2>/dev/null || cat docs/roadmap.md 2>/dev/null || \
  echo "ROADMAP не найден — уточни путь у пользователя"

# 2. Текущее состояние проекта
cat README.md | head -80

# 3. Что уже сделано до этого спринта
git log --oneline -15
git status
```

После чтения дорожной карты зафикси:
- Что входит в Спринт 0 (6 задач)
- Какие зависимости у Спринта 1 от Спринта 0
- Какая ветка нужна (`sprint/0` от `develop`)

---

## Контекст Спринта 0

### Почему этот спринт первый

Спринт 0 закрывает два критических P0-блокера:

1. **Легальность** — платформа рассылает рекламу в каналы без согласия владельцев.
   Поле `bot_is_admin` и фильтр в рассыльщике устраняют это.

2. **«Проблема чёрного ящика»** — новые рекламодатели не могут оценить масштаб платформы
   до регистрации. `/stats` и публичный дашборд устраняют это.

**Без Спринта 0 нельзя начинать Спринт 1** — модель `Payout` в Спринте 1 зависит
от `owner_user_id` который создаётся здесь.

### Что уже есть в проекте (не трогать)

- Mypy: 0 ошибок ✅
- Ruff: чист ✅
- Баг 400 CryptoBot: исправлен ✅
- `src/bot/utils/safe_callback.py`: создан ✅
- `TelegramChat` модель: существует в `src/db/models/analytics.py` или `src/db/models/chat.py`
- `User` модель: существует в `src/db/models/user.py`
- Парсинг через Telethon: только чтение, отправка через Bot API ✅

### Состав Спринта 0

| # | Задача | Файлы |
|---|--------|-------|
| 0.1 | Миграция — поля opt-in в TelegramChat | `models/`, `alembic/versions/` |
| 0.2 | Фильтр bot_is_admin в рассыльщике | `tasks/mailing_tasks.py` |
| 0.3 | Хэндлер /add_channel | `bot/handlers/channel_owner.py` (новый) |
| 0.4 | Команда /stats | `bot/handlers/stats.py` (новый), `core/services/analytics_service.py` |
| 0.5 | FastAPI эндпоинт + Mini App страница | `api/routers/analytics.py`, `mini_app/src/` |
| 0.6 | Приветственное сообщение с метриками | `bot/handlers/start.py` |

---

## ГЛОБАЛЬНЫЕ ПРАВИЛА (читать перед каждой задачей)

1. **Читай файл целиком** перед любым изменением — не правь вслепую
2. **Никогда не меняй логику** существующего кода — только добавляй новое
3. **Один коммит на задачу** — не копи изменения из нескольких задач в один коммит
4. **После каждой задачи** — запускай проверочную команду, фиксируй результат
5. **Если структура файла не совпадает** с ожидаемой — остановись, прочитай файл, адаптируй
6. **Не используй** `# type: ignore` без явного обоснования

### Обязательные проверки после каждой задачи

```powershell
poetry run ruff check src/
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -3
```

Оба должны показывать 0 ошибок. Если появились — исправь до следующей задачи.

---

## ПОДГОТОВКА: создать ветку

```powershell
cd ~/python-projects/market-telegram-bot
source .venv/Scripts/activate

git checkout develop
git pull origin develop
git checkout -b sprint/0

git log --oneline -5  # убедись что ты на sprint/0 и видишь последние коммиты develop
```

---

## ЗАДАЧА 0.1: Миграция — поля opt-in в TelegramChat

### Шаг 0.1.1 — Найди модель TelegramChat

```powershell
# Найди где живёт модель
grep -rn "class TelegramChat\|class Chat\b" src/ --include="*.py"

# Прочитай файл целиком
cat [найденный_файл]
```

Зафикси:
- Точный путь к файлу
- Какие поля уже есть
- Как объявляются поля (стиль: `Mapped[...]` или старый `Column(...)`)
- Имя таблицы (`__tablename__`)

### Шаг 0.1.2 — Добавь поля в модель

⚠️ **Используй тот же стиль объявления** что уже есть в файле. Не меняй стиль других полей.

Если в модели используется `Mapped[...]` (SQLAlchemy 2.0):

```python
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Boolean, DateTime, BigInteger, Numeric, ForeignKey
from decimal import Decimal
from datetime import datetime

# Добавить в класс TelegramChat после существующих полей:

# === Поля opt-in (Спринт 0) ===
bot_is_admin: Mapped[bool] = mapped_column(
    Boolean, default=False, nullable=False, server_default="false"
)
admin_added_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
owner_user_id: Mapped[int | None] = mapped_column(
    BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
price_per_post: Mapped[Decimal | None] = mapped_column(
    Numeric(10, 2), nullable=True
)
is_accepting_ads: Mapped[bool] = mapped_column(
    Boolean, default=False, nullable=False, server_default="false"
)
```

Если в модели используется старый стиль `Column(...)`:

```python
from sqlalchemy import Boolean, DateTime, BigInteger, Numeric, ForeignKey
from decimal import Decimal

# Добавить:
bot_is_admin = Column(Boolean, default=False, nullable=False, server_default="false")
admin_added_at = Column(DateTime(timezone=True), nullable=True)
owner_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
price_per_post = Column(Numeric(10, 2), nullable=True)
is_accepting_ads = Column(Boolean, default=False, nullable=False, server_default="false")
```

⚠️ Перед добавлением `ForeignKey("users.id")` убедись что таблица называется именно `users`:
```powershell
grep -n "__tablename__" src/db/models/user.py
```

### Шаг 0.1.3 — Создай Alembic-миграцию

```powershell
# Убедись что Alembic видит изменения
poetry run alembic check 2>&1 | head -5

# Создай миграцию
poetry run alembic revision --autogenerate \
  -m "add_opt_in_fields_to_telegram_chat"

# Найди созданный файл
ls alembic/versions/ | tail -3
```

Прочитай сгенерированную миграцию:
```powershell
cat alembic/versions/[последний_файл].py
```

Убедись что в `upgrade()` есть добавление всех 5 колонок,
а в `downgrade()` есть их удаление. Если чего-то не хватает — добавь вручную.

### Шаг 0.1.4 — Примени миграцию

```powershell
poetry run alembic upgrade head
poetry run alembic current  # должен показывать head
```

### Шаг 0.1.5 — Проверка

```powershell
# Убедись что поля есть в БД
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
# Проверь реальный DATABASE_URL в .env
"

# Или через psql если доступен:
# \d telegram_chats  # должны быть 5 новых колонок

poetry run ruff check src/
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -3
```

### Коммит 0.1

```powershell
git add src/db/models/ alembic/versions/
git status  # убедись что только нужные файлы
git commit -m "feat(opt-in): add bot_is_admin fields to TelegramChat model and migration"
```

---

## ЗАДАЧА 0.2: Фильтр bot_is_admin в рассыльщике

### Шаг 0.2.1 — Найди место запуска рассылки

```powershell
# Найди главную задачу рассылки
grep -rn "def.*campaign\|def.*mailing\|def.*send_campaign\|async def send" \
  src/tasks/mailing_tasks.py | head -20

# Прочитай файл целиком
cat src/tasks/mailing_tasks.py
```

Зафикси:
- Имя функции которая запускает рассылку по каналам
- Как получается список каналов для рассылки (SQL-запрос или метод репозитория)
- Где именно список каналов формируется — это место надо изменить

### Шаг 0.2.2 — Найди репозиторий или запрос получения каналов

```powershell
# Найди где выбираются каналы для кампании
grep -rn "get_chats\|get_channels\|select.*TelegramChat\|query.*chat" \
  src/db/repositories/ src/core/services/ --include="*.py" | head -20
```

Прочитай найденный метод полностью.

### Шаг 0.2.3 — Добавь фильтр

Найди SQL-запрос или ORM-запрос который возвращает список каналов для рассылки.
Добавь условие — **не заменяй** существующие фильтры, только добавляй:

Если это SQLAlchemy ORM:
```python
# БЫЛО (пример — адаптируй под реальный код):
chats = await session.execute(
    select(TelegramChat).where(TelegramChat.is_active == True)
)

# СТАЛО — добавить два условия:
chats = await session.execute(
    select(TelegramChat).where(
        TelegramChat.is_active == True,
        TelegramChat.bot_is_admin == True,      # ← добавить
        TelegramChat.is_accepting_ads == True,   # ← добавить
    )
)
```

Если это raw SQL:
```python
# Добавить в WHERE:
# AND bot_is_admin = true AND is_accepting_ads = true
```

⚠️ Если каналы для рассылки берутся **не напрямую из БД**, а формируются иначе
(например, уже переданы в задачу через параметры) — найди место где этот список
фильтруется или подтверждается и добавь проверку там.

### Шаг 0.2.4 — Проверка

```powershell
poetry run ruff check src/tasks/mailing_tasks.py
poetry run mypy src/tasks/mailing_tasks.py --ignore-missing-imports
```

Напиши простой unit тест в `tests/unit/test_mailing_filter.py`:

```python
"""Тест фильтра bot_is_admin в рассыльщике."""
import pytest
from unittest.mock import AsyncMock, MagicMock


def test_only_opt_in_channels_selected():
    """
    Каналы без bot_is_admin=True не должны попадать в рассылку.
    Проверяет что SQL-запрос содержит нужный фильтр.
    """
    # Адаптируй под реальную структуру репозитория после чтения кода
    # Это минимальный smoke-тест — проверяем что фильтр присутствует
    from src.tasks.mailing_tasks import (
        # импортируй реальную функцию получения каналов
    )
    # TODO: реализовать после изучения реальной структуры
    pass
```

⚠️ Не пиши тест который просто `pass` — прочитай реальную функцию и напиши
хотя бы проверку что фильтр присутствует в запросе. Если не можешь —
сообщи об этом в итоговом отчёте.

### Коммит 0.2

```powershell
git add src/tasks/ src/db/repositories/ src/core/services/ tests/unit/
git status
git commit -m "feat(mailing): filter channels by bot_is_admin and is_accepting_ads"
```

---

## ЗАДАЧА 0.3: Хэндлер /add_channel

### Шаг 0.3.1 — Изучи существующие хэндлеры как образец

```powershell
# Посмотри как устроены другие хэндлеры
cat src/bot/handlers/billing.py | head -80
cat src/bot/states/campaign.py  # как объявляются FSM-состояния

# Посмотри как регистрируются роутеры
cat src/bot/main.py 2>/dev/null || \
  grep -rn "include_router\|router" src/bot/ --include="*.py" | head -15
```

Зафикси:
- Как импортируются и регистрируются роутеры в главном файле бота
- Как объявляются State классы (StatesGroup)
- Как используется `safe_callback_edit` из `src/bot/utils/safe_callback.py`

### Шаг 0.3.2 — Создай файл состояний

**Файл:** `src/bot/states/channel_owner.py` (создать если не существует)

```python
"""FSM состояния для хэндлеров владельца канала."""
from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    """Состояния мастера добавления канала."""
    waiting_username = State()      # ожидаем @username канала
    waiting_verification = State()  # ожидаем нажатия «Проверить»
    waiting_price = State()         # ожидаем цену за пост
    waiting_topics = State()        # ожидаем выбор тематик
```

### Шаг 0.3.3 — Создай хэндлер

**Файл:** `src/bot/handlers/channel_owner.py` (создать)

```python
"""
Хэндлеры для владельцев каналов.
Спринт 0: регистрация канала (/add_channel) с верификацией bot_is_admin.
"""
import logging
from datetime import datetime, timezone

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InaccessibleMessage,
)

from src.bot.states.channel_owner import AddChannelStates
from src.bot.utils.safe_callback import safe_callback_edit

# ⚠️ АДАПТИРУЙ импорты под реальную структуру проекта:
# Найди как импортируется get_user_service, репозиторий TelegramChat и т.д.
# grep -rn "get_user_service\|UserService\|user_service" src/bot/handlers/ --include="*.py" | head -5
# grep -rn "TelegramChat\|chat_repo\|ChatRepository" src/bot/handlers/ --include="*.py" | head -5

logger = logging.getLogger(__name__)
router = Router(name="channel_owner")

# Текст инструкции как добавить бота администратором
ADD_BOT_INSTRUCTION = """
📋 <b>Как добавить бота администратором:</b>

1. Откройте ваш канал в Telegram
2. Нажмите на название канала → <b>Управление каналом</b>
3. Перейдите в <b>Администраторы</b>
4. Нажмите <b>Добавить администратора</b>
5. Найдите <b>@{bot_username}</b>
6. Убедитесь что включено право <b>«Публикация сообщений»</b>
7. Нажмите «Сохранить»

После добавления нажмите кнопку ниже ↓
"""


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, state: FSMContext) -> None:
    """Начало флоу добавления канала."""
    await state.set_state(AddChannelStates.waiting_username)
    await message.answer(
        "📺 <b>Регистрация канала на платформе</b>\n\n"
        "Введите @username вашего канала (например: @mychannel)\n\n"
        "⚠️ Канал должен быть публичным (иметь @username)",
        parse_mode="HTML",
    )


@router.message(AddChannelStates.waiting_username)
async def process_channel_username(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Обработка введённого username канала."""
    if message.text is None:
        await message.answer("Пожалуйста, введите текстовый @username канала.")
        return

    username = (message.text or "").strip().lstrip("@")

    if not username:
        await message.answer("Username не может быть пустым. Попробуйте ещё раз.")
        return

    # Проверяем что канал существует через Bot API
    try:
        chat = await bot.get_chat(f"@{username}")
    except Exception as e:
        logger.warning(f"Cannot get chat @{username}: {e}")
        await message.answer(
            f"❌ Не удалось найти канал <b>@{username}</b>.\n\n"
            "Убедитесь что:\n"
            "• Канал публичный\n"
            "• Username написан верно\n\n"
            "Попробуйте ещё раз:",
            parse_mode="HTML",
        )
        return

    if chat.type not in ("channel", "supergroup"):
        await message.answer(
            "❌ Это не канал. Пожалуйста, укажите @username Telegram-канала."
        )
        return

    # Сохраняем данные в FSM
    bot_info = await bot.get_me()
    await state.update_data(
        channel_username=username,
        channel_telegram_id=chat.id,
        channel_title=chat.title or username,
    )
    await state.set_state(AddChannelStates.waiting_verification)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Я добавил бота, проверить",
            callback_data="check_bot_admin",
        )
    ]])

    await message.answer(
        ADD_BOT_INSTRUCTION.format(bot_username=bot_info.username),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    AddChannelStates.waiting_verification,
    F.data == "check_bot_admin",
)
async def process_verify_bot_admin(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Верификация что бот добавлен администратором."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    channel_id = data.get("channel_telegram_id")
    channel_username = data.get("channel_username")

    if channel_id is None:
        await callback.answer("Ошибка сессии. Начните заново: /add_channel", show_alert=True)
        await state.clear()
        return

    # Проверяем права бота в канале через getChatMember
    try:
        bot_info = await bot.get_me()
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot_info.id)
    except Exception as e:
        logger.error(f"Cannot check bot membership in {channel_id}: {e}")
        await callback.answer(
            "Не удалось проверить права. Попробуйте ещё раз.",
            show_alert=True,
        )
        return

    # Проверяем что бот является администратором с правом публикации
    is_admin = (
        member.status == "administrator"
        and getattr(member, "can_post_messages", False)
    )

    if not is_admin:
        await safe_callback_edit(
            callback.message,
            "❌ <b>Бот не найден среди администраторов</b> или у него нет права публикации.\n\n"
            "Пожалуйста:\n"
            "1. Убедитесь что бот добавлен как администратор\n"
            "2. Включите право <b>«Публикация сообщений»</b>\n"
            "3. Нажмите кнопку снова",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🔄 Проверить ещё раз",
                    callback_data="check_bot_admin",
                )
            ]]),
            parse_mode="HTML",
        )
        return

    # ✅ Бот является администратором — сохраняем в БД
    # ⚠️ АДАПТИРУЙ: найди как сохранять TelegramChat в репозитории
    # Пример (замени на реальный вызов):
    #
    # from src.db.repositories.chat_repo import ChatRepository  # адаптируй импорт
    # chat_repo = ChatRepository(session)
    # await chat_repo.update_opt_in(
    #     telegram_id=channel_id,
    #     bot_is_admin=True,
    #     admin_added_at=datetime.now(timezone.utc),
    #     owner_user_id=callback.from_user.id,  # ← это Telegram ID, нужен внутренний ID из БД
    # )
    #
    # Изучи репозиторий: grep -rn "def update\|async def update" src/db/repositories/ --include="*.py"

    logger.info(
        f"Channel @{channel_username} verified: bot is admin. "
        f"Owner: {callback.from_user.id}"
    )

    # Переходим к следующему шагу — цена за пост
    await state.set_state(AddChannelStates.waiting_price)
    await safe_callback_edit(
        callback.message,
        f"✅ <b>Отлично! Бот добавлен в @{channel_username}</b>\n\n"
        "Теперь укажите <b>цену за один рекламный пост</b> (в рублях).\n\n"
        "Например: <code>1500</code>\n\n"
        "💡 Рекламодатели увидят эту цену в каталоге.",
        parse_mode="HTML",
    )


@router.message(AddChannelStates.waiting_price)
async def process_channel_price(message: Message, state: FSMContext) -> None:
    """Обработка введённой цены за пост."""
    text = (message.text or "").strip()

    if not text.isdigit() or int(text) <= 0:
        await message.answer(
            "❌ Пожалуйста, введите цену числом (только цифры, больше 0).\n"
            "Например: <code>1500</code>",
            parse_mode="HTML",
        )
        return

    price = int(text)
    if price < 100:
        await message.answer(
            "❌ Минимальная цена — 100 рублей. Укажите другую цену:"
        )
        return

    await state.update_data(price_per_post=price)
    await state.set_state(AddChannelStates.waiting_topics)

    # ⚠️ Список тематик должен совпадать с теми что используются в каталоге
    # Найди реальные тематики: grep -rn "TOPICS\|CATEGORIES\|topic_list" src/ --include="*.py" | head -10
    # Адаптируй кнопки под реальные тематики из topic_classifier.py

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💻 IT", callback_data="topic_it"),
            InlineKeyboardButton(text="💼 Бизнес", callback_data="topic_business"),
            InlineKeyboardButton(text="📈 Маркетинг", callback_data="topic_marketing"),
        ],
        [
            InlineKeyboardButton(text="💰 Финансы", callback_data="topic_finance"),
            InlineKeyboardButton(text="🏠 Недвижимость", callback_data="topic_realestate"),
            InlineKeyboardButton(text="🔗 Крипта", callback_data="topic_crypto"),
        ],
        [
            InlineKeyboardButton(text="📰 Новости", callback_data="topic_news"),
            InlineKeyboardButton(text="🎓 Образование", callback_data="topic_education"),
            InlineKeyboardButton(text="🌐 Другое", callback_data="topic_other"),
        ],
        [
            InlineKeyboardButton(
                text="✅ Готово (выбрать позже)", callback_data="topics_done"
            )
        ],
    ])

    await message.answer(
        f"💰 Цена <b>{price} ₽</b> за пост — записано.\n\n"
        "Теперь выберите <b>тематики</b> которые подходят вашему каналу.\n"
        "Рекламодатели используют их для поиска:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    AddChannelStates.waiting_topics,
    F.data.startswith("topic_") | (F.data == "topics_done"),
)
async def process_channel_topics(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработка выбора тематик (мультиселект или завершение)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    selected_topics: list[str] = data.get("selected_topics", [])

    if callback.data == "topics_done":
        # Завершение — активируем канал
        await _finalize_channel_registration(callback, state, selected_topics)
        return

    # Тоггл тематики
    topic_code = (callback.data or "").replace("topic_", "")
    if topic_code in selected_topics:
        selected_topics.remove(topic_code)
    else:
        selected_topics.append(topic_code)

    await state.update_data(selected_topics=selected_topics)

    topics_str = ", ".join(selected_topics) if selected_topics else "не выбрано"
    await callback.answer(f"Выбрано: {topics_str}"[:200])


async def _finalize_channel_registration(
    callback: CallbackQuery,
    state: FSMContext,
    selected_topics: list[str],
) -> None:
    """Финальный шаг — сохранение канала и активация в каталоге."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    channel_username = data.get("channel_username", "")
    channel_telegram_id = data.get("channel_telegram_id")
    channel_title = data.get("channel_title", channel_username)
    price_per_post = data.get("price_per_post")

    # ⚠️ ЗДЕСЬ РЕАЛЬНОЕ СОХРАНЕНИЕ В БД
    # Адаптируй под реальный репозиторий проекта:
    #
    # async with get_db_session() as session:  # ← найди как получить сессию
    #     chat_repo = ChatRepository(session)
    #     # Обновить или создать TelegramChat:
    #     await chat_repo.upsert_opt_in_channel(
    #         telegram_id=channel_telegram_id,
    #         username=channel_username,
    #         title=channel_title,
    #         owner_user_id=...,  # внутренний User.id владельца
    #         bot_is_admin=True,
    #         admin_added_at=datetime.now(timezone.utc),
    #         price_per_post=price_per_post,
    #         is_accepting_ads=True,
    #         accepted_topics=selected_topics,
    #     )

    await state.clear()

    topics_display = ", ".join(selected_topics) if selected_topics else "будут указаны позже"

    await safe_callback_edit(
        callback.message,
        f"🎉 <b>Канал @{channel_username} успешно зарегистрирован!</b>\n\n"
        f"📺 Канал: {channel_title}\n"
        f"💰 Цена за пост: {price_per_post} ₽\n"
        f"🏷 Тематики: {topics_display}\n\n"
        "✅ Канал виден рекламодателям в каталоге.\n\n"
        "Управление каналом: /my_channels",
        parse_mode="HTML",
    )
```

### Шаг 0.3.4 — Адаптируй сохранение в БД

После создания файла выполни:

```powershell
# Найди как получать сессию БД в хэндлерах
grep -rn "get_db\|async_session\|Session\|db:" \
  src/bot/handlers/billing.py \
  src/bot/handlers/campaigns.py | head -20

# Найди репозиторий для работы с каналами
grep -rn "class.*Chat.*Repo\|class.*Channel.*Repo\|ChatRepository\|ChannelRepository" \
  src/db/repositories/ --include="*.py"
cat [найденный_репозиторий]

# Найди как получается User из telegram_id в хэндлерах
grep -rn "get_user\|user_service\|UserService" \
  src/bot/handlers/billing.py | head -10
```

Заполни все места помеченные `# ⚠️ АДАПТИРУЙ` в файле хэндлера,
используя те же паттерны что используются в существующих хэндлерах.

### Шаг 0.3.5 — Зарегистрируй роутер

```powershell
# Найди где регистрируются роутеры
cat src/bot/main.py 2>/dev/null | grep -A 3 "include_router\|router"
grep -rn "include_router" src/bot/ --include="*.py" | head -10
```

Добавь регистрацию в том же месте где зарегистрированы другие хэндлеры:

```python
from src.bot.handlers.channel_owner import router as channel_owner_router
dp.include_router(channel_owner_router)
```

### Шаг 0.3.6 — Проверка

```powershell
poetry run ruff check src/bot/handlers/channel_owner.py
poetry run mypy src/bot/handlers/channel_owner.py --ignore-missing-imports
```

### Коммит 0.3

```powershell
git add src/bot/handlers/channel_owner.py \
        src/bot/states/channel_owner.py \
        src/bot/main.py  # если менял регистрацию роутеров
git status
git commit -m "feat(channel-owner): add /add_channel handler with bot admin verification"
```

---

## ЗАДАЧА 0.4: Команда /stats и сервисный метод

### Шаг 0.4.1 — Добавь метод в AnalyticsService

```powershell
# Прочитай существующий сервис
cat src/core/services/analytics_service.py
```

Добавь метод `get_platform_stats()` в конец класса (не меняй существующие методы):

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PlatformStats:
    """Публичные метрики платформы для дашборда."""
    active_channels_count: int       # каналы с bot_is_admin=True и is_accepting_ads=True
    total_reach: int                 # суммарный member_count активных каналов
    campaigns_launched: int          # всего кампаний не в статусе DRAFT
    campaigns_completed: int         # кампании в статусе DONE
    avg_channel_rating: float        # средний rating по активным каналам
    total_paid_out: Decimal          # суммарно выплачено владельцам (пока 0)


# В классе AnalyticsService добавить:
async def get_platform_stats(self) -> PlatformStats:
    """
    Публичные метрики платформы.
    Используется в /stats команде и Mini App без авторизации.
    """
    # ⚠️ АДАПТИРУЙ под реальную сессию БД в этом сервисе
    # Смотри как другие методы этого класса получают сессию

    # Запрос активных каналов
    # active_channels_result = await self.session.execute(
    #     select(
    #         func.count(TelegramChat.id).label("count"),
    #         func.sum(TelegramChat.member_count).label("total_reach"),
    #         func.avg(TelegramChat.rating).label("avg_rating"),
    #     ).where(
    #         TelegramChat.bot_is_admin == True,
    #         TelegramChat.is_accepting_ads == True,
    #         TelegramChat.is_active == True,
    #     )
    # )
    # row = active_channels_result.one()

    # Запрос кампаний
    # from src.db.models.campaign import Campaign, CampaignStatus
    # campaigns_result = await self.session.execute(
    #     select(
    #         func.count(Campaign.id).label("total"),
    #         func.count(Campaign.id).filter(
    #             Campaign.status == CampaignStatus.DONE
    #         ).label("completed"),
    #     ).where(Campaign.status != CampaignStatus.DRAFT)
    # )
    # c_row = campaigns_result.one()

    # Временные заглушки до реализации Payout в Спринте 1:
    return PlatformStats(
        active_channels_count=0,   # заменить на row.count
        total_reach=0,             # заменить на row.total_reach or 0
        campaigns_launched=0,      # заменить на c_row.total
        campaigns_completed=0,     # заменить на c_row.completed
        avg_channel_rating=0.0,    # заменить на float(row.avg_rating or 0)
        total_paid_out=Decimal("0"),  # Payout будет в Спринте 1
    )
```

⚠️ Раскомментируй и адаптируй SQL-запросы под реальную структуру сервиса.
Не оставляй заглушки с нулями если можешь сделать реальные запросы.

### Шаг 0.4.2 — Создай хэндлер /stats

**Файл:** `src/bot/handlers/stats.py` (создать)

```python
"""
Хэндлер команды /stats — публичный дашборд метрик платформы.
Доступен без авторизации (для гостей).
Спринт 0, задача 0.4.
"""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router(name="stats")


def _format_number(n: int) -> str:
    """Форматирование больших чисел: 1234567 → 1 234 567."""
    return f"{n:,}".replace(",", " ")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Публичный дашборд метрик платформы.
    Доступен всем пользователям включая незарегистрированных.
    """
    # ⚠️ АДАПТИРУЙ: получи analytics_service так же как в других хэндлерах
    # from src.core.services.analytics_service import AnalyticsService
    # stats = await analytics_service.get_platform_stats()

    # Временная заглушка — замени на реальный вызов:
    # stats = await analytics_service.get_platform_stats()

    try:
        # stats = await analytics_service.get_platform_stats()
        # Замени на реальные данные из stats:
        active_channels = 0     # stats.active_channels_count
        total_reach = 0         # stats.total_reach
        launched = 0            # stats.campaigns_launched
        completed = 0           # stats.campaigns_completed
        avg_rating = 0.0        # stats.avg_channel_rating
        paid_out = "0"          # stats.total_paid_out

        success_rate = (
            f"{completed / launched * 100:.0f}%"
            if launched > 0
            else "—"
        )

        text = (
            "📊 <b>RekHarborBot — Статистика платформы</b>\n\n"
            f"📺 Активных каналов: <b>{_format_number(active_channels)}</b>\n"
            f"👥 Суммарный охват: <b>{_format_number(total_reach)}</b> подписчиков\n"
            f"🚀 Кампаний запущено: <b>{_format_number(launched)}</b>\n"
            f"✅ Успешно завершено: <b>{_format_number(completed)}</b> ({success_rate})\n"
            f"⭐ Средний рейтинг каналов: <b>{avg_rating:.1f}</b> / 10\n"
            f"💸 Выплачено владельцам: <b>{paid_out} ₽</b>\n\n"
            "📈 Метрики обновляются ежедневно\n\n"
            "➡️ /start — начать работу с платформой"
        )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Failed to get platform stats: {e}")
        await message.answer(
            "⚠️ Не удалось загрузить статистику. Попробуйте позже."
        )
```

### Шаг 0.4.3 — Зарегистрируй роутер stats

По аналогии с задачей 0.3.5 — добавь `stats_router` в регистрацию.

### Шаг 0.4.4 — Проверка

```powershell
poetry run ruff check src/bot/handlers/stats.py src/core/services/analytics_service.py
poetry run mypy src/bot/handlers/stats.py src/core/services/analytics_service.py \
  --ignore-missing-imports
```

### Коммит 0.4

```powershell
git add src/bot/handlers/stats.py \
        src/core/services/analytics_service.py \
        src/bot/main.py
git commit -m "feat(stats): add /stats command with public platform metrics dashboard"
```

---

## ЗАДАЧА 0.5: FastAPI эндпоинт и Mini App страница

### Шаг 0.5.1 — Добавь FastAPI эндпоинт

```powershell
# Прочитай существующий роутер аналитики
cat src/api/routers/analytics.py
```

Добавь эндпоинт в конец файла (не меняй существующие):

```python
from fastapi import APIRouter
# Остальные импорты из существующего файла

# В конце файла добавить:

@router.get("/stats/public", response_model=PlatformStatsResponse)
async def get_public_stats():
    """
    Публичные метрики платформы.
    Не требует авторизации — доступен для гостей и Mini App без токена.
    """
    # ⚠️ АДАПТИРУЙ под реальную зависимость сессии в этом файле
    # Смотри как другие эндпоинты получают сессию БД
    # stats = await analytics_service.get_platform_stats()

    # Временно возвращаем заглушку — замени на реальный вызов:
    return {
        "active_channels_count": 0,
        "total_reach": 0,
        "campaigns_launched": 0,
        "campaigns_completed": 0,
        "avg_channel_rating": 0.0,
        "total_paid_out": "0.00",
    }
```

Добавь Pydantic-схему ответа (в `src/api/schemas/` или рядом с роутером, как принято в проекте):

```python
from pydantic import BaseModel
from decimal import Decimal

class PlatformStatsResponse(BaseModel):
    active_channels_count: int
    total_reach: int
    campaigns_launched: int
    campaigns_completed: int
    avg_channel_rating: float
    total_paid_out: Decimal
```

### Шаг 0.5.2 — Добавь страницу в Mini App

```powershell
# Изучи структуру Mini App
ls mini_app/src/pages/
cat mini_app/src/pages/[любая существующая страница].tsx | head -50
```

Создай `mini_app/src/pages/PlatformStats.tsx`:

```tsx
/**
 * Публичный дашборд метрик платформы.
 * Доступен без авторизации — для новых пользователей.
 * Спринт 0, задача 0.5.
 */
import { useEffect, useState } from "react";

interface PlatformStats {
  active_channels_count: number;
  total_reach: number;
  campaigns_launched: number;
  campaigns_completed: number;
  avg_channel_rating: number;
  total_paid_out: string;
}

// ⚠️ АДАПТИРУЙ: используй тот же API_BASE_URL что в других страницах проекта
// grep -rn "API_BASE\|apiUrl\|fetch(" mini_app/src/ --include="*.tsx" | head -5
const API_BASE = import.meta.env.VITE_API_URL || "";

export default function PlatformStatsPage() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/stats/public`)
      .then((r) => r.json())
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Не удалось загрузить статистику");
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-4 text-center">Загрузка...</div>;
  if (error) return <div className="p-4 text-center text-red-500">{error}</div>;
  if (!stats) return null;

  const successRate =
    stats.campaigns_launched > 0
      ? ((stats.campaigns_completed / stats.campaigns_launched) * 100).toFixed(0)
      : "—";

  return (
    <div className="p-4 max-w-sm mx-auto">
      <h1 className="text-xl font-bold mb-4 text-center">
        📊 Статистика платформы
      </h1>

      <div className="space-y-3">
        <StatRow label="📺 Активных каналов" value={stats.active_channels_count.toLocaleString("ru")} />
        <StatRow label="👥 Суммарный охват" value={`${stats.total_reach.toLocaleString("ru")} подп.`} />
        <StatRow label="🚀 Кампаний запущено" value={stats.campaigns_launched.toLocaleString("ru")} />
        <StatRow label="✅ Успешно завершено" value={`${stats.campaigns_completed.toLocaleString("ru")} (${successRate}%)`} />
        <StatRow label="⭐ Средний рейтинг" value={`${stats.avg_channel_rating.toFixed(1)} / 10`} />
        <StatRow label="💸 Выплачено владельцам" value={`${stats.total_paid_out} ₽`} />
      </div>

      <p className="text-xs text-gray-400 text-center mt-4">
        Обновляется ежедневно
      </p>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-100">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
```

Добавь маршрут в роутер Mini App (адаптируй под реальный роутер):
```powershell
grep -rn "Route\|path.*=" mini_app/src/App.tsx 2>/dev/null || \
  grep -rn "Route\|path.*=" mini_app/src/main.tsx | head -10
```

### Коммит 0.5

```powershell
git add src/api/routers/analytics.py \
        mini_app/src/pages/PlatformStats.tsx \
        mini_app/src/  # если менял роутер
git commit -m "feat(stats): add FastAPI public stats endpoint and Mini App dashboard page"
```

---

## ЗАДАЧА 0.6: Приветственное сообщение с метриками платформы

### Шаг 0.6.1 — Найди место приветствия

```powershell
cat src/bot/handlers/start.py
```

Найди обработчик `/start` для новых пользователей (обычно после регистрации или при первом входе).

### Шаг 0.6.2 — Добавь метрики в приветствие

Найди место где отправляется приветственное сообщение новому пользователю.
Добавь вызов `get_platform_stats()` и вставь ключевые цифры в текст.

```python
# Пример — адаптируй под реальный обработчик:

# Получить статистику (не блокирует если упадёт)
try:
    stats = await analytics_service.get_platform_stats()
    stats_text = (
        f"\n\n📊 <b>Уже на платформе:</b>\n"
        f"• {stats.active_channels_count} активных каналов\n"
        f"• {stats.total_reach:,} подписчиков суммарного охвата\n"
        f"• {stats.campaigns_launched} кампаний запущено".replace(",", " ")
    )
except Exception:
    stats_text = ""  # Если не удалось — просто не показываем

welcome_text = (
    "👋 <b>Добро пожаловать в RekHarborBot!</b>\n\n"
    "Рекламная биржа в Telegram — весь цикл от подбора каналов "
    "до оплаты и аналитики без выхода из мессенджера."
    + stats_text +
    "\n\n➡️ Нажмите кнопку ниже чтобы начать"
)
```

⚠️ Не меняй структуру существующего `/start` хэндлера — только добавь метрики
в текст приветствия. Если приветствие составное — добавь в подходящее место.

### Шаг 0.6.3 — Проверка

```powershell
poetry run ruff check src/bot/handlers/start.py
poetry run mypy src/bot/handlers/start.py --ignore-missing-imports
```

### Коммит 0.6

```powershell
git add src/bot/handlers/start.py
git commit -m "feat(start): show platform metrics in welcome message for new users"
```

---

## ФИНАЛЬНАЯ ПРОВЕРКА И ОТПРАВКА

### Полный прогон проверок

```powershell
# 1. Линтинг
poetry run ruff check src/
echo "Ruff exit: $?"

# 2. Типизация
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -5

# 3. Миграции
poetry run alembic current
poetry run alembic check 2>&1 | head -3

# 4. Тесты (только стабильные)
poetry run pytest tests/unit/ -v --tb=short -k "not outdated" 2>&1 | tail -15

# 5. Проверка всех 6 коммитов
git log --oneline sprint/0 ^develop
```

Ожидаемый вывод git log — ровно 6 коммитов:
```
feat(start): show platform metrics in welcome message for new users
feat(stats): add FastAPI public stats endpoint and Mini App dashboard page
feat(stats): add /stats command with public platform metrics dashboard
feat(channel-owner): add /add_channel handler with bot admin verification
feat(mailing): filter channels by bot_is_admin and is_accepting_ads
feat(opt-in): add bot_is_admin fields to TelegramChat model and migration
```

### Отправка ветки

```powershell
git push origin sprint/0
```

### Метрики успеха — финальная таблица

| Метрика | Ожидание | Результат |
|---------|----------|-----------|
| Поля в БД | `bot_is_admin`, `admin_added_at`, `owner_user_id`, `price_per_post`, `is_accepting_ads` | |
| Миграция | `alembic current` = head | |
| Фильтр в рассыльщике | Каналы без bot_is_admin не получают рассылку | |
| /add_channel | 5 шагов до активации канала | |
| Верификация getChatMember | Проверяет `status == administrator` и `can_post_messages` | |
| /stats | Отвечает и показывает 6 метрик | |
| FastAPI /stats/public | HTTP 200, валидный JSON | |
| Mini App страница | Рендерится, загружает данные | |
| /start | Показывает метрики для новых пользователей | |
| Ruff | 0 ошибок | |
| Mypy | 0 ошибок | |
| Коммитов в ветке | 6 | |

---

## Итоговый отчёт

После `git push origin sprint/0` предоставь отчёт:

```
══════════════════════════════════════════
 ОТЧЁТ: СПРИНТ 0 — Технический фундамент
══════════════════════════════════════════

Ветка: sprint/0
Коммитов: [N] из 6

ЗАДАЧА 0.1 — Миграция:
  Поля добавлены: [✅/❌]
  Миграция применена: [✅/❌]
  Имя файла миграции: [название]

ЗАДАЧА 0.2 — Фильтр рассыльщика:
  Фильтр добавлен: [✅/❌]
  Файл: [путь]
  Unit тест: [✅ написан / ⚠️ заглушка / ❌]

ЗАДАЧА 0.3 — /add_channel:
  Хэндлер создан: [✅/❌]
  FSM-состояния: [N шагов]
  Сохранение в БД: [✅ реальное / ⚠️ заглушка — почему]
  Регистрация роутера: [✅/❌]

ЗАДАЧА 0.4 — /stats:
  Команда работает: [✅/❌]
  get_platform_stats(): [✅ реальные данные / ⚠️ заглушки — почему]

ЗАДАЧА 0.5 — API + Mini App:
  FastAPI эндпоинт: [✅/❌]
  Mini App страница: [✅/❌]

ЗАДАЧА 0.6 — /start:
  Метрики добавлены: [✅/❌]

Ruff: [✅ 0 ошибок / ❌ N ошибок]
Mypy: [✅ 0 ошибок / ❌ N ошибок]
Тесты: [N passed, N failed]

Нерешённые проблемы:
  [список или "нет"]

Что потребует доработки в Спринте 1:
  [список заглушек которые нужно заменить на реальные вызовы]

PR готов к review: sprint/0 → develop
```
