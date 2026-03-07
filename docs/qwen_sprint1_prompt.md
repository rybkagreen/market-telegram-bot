# Qwen Code Промт: Спринт 1 — Полный цикл владельца канала

## Твоя роль и контекст

Ты реализуешь **Спринт 1** проекта RekHarborBot согласно дорожной карте.

### Обязательная ориентация перед стартом

```powershell
cd ~/python-projects/market-telegram-bot
source .venv/Scripts/activate

# 1. Прочитай дорожную карту — обязательно целиком
cat ROADMAP.md

# 2. Убедись что Спринт 0 завершён и смержен в develop
git log --oneline develop | head -10
# Должны быть все 6 коммитов sprint/0:
# feat(start): show platform metrics in welcome message for new users
# feat(stats): add FastAPI public stats endpoint and Mini App dashboard page
# feat(stats): add /stats command with public platform metrics dashboard
# feat(channel-owner): add /add_channel handler with bot admin verification
# feat(mailing): filter channels by bot_is_admin and is_accepting_ads
# feat(opt-in): add bot_is_admin fields to TelegramChat model and migration

# 3. Если коммиты не найдены — СТОП, уточни у пользователя статус Спринта 0
```

После чтения дорожной карты зафикси письменно:
- Что Спринт 1 добавляет поверх Спринта 0
- Какие поля из Спринта 0 использует (`owner_user_id`, `bot_is_admin`, `is_accepting_ads`)
- Какую зависимость от Спринта 1 имеет Спринт 2 (Review → placements)

---

## Контекст Спринта 1

### Что уже есть после Спринта 0

| Файл / Сущность | Что есть |
|-----------------|----------|
| `TelegramChat` | Поля `bot_is_admin`, `admin_added_at`, `owner_user_id`, `price_per_post`, `is_accepting_ads` |
| `channel_owner.py` | FSM `/add_channel` с верификацией через `getChatMember` |
| `mailing_tasks.py` | Фильтр `bot_is_admin=True AND is_accepting_ads=True` |
| `analytics_service.py` | Метод `get_platform_stats()` |
| `/stats` | Команда бота и FastAPI эндпоинт |

### Что добавляет Спринт 1

Владелец канала получает **полный рабочий цикл**: управление настройками, обработка входящих заявок на рекламу, учёт заработка и базовая система выплат с эскроу-защитой.

**Без Спринта 1 нельзя начинать Спринт 2** — модель `Review` в Спринте 2 обязательно ссылается на `placement_id`, который появляется только в этом спринте.

### Состав Спринта 1

| # | Задача | Тип | Файлы |
|---|--------|-----|-------|
| 1.1 | Модель Payout + миграция | БД | `models/payout.py`, `alembic/versions/` |
| 1.2 | /my_channels и настройки канала | Хэндлер | `handlers/channel_owner.py` |
| 1.3 | Обработка входящих заявок | Хэндлер + Celery | `handlers/channel_owner.py`, `tasks/mailing_tasks.py` |
| 1.4 | Сервис выплат (базовый) | Сервис | `services/payout_service.py` |
| 1.5 | Эскроу-механика | Сервис | `services/billing_service.py` |
| 1.6 | Уведомления владельца | Celery | `tasks/notification_tasks.py` |

---

## ГЛОБАЛЬНЫЕ ПРАВИЛА

1. **Читай файл целиком** перед любым изменением
2. **Проверяй зависимости от Спринта 0** — перед обращением к `owner_user_id` убедись что поле есть в модели
3. **Один коммит на задачу** — строго по плану из дорожной карты
4. **Не трогай** существующую логику рассылки — только расширяй
5. **После каждой задачи** — полный прогон проверок

### Проверки после каждой задачи

```powershell
poetry run ruff check src/
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -3
# Оба: 0 ошибок. Если появились — исправь до следующей задачи.
```

---

## ПОДГОТОВКА: создать ветку

```powershell
git checkout develop
git pull origin develop
git checkout -b sprint/1

# Проверь что ты на правильной ветке и видишь результаты Спринта 0
git log --oneline -8
git status  # должно быть "nothing to commit"
```

---

## ПОДГОТОВКА: разведка структуры

Прежде чем писать код — прочитай ключевые файлы которые будешь расширять.

```powershell
# Структура handlers
ls src/bot/handlers/

# Существующий channel_owner.py от Спринта 0
cat src/bot/handlers/channel_owner.py

# Как устроен billing_service — будем расширять
cat src/core/services/billing_service.py

# Как устроены notification_tasks — будем расширять
cat src/tasks/notification_tasks.py

# Как устроены mailing_tasks — добавим auto_approve
cat src/tasks/mailing_tasks.py

# Модель Campaign — нужно понять как устроены placements
cat src/db/models/campaign.py
grep -rn "placement\|Placement\|mailing_log\|MailingLog" src/db/models/ --include="*.py"
```

Зафикси:
- Есть ли отдельная модель для «размещений» (placement/mailing_log)? Какие у неё поля?
- Как в `billing_service.py` работает списание баланса (какие методы, какие параметры)?
- Как в `notification_tasks.py` отправляются уведомления (через bot.send_message или иначе)?
- Как в `mailing_tasks.py` хранятся Celery-задачи — синхронные или async?

---

## ЗАДАЧА 1.1: Модель Payout и миграция

### Шаг 1.1.1 — Найди модель «размещения»

Модель Payout ссылается на `placement_id`. Сначала найди как называется эта сущность:

```powershell
# Ищем модель размещения (запись о конкретной отправке в конкретный канал)
grep -rn "class.*Placement\|class.*MailingLog\|class.*CampaignLog\|__tablename__" \
  src/db/models/ --include="*.py" | grep -i "placement\|mailing\|log\|send"
```

Запомни: имя таблицы размещений (например, `mailing_logs` или `placements`) —
оно нужно для `ForeignKey` в модели Payout.

### Шаг 1.1.2 — Изучи стиль существующих моделей

```powershell
# Прочитай одну из существующих моделей полностью — возьми за образец
cat src/db/models/transaction.py 2>/dev/null || \
cat src/db/models/campaign.py
```

Зафикси:
- Используется ли `Mapped[...]` (SQLAlchemy 2.0) или старый `Column(...)`
- Как объявляется `id` (autoincrement PK)
- Как импортируется `Base`
- Есть ли `__repr__` и `created_at` как стандартные поля

### Шаг 1.1.3 — Создай модель

**Файл:** `src/db/models/payout.py` (создать)

```python
"""
Модель выплат владельцам каналов.
Спринт 1 — базовая система учёта выплат (80% от цены поста).
Реальная интеграция с CryptoBot добавляется в Спринте 2.
"""
# ⚠️ АДАПТИРУЙ импорты под реальный стиль проекта
# Смотри как импортируется Base в других моделях:
# grep -n "from.*Base\|import.*Base" src/db/models/campaign.py

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

# Используй тот же Base что и в других моделях проекта


class PayoutStatus(str, PyEnum):
    PENDING = "pending"       # начислено, ожидает выплаты
    PROCESSING = "processing" # в процессе перевода
    PAID = "paid"             # выплачено
    FAILED = "failed"         # ошибка выплаты
    CANCELLED = "cancelled"   # отменено (например, при отмене кампании)


class PayoutCurrency(str, PyEnum):
    USDT = "USDT"
    TON = "TON"
    RUB = "RUB"


# ⚠️ АДАПТИРУЙ под реальный стиль (Mapped[...] или Column(...))
# Ниже — пример в стиле SQLAlchemy 2.0 (Mapped)
# Если в проекте используется старый стиль — перепиши соответственно

class Payout(Base):
    """
    Запись о выплате владельцу канала за одно рекламное размещение.
    
    Создаётся автоматически после факта публикации поста.
    80% от цены поста — владельцу, 20% — комиссия платформы.
    """
    __tablename__ = "payouts"

    # ⚠️ Адаптируй объявление id под стиль проекта
    # id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    owner_id: ...  # FK → users.id — внутренний ID владельца
    channel_id: ... # FK → telegram_chats.id
    placement_id: ... # FK → [таблица_размещений].id (найди имя в шаге 1.1.1)
    
    amount: ...        # Numeric(10, 2) — сумма выплаты в рублях (80% от price_per_post)
    platform_fee: ...  # Numeric(10, 2) — комиссия платформы (20%)
    currency: ...      # String(10), default PayoutCurrency.RUB
    status: ...        # String(20), default PayoutStatus.PENDING
    
    # Детали выплаты
    wallet_address: ... # String(200), nullable — адрес кошелька (USDT/TON)
    tx_hash: ...        # String(200), nullable — хэш транзакции после выплаты
    
    # Временные метки
    created_at: ...     # DateTime(timezone=True), default=now
    paid_at: ...        # DateTime(timezone=True), nullable

    # ⚠️ Добавь __repr__ по аналогии с другими моделями проекта
```

⚠️ **Заполни все `...`** — используй реальные типы SQLAlchemy из образцовой модели.
Не оставляй `...` в финальном коде.

### Шаг 1.1.4 — Добавь модель в реестр Alembic

```powershell
# Найди где импортируются модели для Alembic
grep -rn "import.*models\|from.*models" alembic/env.py
grep -rn "models\." alembic/env.py | head -10
```

Добавь импорт `Payout` туда же где импортируются другие модели.

### Шаг 1.1.5 — Создай и проверь миграцию

```powershell
poetry run alembic revision --autogenerate -m "add_payout_model"

# Прочитай сгенерированную миграцию
ls alembic/versions/ | tail -3
cat alembic/versions/[последний_файл].py
```

Убедись что в `upgrade()` создаётся таблица `payouts` со всеми полями.
Убедись что в `downgrade()` таблица удаляется.

```powershell
poetry run alembic upgrade head
poetry run alembic current  # → head
```

### Шаг 1.1.6 — Проверка

```powershell
poetry run ruff check src/db/models/payout.py
poetry run mypy src/db/models/payout.py --ignore-missing-imports
```

### Коммит 1.1

```powershell
git add src/db/models/payout.py alembic/versions/ alembic/env.py
git status
git commit -m "feat(payout): add Payout model and migration"
```

---

## ЗАДАЧА 1.2: /my_channels и управление настройками канала

### Шаг 1.2.1 — Прочитай текущий channel_owner.py

```powershell
cat src/bot/handlers/channel_owner.py
```

Зафикси:
- Какие роутеры и состояния уже объявлены
- Как уже сохраняется канал в БД (если сохранялся) — какой репозиторий используется
- В каком месте файла добавлять новые хэндлеры

### Шаг 1.2.2 — Найди репозиторий каналов

```powershell
# Найди репозиторий для работы с TelegramChat
grep -rn "class.*Chat.*Repo\|TelegramChat\b" \
  src/db/repositories/ --include="*.py" | head -10

# Прочитай найденный репозиторий
cat src/db/repositories/[chat_repo_file].py
```

Зафикси методы которые уже есть:
- Получение канала по telegram_id
- Получение каналов по owner_user_id
- Обновление полей канала

Если метода `get_by_owner` нет — добавишь его ниже.

### Шаг 1.2.3 — Добавь состояния

В `src/bot/states/channel_owner.py` добавь группы состояний для новых флоу:

```python
class EditChannelStates(StatesGroup):
    """Состояния редактирования настроек канала."""
    choosing_setting = State()   # выбор что менять
    waiting_new_price = State()  # ввод новой цены
    choosing_topics = State()    # выбор тематик


class ChannelStates(StatesGroup):
    """Общие состояния для работы с каналами."""
    viewing_channel = State()    # просмотр карточки канала
```

### Шаг 1.2.4 — Добавь хэндлер /my_channels

В `src/bot/handlers/channel_owner.py` добавь в конец файла:

```python
# ─────────────────────────────────────────────
# /my_channels — список каналов владельца
# ─────────────────────────────────────────────

@router.message(Command("my_channels"))
async def cmd_my_channels(message: Message) -> None:
    """
    Список каналов зарегистрированных пользователем.
    Показывает статус, баланс к выплате и быстрые кнопки управления.
    """
    # ⚠️ АДАПТИРУЙ: получи user и его каналы через реальный репозиторий
    # Паттерн из других хэндлеров:
    # async with get_db_session() as session:
    #     user = await user_repo.get_by_telegram_id(session, message.from_user.id)
    #     if user is None:
    #         await message.answer("Зарегистрируйтесь: /start")
    #         return
    #     channels = await chat_repo.get_by_owner_id(session, user.id)

    # Если каналов нет:
    # if not channels:
    #     await message.answer(
    #         "У вас нет зарегистрированных каналов.\n"
    #         "Добавьте канал командой /add_channel"
    #     )
    #     return

    # Для каждого канала строим кнопку:
    # InlineKeyboardButton(
    #     text=f"{'🟢' if ch.is_accepting_ads else '🔴'} @{ch.username} — {ch.price_per_post} ₽",
    #     callback_data=f"channel_menu:{ch.id}",
    # )
    pass  # ← замени на реальную реализацию


@router.callback_query(F.data.startswith("channel_menu:"))
async def show_channel_menu(callback: CallbackQuery) -> None:
    """
    Меню управления конкретным каналом.
    Показывает статистику и кнопки действий.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    # ⚠️ АДАПТИРУЙ: получи канал и баланс выплат
    # channel = await chat_repo.get_by_id(session, channel_id)
    # pending_payout = await payout_service.get_owner_balance(channel.owner_user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"ch_settings:{channel_id}"),
            InlineKeyboardButton(text="📊 Аналитика", callback_data=f"ch_analytics:{channel_id}"),
        ],
        [
            InlineKeyboardButton(text="📋 Заявки", callback_data=f"ch_requests:{channel_id}"),
            InlineKeyboardButton(text="💰 Выплаты", callback_data=f"ch_payouts:{channel_id}"),
        ],
        [
            # Кнопка переключает is_accepting_ads
            InlineKeyboardButton(
                text="🔴 Отключить рекламу",  # или 🟢 Включить — в зависимости от статуса
                callback_data=f"ch_toggle:{channel_id}",
            ),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_channels_back")],
    ])

    # ⚠️ Подставь реальные данные канала
    await safe_callback_edit(
        callback.message,
        f"📺 <b>@channel_username</b>\n\n"
        f"👥 Подписчиков: N\n"
        f"💰 Цена за пост: X ₽\n"
        f"📈 Размещений всего: N\n"
        f"💸 К выплате: X ₽\n"
        f"{'🟢 Принимает рекламу' if True else '🔴 Реклама отключена'}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("ch_settings:"))
async def show_channel_settings(callback: CallbackQuery) -> None:
    """Меню настроек канала."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"ch_edit_price:{channel_id}")],
        [InlineKeyboardButton(text="🏷 Изменить тематики", callback_data=f"ch_edit_topics:{channel_id}")],
        [InlineKeyboardButton(text="⚡ Режим одобрения", callback_data=f"ch_edit_approval:{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"channel_menu:{channel_id}")],
    ])

    await safe_callback_edit(
        callback.message,
        "⚙️ <b>Настройки канала</b>\n\nЧто хотите изменить?",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("ch_toggle:"))
async def toggle_accepting_ads(callback: CallbackQuery) -> None:
    """Переключить статус приёма рекламы."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    # ⚠️ АДАПТИРУЙ: переключи is_accepting_ads и сохрани
    # channel = await chat_repo.get_by_id(session, channel_id)
    # new_status = not channel.is_accepting_ads
    # await chat_repo.update_field(session, channel_id, "is_accepting_ads", new_status)
    # status_text = "включена" if new_status else "отключена"

    await callback.answer("Статус обновлён")
    # Обнови меню канала
    await show_channel_menu(callback)
```

⚠️ Все места с `# ⚠️ АДАПТИРУЙ` — обязательны к заполнению реальным кодом.
Не оставляй `pass` в финальном коде. После заполнения удали `pass`.

### Шаг 1.2.5 — Добавь метод в репозиторий если нужно

Если метода `get_by_owner_id` нет в репозитории каналов:

```powershell
# Проверь
grep -n "def get_by_owner\|owner_user_id" src/db/repositories/ -r --include="*.py"
```

Если нет — добавь в репозиторий:

```python
async def get_by_owner_id(self, owner_user_id: int) -> list[TelegramChat]:
    """Получить все каналы зарегистрированные данным пользователем."""
    result = await self.session.execute(
        select(TelegramChat).where(
            TelegramChat.owner_user_id == owner_user_id
        ).order_by(TelegramChat.created_at.desc())
    )
    return list(result.scalars().all())
```

### Шаг 1.2.6 — Проверка

```powershell
poetry run ruff check src/bot/handlers/channel_owner.py
poetry run mypy src/bot/handlers/channel_owner.py --ignore-missing-imports
```

### Коммит 1.2

```powershell
git add src/bot/handlers/channel_owner.py \
        src/bot/states/channel_owner.py \
        src/db/repositories/
git status
git commit -m "feat(channel-owner): add /my_channels and channel settings management"
```

---

## ЗАДАЧА 1.3: Обработка входящих заявок на размещение

### Шаг 1.3.1 — Найди модель размещения

```powershell
# Найди существующую модель для записей о рассылке в конкретный канал
grep -rn "class.*MailingLog\|class.*Placement\|class.*CampaignChat" \
  src/db/models/ --include="*.py"

# Прочитай её целиком
cat src/db/models/mailing_log.py 2>/dev/null || \
cat src/db/models/[найденный_файл].py
```

Зафикси:
- Имя модели и таблицы
- Поля статуса (PENDING, SENT, FAILED, ...)
- Есть ли поле для хранения «ожидает одобрения владельца»?

### Шаг 1.3.2 — Добавь статус «ожидает одобрения» если нужно

Если в модели размещения нет статуса `PENDING_APPROVAL` — добавь:

```powershell
# Проверь текущие статусы
grep -n "class.*Status\|PENDING\|SENT\|QUEUED\|WAITING" \
  src/db/models/mailing_log.py 2>/dev/null || \
grep -rn "class.*Status" src/db/models/ --include="*.py"
```

Если нужен новый статус — добавь в enum модели:
```python
PENDING_APPROVAL = "pending_approval"  # ожидает одобрения владельца
REJECTED = "rejected"                  # отклонено владельцем
```

Создай миграцию если меняешь enum в PostgreSQL:
```powershell
poetry run alembic revision --autogenerate -m "add_pending_approval_status"
poetry run alembic upgrade head
```

### Шаг 1.3.3 — Хэндлер обработки заявок (одобрение/отклонение)

В `src/bot/handlers/channel_owner.py` добавь:

```python
# ─────────────────────────────────────────────
# Обработка входящих заявок на размещение
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("approve_placement:"))
async def approve_placement(callback: CallbackQuery) -> None:
    """
    Владелец канала одобряет заявку на размещение.
    Переводит размещение в статус QUEUED для исполнения рассыльщиком.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])

    try:
        # ⚠️ АДАПТИРУЙ: обнови статус размещения
        # async with get_db_session() as session:
        #     placement = await placement_repo.get_by_id(session, placement_id)
        #     if placement is None:
        #         await callback.answer("Заявка не найдена", show_alert=True)
        #         return
        #     if placement.status != PlacementStatus.PENDING_APPROVAL:
        #         await callback.answer("Заявка уже обработана", show_alert=True)
        #         return
        #     await placement_repo.update_status(session, placement_id, PlacementStatus.QUEUED)

        await safe_callback_edit(
            callback.message,
            "✅ <b>Заявка одобрена!</b>\n\n"
            "Пост будет опубликован в согласованное время.\n"
            "После публикации вы получите уведомление и выплата будет начислена.",
            parse_mode="HTML",
        )
        await callback.answer("Заявка одобрена")

    except Exception as e:
        logger.error(f"Failed to approve placement {placement_id}: {e}")
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("reject_placement:"))
async def reject_placement(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Владелец канала отклоняет заявку.
    Средства рекламодателя размораживаются и возвращаются на баланс.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])

    # ⚠️ АДАПТИРУЙ:
    # 1. Обновить статус размещения → REJECTED
    # 2. Вернуть замороженные средства рекламодателю (billing_service.refund_frozen_funds)
    # 3. Уведомить рекламодателя об отклонении

    await safe_callback_edit(
        callback.message,
        "❌ <b>Заявка отклонена</b>\n\n"
        "Средства рекламодателя будут возвращены на его баланс.",
        parse_mode="HTML",
    )
    await callback.answer("Заявка отклонена")
```

### Шаг 1.3.4 — Задача автоодобрения в Celery

В `src/tasks/mailing_tasks.py` добавь в конец файла:

```python
# ─────────────────────────────────────────────
# Задача автоодобрения заявок (Спринт 1)
# ─────────────────────────────────────────────

@celery_app.task(name="mailing:auto_approve_pending_placements")
def auto_approve_pending_placements() -> dict:
    """
    Автоматически одобряет заявки которые не получили ответа от владельца за 24 часа.
    Запускается каждый час через Celery Beat.
    
    Логика:
    - Найти все размещения в статусе PENDING_APPROVAL
    - Если created_at + 24ч < now() → перевести в QUEUED
    """
    import asyncio
    from datetime import datetime, timezone, timedelta

    # ⚠️ АДАПТИРУЙ под реальную структуру Celery-задач в проекте
    # Смотри как другие задачи в этом файле работают с БД
    # Паттерн: используй тот же способ получения sync/async сессии что уже есть
    
    deadline = datetime.now(timezone.utc) - timedelta(hours=24)
    approved_count = 0
    failed_count = 0

    try:
        # Найди все PENDING_APPROVAL размещения старше 24 часов
        # placements = placement_repo.get_pending_older_than(deadline)
        # for placement in placements:
        #     try:
        #         placement_repo.update_status(placement.id, PlacementStatus.QUEUED)
        #         approved_count += 1
        #     except Exception as e:
        #         logger.error(f"Auto-approve failed for placement {placement.id}: {e}")
        #         failed_count += 1
        pass  # ← замени

    except Exception as e:
        logger.error(f"auto_approve_pending_placements failed: {e}")
        return {"status": "error", "error": str(e)}

    return {
        "status": "ok",
        "approved": approved_count,
        "failed": failed_count,
    }
```

### Шаг 1.3.5 — Добавь задачу в Beat-расписание

```powershell
cat src/tasks/celery_config.py
```

Добавь в `beat_schedule`:

```python
"auto-approve-pending-placements": {
    "task": "mailing:auto_approve_pending_placements",
    "schedule": crontab(minute=0),  # каждый час
},
```

### Шаг 1.3.6 — Функция уведомления владельца о новой заявке

В `src/tasks/notification_tasks.py` найди как отправляются уведомления
и добавь функцию уведомления о новой заявке:

```python
async def notify_owner_new_placement(placement_id: int) -> None:
    """
    Уведомляет владельца канала о новой заявке на размещение.
    Отправляет текст объявления, сумму выплаты, дату публикации и кнопки одобрения.
    """
    # ⚠️ АДАПТИРУЙ: получи данные размещения и канала, отправь сообщение
    # placement = await placement_repo.get_by_id(placement_id)
    # channel = await chat_repo.get_by_id(placement.channel_id)
    # campaign = await campaign_repo.get_by_id(placement.campaign_id)
    # owner = await user_repo.get_by_id(channel.owner_user_id)
    
    # payout_amount = placement.price_per_post * Decimal("0.8")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"approve_placement:{placement_id}",
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"reject_placement:{placement_id}",
        ),
    ]])
    
    # await bot.send_message(
    #     chat_id=owner.telegram_id,
    #     text=(
    #         f"📢 <b>Новая заявка на размещение в @{channel.username}</b>\n\n"
    #         f"💬 Текст объявления:\n{campaign.text[:500]}\n\n"
    #         f"📅 Дата публикации: {placement.scheduled_at:%d.%m.%Y %H:%M}\n"
    #         f"💸 Выплата: {payout_amount:.0f} ₽\n\n"
    #         f"⏰ Автоодобрение через 24 часа если не ответите"
    #     ),
    #     reply_markup=keyboard,
    #     parse_mode="HTML",
    # )
    pass  # ← замени на реальную реализацию
```

### Проверка

```powershell
poetry run ruff check src/bot/handlers/channel_owner.py src/tasks/
poetry run mypy src/bot/handlers/channel_owner.py src/tasks/ --ignore-missing-imports
```

### Коммит 1.3

```powershell
git add src/bot/handlers/channel_owner.py \
        src/tasks/mailing_tasks.py \
        src/tasks/notification_tasks.py \
        src/tasks/celery_config.py \
        src/db/models/  # если менял enum статусов
git status
git commit -m "feat(channel-owner): add placement approval flow and auto-approve task"
```

---

## ЗАДАЧА 1.4: Сервис выплат (базовый)

### Шаг 1.4.1 — Создай сервис

**Файл:** `src/core/services/payout_service.py` (создать)

```powershell
# Изучи как устроены другие сервисы — возьми за образец
cat src/core/services/billing_service.py | head -60
```

```python
"""
Сервис управления выплатами владельцам каналов.

Спринт 1: базовая логика учёта (создание Payout, подсчёт баланса).
Реальная интеграция выплат с CryptoBot — в Спринте 2.

Бизнес-правило: владелец получает 80% от price_per_post, 20% — комиссия платформы.
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# Комиссия платформы
PLATFORM_FEE_RATE = Decimal("0.20")   # 20%
OWNER_SHARE_RATE = Decimal("0.80")    # 80%


class PayoutService:
    """Сервис выплат владельцам каналов."""

    # ⚠️ АДАПТИРУЙ: используй тот же способ инжекции зависимостей
    # что используют другие сервисы в проекте
    # Смотри: как BillingService получает session и репозитории

    def calculate_payout_amount(self, price_per_post: Decimal) -> tuple[Decimal, Decimal]:
        """
        Рассчитать суммы выплаты и комиссии.
        
        Returns:
            (owner_amount, platform_fee) — оба в той же валюте что price_per_post
        """
        owner_amount = (price_per_post * OWNER_SHARE_RATE).quantize(Decimal("0.01"))
        platform_fee = (price_per_post * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
        return owner_amount, platform_fee

    async def create_pending_payout(
        self,
        placement_id: int,
        owner_id: int,
        channel_id: int,
        price_per_post: Decimal,
        currency: str = "RUB",
    ) -> "Payout":
        """
        Создать запись о выплате после факта публикации.
        Статус: PENDING — ожидает перевода.
        
        Вызывается из billing_service.release_funds_for_placement().
        """
        owner_amount, platform_fee = self.calculate_payout_amount(price_per_post)

        # ⚠️ АДАПТИРУЙ: сохрани Payout через репозиторий
        # payout = Payout(
        #     owner_id=owner_id,
        #     channel_id=channel_id,
        #     placement_id=placement_id,
        #     amount=owner_amount,
        #     platform_fee=platform_fee,
        #     currency=currency,
        #     status=PayoutStatus.PENDING,
        # )
        # await self.session.add(payout)
        # await self.session.commit()
        # return payout
        pass  # ← замени

    async def get_owner_balance(self, owner_id: int) -> Decimal:
        """
        Получить суммарный баланс к выплате для владельца.
        Считает только Payout в статусе PENDING.
        """
        # ⚠️ АДАПТИРУЙ: SQL-запрос через репозиторий
        # result = await self.session.execute(
        #     select(func.sum(Payout.amount)).where(
        #         Payout.owner_id == owner_id,
        #         Payout.status == PayoutStatus.PENDING,
        #     )
        # )
        # return result.scalar() or Decimal("0")
        return Decimal("0")  # ← замени

    async def process_payout(self, payout_id: int) -> None:
        """
        Заглушка для реального перевода выплаты.
        
        В Спринте 1: только логирование запроса.
        В Спринте 2: реальная интеграция с CryptoBot API.
        """
        logger.info(
            f"Payout {payout_id} requested for processing. "
            "Real transfer will be implemented in Sprint 2."
        )
        # Пока только меняем статус на PROCESSING
        # ⚠️ АДАПТИРУЙ: обнови статус Payout
        # await payout_repo.update_status(payout_id, PayoutStatus.PROCESSING)
```

### Шаг 1.4.2 — Добавь Celery задачу проверки выплат

В `src/tasks/billing_tasks.py` добавь:

```python
@celery_app.task(name="billing:check_pending_payouts")
def check_pending_payouts() -> dict:
    """
    Еженедельная задача: проверить PENDING выплаты и логировать суммы.
    В Спринте 1 — только отчёт. В Спринте 2 — реальные переводы.
    """
    # ⚠️ АДАПТИРУЙ под стиль задач в файле
    # pending = payout_repo.get_by_status(PayoutStatus.PENDING)
    # total_amount = sum(p.amount for p in pending)
    # logger.info(f"Pending payouts: {len(pending)}, total: {total_amount}")
    return {"status": "ok", "pending_count": 0, "total_amount": "0"}
```

Добавь в Beat-расписание:
```python
"check-pending-payouts": {
    "task": "billing:check_pending_payouts",
    "schedule": crontab(day_of_week=1, hour=9, minute=0),  # понедельник 09:00
},
```

### Шаг 1.4.3 — Unit тесты для PayoutService

**Файл:** `tests/unit/test_payout_service.py` (создать)

```python
"""Unit тесты для PayoutService."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

# ⚠️ АДАПТИРУЙ импорт под реальный путь
from src.core.services.payout_service import PayoutService, OWNER_SHARE_RATE, PLATFORM_FEE_RATE


class TestPayoutCalculation:
    """Тесты расчёта суммы выплаты."""

    def setup_method(self):
        # ⚠️ АДАПТИРУЙ: создай экземпляр сервиса с mock сессией
        self.service = PayoutService()  # адаптируй если нужны аргументы

    def test_calculate_payout_amount_standard(self):
        """Стандартный расчёт: 1000 ₽ → 800 ₽ владельцу, 200 ₽ платформе."""
        owner, fee = self.service.calculate_payout_amount(Decimal("1000"))
        assert owner == Decimal("800.00")
        assert fee == Decimal("200.00")
        assert owner + fee == Decimal("1000.00")

    def test_calculate_payout_amount_zero(self):
        """Нулевая цена → нулевые суммы."""
        owner, fee = self.service.calculate_payout_amount(Decimal("0"))
        assert owner == Decimal("0.00")
        assert fee == Decimal("0.00")

    def test_calculate_payout_rounding(self):
        """Проверка округления до копеек."""
        owner, fee = self.service.calculate_payout_amount(Decimal("333.33"))
        # 333.33 * 0.80 = 266.664 → 266.66
        # 333.33 * 0.20 = 66.666 → 66.67
        assert len(str(owner).split(".")[-1]) <= 2
        assert len(str(fee).split(".")[-1]) <= 2

    def test_owner_share_rate(self):
        """Константы долей совпадают с бизнес-правилом PRD §3.2."""
        assert OWNER_SHARE_RATE == Decimal("0.80")
        assert PLATFORM_FEE_RATE == Decimal("0.20")
        assert OWNER_SHARE_RATE + PLATFORM_FEE_RATE == Decimal("1.00")
```

```powershell
poetry run pytest tests/unit/test_payout_service.py -v
```

### Проверка

```powershell
poetry run ruff check src/core/services/payout_service.py src/tasks/billing_tasks.py
poetry run mypy src/core/services/payout_service.py src/tasks/billing_tasks.py \
  --ignore-missing-imports
```

### Коммит 1.4

```powershell
git add src/core/services/payout_service.py \
        src/tasks/billing_tasks.py \
        src/tasks/celery_config.py \
        tests/unit/test_payout_service.py
git commit -m "feat(payout): add payout_service with calculation logic and pending check task"
```

---

## ЗАДАЧА 1.5: Эскроу-механика

### Шаг 1.5.1 — Прочитай billing_service целиком

```powershell
cat src/core/services/billing_service.py
```

Зафикси:
- Как хранится баланс пользователя (поле `credits`, `balance` или другое?)
- Есть ли поле для «замороженных» средств в модели User или Campaign?
- Как текущие методы работают с транзакциями (Transaction модель?)

### Шаг 1.5.2 — Проверь нужно ли поле frozen_amount

```powershell
grep -n "frozen\|escrow\|locked\|reserve" src/db/models/user.py src/db/models/campaign.py
```

Если поля `frozen_amount` нет в User или Campaign — добавить его:

**Вариант А** — добавить `frozen_amount` в User:
```python
frozen_amount: Mapped[Decimal] = mapped_column(
    Numeric(10, 2), default=0, nullable=False, server_default="0"
)
```

**Вариант Б** — хранить статус замороженных средств в Campaign:
```python
frozen_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
is_funds_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

Обсуди с пользователем какой вариант предпочтительнее если неясно.
После выбора — создай миграцию.

### Шаг 1.5.3 — Добавь методы эскроу в BillingService

В `src/core/services/billing_service.py` добавь методы (не меняй существующие):

```python
async def freeze_funds(self, user_id: int, campaign_id: int, amount: Decimal) -> bool:
    """
    Заморозить средства рекламодателя при запуске кампании.
    
    Логика:
    1. Проверить что на балансе достаточно средств
    2. Списать amount с доступного баланса
    3. Добавить amount к frozen_amount
    4. Записать транзакцию типа FREEZE
    5. Обновить campaign.is_funds_frozen = True
    
    Returns:
        True если заморозка успешна, False если недостаточно средств
    """
    # ⚠️ АДАПТИРУЙ: используй реальные поля модели User и Transaction
    # user = await user_repo.get_by_id(user_id)
    # if user.credits < amount:  # или user.balance < amount
    #     return False
    #
    # await user_repo.update_balance(user_id, delta=-amount)
    # await user_repo.update_frozen(user_id, delta=+amount)
    # await transaction_repo.create(
    #     user_id=user_id,
    #     amount=-amount,
    #     type=TransactionType.FREEZE,
    #     meta_json={"campaign_id": campaign_id},
    # )
    # return True
    logger.warning("freeze_funds not yet implemented — placeholder in Sprint 1")
    return True  # ← замени на реальную реализацию

async def release_funds_for_placement(
    self,
    placement_id: int,
    owner_id: int,
    channel_id: int,
    amount: Decimal,
) -> None:
    """
    Разморозить средства после факта публикации.
    Создаёт Payout для владельца канала.
    
    Вызывается рассыльщиком после успешной публикации поста.
    """
    # ⚠️ АДАПТИРУЙ:
    # 1. Уменьшить frozen_amount пользователя на amount
    # 2. Записать транзакцию типа SPEND
    # 3. Вызвать payout_service.create_pending_payout(...)
    # 4. Уведомить владельца о начисленной выплате
    logger.info(
        f"Releasing funds for placement {placement_id}: "
        f"{amount} to owner {owner_id} via channel {channel_id}"
    )

async def refund_frozen_funds(self, placement_id: int, user_id: int, amount: Decimal) -> None:
    """
    Вернуть замороженные средства рекламодателю.
    
    Вызывается если публикация не состоялась в течение 48 часов
    или если владелец отклонил заявку.
    """
    # ⚠️ АДАПТИРУЙ:
    # 1. Уменьшить frozen_amount на amount
    # 2. Увеличить доступный баланс на amount
    # 3. Записать транзакцию типа REFUND
    # 4. Уведомить рекламодателя о возврате
    logger.info(f"Refunding {amount} to user {user_id} for placement {placement_id}")
```

### Шаг 1.5.4 — Unit тесты эскроу

В `tests/unit/test_payout_service.py` добавь:

```python
class TestEscrowLogic:
    """Тесты эскроу-механики."""

    @pytest.mark.asyncio
    async def test_freeze_reduces_available_balance(self):
        """После заморозки доступный баланс уменьшается."""
        # ⚠️ АДАПТИРУЙ: создай mock для user_repo и billing_service
        # Проверь что после freeze_funds(user_id, campaign_id, 500)
        # user.available_balance уменьшился на 500
        pass

    @pytest.mark.asyncio
    async def test_freeze_fails_if_insufficient_balance(self):
        """Заморозка невозможна если средств недостаточно."""
        # result = await billing_service.freeze_funds(user_id=1, campaign_id=1, amount=Decimal("99999"))
        # assert result == False
        pass

    @pytest.mark.asyncio
    async def test_release_creates_payout(self):
        """release_funds_for_placement создаёт Payout в статусе PENDING."""
        # ⚠️ Проверь что после release создан Payout с нужными полями
        pass
```

⚠️ Не оставляй тесты с `pass` — реализуй хотя бы базовые проверки с mock объектами.

### Проверка

```powershell
poetry run ruff check src/core/services/billing_service.py
poetry run mypy src/core/services/billing_service.py --ignore-missing-imports
poetry run pytest tests/unit/test_payout_service.py -v
```

### Коммит 1.5

```powershell
git add src/core/services/billing_service.py \
        src/db/models/ \
        alembic/versions/ \
        tests/unit/test_payout_service.py
git commit -m "feat(billing): add escrow freeze/release/refund to billing_service"
```

---

## ЗАДАЧА 1.6: Уведомления для владельца канала

### Шаг 1.6.1 — Изучи существующие уведомления

```powershell
cat src/tasks/notification_tasks.py
```

Зафикси:
- Как задача получает экземпляр `bot` (через контекст Celery или явно?)
- Как получается `telegram_id` пользователя для отправки
- Есть ли вспомогательная функция `send_notification(user_id, text)`?

### Шаг 1.6.2 — Добавь три функции уведомлений

В `src/tasks/notification_tasks.py` добавь:

```python
# ─────────────────────────────────────────────
# Уведомления для владельцев каналов (Спринт 1)
# ─────────────────────────────────────────────

@celery_app.task(name="notifications:notify_owner_new_placement")
def notify_owner_new_placement(placement_id: int) -> None:
    """
    Уведомить владельца о новой заявке на размещение.
    Вызывается сразу после создания заявки в mailing_tasks.
    """
    # ⚠️ АДАПТИРУЙ: используй существующий паттерн отправки уведомлений
    # Содержимое: текст объявления, сумма выплаты, дата публикации, кнопки одобрения
    # Кнопки: approve_placement:{placement_id} и reject_placement:{placement_id}
    pass  # ← замени


@celery_app.task(name="notifications:notify_owner_payout_created")
def notify_owner_payout_created(payout_id: int) -> None:
    """
    Уведомить владельца что выплата начислена после публикации.
    Вызывается из billing_service.release_funds_for_placement().
    """
    # ⚠️ АДАПТИРУЙ
    # Содержимое: сумма выплаты, канал, дата поступления
    pass  # ← замени


@celery_app.task(name="notifications:remind_owner_pending_placement")
def remind_owner_pending_placement(placement_id: int) -> None:
    """
    Напомнить владельцу об ожидающей заявке за 4 часа до автоодобрения.
    Задача планируется при создании заявки с eta = created_at + 20h.
    """
    # ⚠️ АДАПТИРУЙ
    # Проверить что статус всё ещё PENDING_APPROVAL перед отправкой
    # Содержимое: текст «Заявка автоматически одобрится через 4 часа»
    pass  # ← замени
```

### Шаг 1.6.3 — Подключи уведомления к событиям

Найди место в `mailing_tasks.py` где создаётся новое размещение (placement).
После создания добавь вызов уведомления:

```python
# После создания placement:
from src.tasks.notification_tasks import notify_owner_new_placement, remind_owner_pending_placement

notify_owner_new_placement.delay(placement_id)

# Запланировать напоминание через 20 часов (за 4 ч до дедлайна)
from datetime import datetime, timezone, timedelta
reminder_eta = datetime.now(timezone.utc) + timedelta(hours=20)
remind_owner_pending_placement.apply_async(
    args=[placement_id],
    eta=reminder_eta,
)
```

### Проверка

```powershell
poetry run ruff check src/tasks/notification_tasks.py
poetry run mypy src/tasks/notification_tasks.py --ignore-missing-imports
```

### Коммит 1.6

```powershell
git add src/tasks/notification_tasks.py src/tasks/mailing_tasks.py
git commit -m "feat(notifications): add owner placement and payout notification tasks"
```

---

## ФИНАЛЬНАЯ ПРОВЕРКА И ОТПРАВКА

### Полный прогон

```powershell
# 1. Линтинг — обязательно 0 ошибок
poetry run ruff check src/ tests/
echo "Ruff exit: $?"

# 2. Типизация — обязательно 0 ошибок
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -5

# 3. Миграции
poetry run alembic current
poetry run alembic check 2>&1 | head -3

# 4. Тесты
poetry run pytest tests/unit/ -v --tb=short 2>&1 | tail -20

# 5. Ровно 6 коммитов в ветке
git log --oneline sprint/1 ^develop
```

Ожидаемый вывод git log:
```
feat(notifications): add owner placement and payout notification tasks
feat(billing): add escrow freeze/release/refund to billing_service
feat(payout): add payout_service with calculation logic and pending check task
feat(channel-owner): add placement approval flow and auto-approve task
feat(channel-owner): add /my_channels and channel settings management
feat(payout): add Payout model and migration
```

### Заполнение PR-шаблона

```powershell
# Список изменённых файлов для описания PR
git diff --name-only develop sprint/1
```

### Отправка

```powershell
git push origin sprint/1
```

---

## Итоговый отчёт

```
══════════════════════════════════════════
 ОТЧЁТ: СПРИНТ 1 — Полный цикл владельца
══════════════════════════════════════════

Ветка: sprint/1
Предыдущий спринт смержен: [✅/❌]

ЗАДАЧА 1.1 — Модель Payout:
  Создана: [✅/❌]
  Поля: [список реальных полей]
  Миграция: [имя файла, alembic current = head ✅/❌]

ЗАДАЧА 1.2 — /my_channels:
  Команда работает: [✅/❌]
  Настройки (цена, тематики, вкл/выкл): [✅ все / ⚠️ частично — что не готово]
  Метод get_by_owner_id в репозитории: [✅ был / ✅ добавлен / ❌]

ЗАДАЧА 1.3 — Обработка заявок:
  Одобрение/отклонение: [✅/❌]
  Статус PENDING_APPROVAL: [✅ был / ✅ добавлен / ❌]
  auto_approve_pending_placements: [✅ в Beat-расписании / ❌]
  notify_owner_new_placement вызывается при создании: [✅/❌]

ЗАДАЧА 1.4 — PayoutService:
  calculate_payout_amount: [✅ реальный / ❌]
  create_pending_payout: [✅ реальный / ⚠️ заглушка — почему]
  get_owner_balance: [✅ реальный / ⚠️ заглушка]
  Unit тесты calculate: [N passed]

ЗАДАЧА 1.5 — Эскроу:
  freeze_funds: [✅ реальный / ⚠️ заглушка — почему]
  release_funds_for_placement: [✅ реальный / ⚠️ заглушка]
  refund_frozen_funds: [✅ реальный / ⚠️ заглушка]
  frozen_amount в модели: [✅ было / ✅ добавлено / ⚠️ не реализовано — почему]

ЗАДАЧА 1.6 — Уведомления:
  notify_owner_new_placement: [✅ реальный / ⚠️ заглушка]
  notify_owner_payout_created: [✅ реальный / ⚠️ заглушка]
  remind_owner_pending_placement: [✅ с eta / ⚠️ заглушка]

Ruff: [✅ 0 / ❌ N]
Mypy: [✅ 0 / ❌ N]
Тесты: [N passed, N failed]
Коммитов в ветке: [N] из 6

Заглушки требующие доработки в Спринте 2:
  [список — будут первыми задачами следующего спринта]

PR готов: sprint/1 → develop
```
