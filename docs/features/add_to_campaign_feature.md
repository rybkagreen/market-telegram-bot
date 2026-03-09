# 📋 ПЛАН РЕАЛИЗАЦИИ: Кнопка "Добавить в кампанию"

**Файл:** `docs/features/add_to_campaign_feature.md`  
**Приоритет:** P2 (средний)  
**Оценка:** 2-3 дня  
**Зависимости:** Спринт 4 (визард создания кампании), Спринт 8 (детальная страница канала)

---

## 🎯 ОПИСАНИЕ ФУНКЦИИ

Кнопка **"📋 Добавить в кампанию"** на детальной странице канала позволяет пользователю быстро создать новую кампанию с предвыбранным каналом.

**User Story:**
> Как рекламодатель, я хочу быстро выбрать конкретный канал для размещения рекламы, чтобы не искать его вручную в каталоге при создании кампании.

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ

### Что есть:
- ✅ Детальная страница канала (`view_channel_detail`)
- ✅ Кнопка "📋 Добавить в кампанию" в клавиатуре
- ✅ Callback: `ChannelsCB(action="add_to_campaign", value=str(channel_id))`

### Чего нет:
- ❌ Handler для обработки callback
- ❌ Логика проверки прав пользователя
- ❌ Интеграция с визардом создания кампании
- ❌ Предзаполнение данных кампании

---

## 🏗 АРХИТЕКТУРА РЕШЕНИЯ

```
┌─────────────────────────────────────────────────────────────┐
│  Детальная страница канала                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📡 Канал: @example                                    │  │
│  │ 👥 Подписчиков: 10,000                                │  │
│  │ 💰 Цена: 500 кр / пост                                │  │
│  │                                                       │  │
│  │ [📋 Добавить в кампанию]  ← НАЖАТИЕ                   │  │
│  │ [🔙 Назад к каталогу]                                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Handler: add_channel_to_campaign()                         │
│  1. Проверить права пользователя (рекламодатель)            │
│  2. Проверить тариф (не FREE)                               │
│  3. Получить данные канала из БД                            │
│  4. Сохранить channel_id в FSM state                        │
│  5. Перейти на шаг wizard'а                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Campaign Wizard (модифицированный)                         │
│  Шаг 1: Тема → Авто: тема канала                            │
│  Шаг 2: Заголовок → Ввод пользователем                      │
│  Шаг 3: Текст → Ввод пользователем / AI                     │
│  Шаг 4: Каналы → Авто: выбранный канал ✅                   │
│  Шаг 5: Бюджет → Авто: цена канала × 1                      │
│  Шаг 6: Подтверждение → Запуск                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 ПОШАГОВЫЙ ПЛАН РЕАЛИЗАЦИИ

### Этап 1: Handler для кнопки (1-2 часа)

**Файл:** `src/bot/handlers/channels_db.py`

```python
@router.callback_query(ChannelsCB.filter(F.action == "add_to_campaign"))
async def add_channel_to_campaign(
    callback: CallbackQuery,
    callback_data: ChannelsCB,
    state: FSMContext,
) -> None:
    """
    Начать создание кампании с предвыбранным каналом.
    """
    channel_id = int(callback_data.value)
    
    # 1. Проверить пользователя
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # 2. Проверить тариф
        if user.plan == UserPlan.FREE:
            await callback.answer(
                "❌ На тарифе FREE создание кампаний недоступно\n"
                "Перейдите в Кабинет → Сменить тариф",
                show_alert=True,
            )
            return
        
        # 3. Проверить лимит кампаний
        campaign_repo = CampaignRepository(session)
        campaign_count = await campaign_repo.get_user_campaigns_count(user.id)
        campaign_limit = user.get_campaign_limit()
        
        if campaign_count >= campaign_limit:
            await callback.answer(
                f"❌ Превышен лимит кампаний: {campaign_count}/{campaign_limit}\n"
                "Завершите текущие кампании или смените тариф",
                show_alert=True,
            )
            return
        
        # 4. Получить данные канала
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return
        
        # 5. Проверить что канал принимает рекламу
        if not channel.is_accepting_ads:
            await callback.answer(
                "⚠️ Этот канал временно не принимает рекламу",
                show_alert=True,
            )
            return
        
        # 6. Сохранить в state
        await state.update_data(
            preselected_channel_id=channel_id,
            preselected_channel_username=channel.username,
            preselected_channel_price=channel.price_per_post,
            preselected_channel_topic=channel.topic,
        )
    
    # 7. Показать приветственное сообщение
    text = (
        f"✅ <b>Канал выбран!</b>\n\n"
        f"📡 @{channel.username}\n"
        f"💰 Цена за пост: {channel.price_per_post} кр\n\n"
        f"Теперь создайте кампанию:\n"
        f"1. Введите заголовок\n"
        f"2. Введите текст\n"
        f"3. Подтвердите запуск\n\n"
        f"Канал будет автоматически добавлен в список для рассылки."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать создание", callback_data="start_campaign_with_channel")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=ChannelsCB(action="categories"))],
    ])
    
    await safe_callback_edit(callback, text, reply_markup=keyboard)
```

---

### Этап 2: Модификация визарда (3-4 часа)

**Файл:** `src/bot/handlers/campaigns.py`

#### 2.1 Добавить шаг "Подтверждение канала"

```python
@router.callback_query(F.data == "start_campaign_with_channel")
async def start_campaign_with_channel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Перейти к вводу заголовка кампании."""
    await state.set_state(CampaignStates.waiting_header)
    
    text = (
        "📝 <b>Заголовок кампании</b>\n\n"
        "Введите название для вашей кампании.\n"
        "Это поможет вам идентифицировать кампанию в списке.\n\n"
        "Пример: «Реклама в @example — Март 2026»\n\n"
        "👇 Введите заголовок:"
    )
    
    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
```

#### 2.2 Модифицировать шаг "Аудитория"

**Файл:** `src/bot/handlers/campaigns.py`

```python
@router.callback_query(
    CampaignStates.waiting_member_count,
    CampaignCB.filter(F.action == "members")
)
async def select_member_count(
    callback: CallbackQuery,
    callback_data: CampaignCB,
    state: FSMContext,
) -> None:
    """Выбрать размер аудитории."""
    data = await state.get_data()
    
    # Проверить есть ли предвыбранный канал
    preselected_channel_id = data.get("preselected_channel_id")
    
    if preselected_channel_id:
        # Пропустить выбор размера, перейти к расписанию
        await state.update_data(
            min_members=0,
            max_members=1000000,
        )
        text = "⏰ <b>Расписание запуска</b>\n\nКогда запустить кампанию?"
        await safe_callback_edit(callback, text, reply_markup=get_schedule_kb())
        await state.set_state(CampaignStates.waiting_schedule)
        return
    
    # Стандартная логика для выбора из каталога
    value = callback_data.value
    # ... existing code ...
```

#### 2.3 Модифицировать подтверждение

```python
async def show_confirmation(target: Message | CallbackQuery, state: FSMContext) -> None:
    """Показать карточку подтверждения кампании."""
    data = await state.get_data()
    
    # Добавить информацию о предвыбранном канале
    preselected_channel = data.get("preselected_channel_username")
    if preselected_channel:
        confirmation_text += f"📡 <b>Канал:</b> @{preselected_channel}\n"
    
    # ... rest of existing code ...
```

---

### Этап 3: Модификация _do_launch_campaign (2-3 часа)

**Файл:** `src/bot/handlers/campaigns.py`

```python
async def _do_launch_campaign(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    user,
    data: dict,
    campaign_repo,
    scheduled_at=None,
) -> None:
    """Запустить кампанию."""
    
    # Проверить есть ли предвыбранный канал
    preselected_channel_id = data.get("preselected_channel_id")
    
    if preselected_channel_id:
        # Создать кампанию с одним каналом
        campaign_data = {
            "user_id": user.id,
            "title": data.get("header", "Без названия"),
            # ... other fields ...
            "filters_json": {
                "topics": [data.get("topic")],
                "preselected_channel_id": preselected_channel_id,  # Сохранить ID
                "use_preselected_only": True,  # Флаг для mailing service
            },
        }
    else:
        # Стандартная логика для массового выбора
        campaign_data = {
            # ... standard fields ...
        }
    
    campaign = await campaign_repo.create(campaign_data)
    # ... rest of code ...
```

---

### Этап 4: Модификация mailing service (4-5 часов)

**Файл:** `src/core/services/mailing_service.py` или `src/tasks/mailing_tasks.py`

```python
async def get_chats_for_campaign(campaign: Campaign) -> list[TelegramChat]:
    """Получить список чатов для рассылки."""
    
    filters = campaign.filters or {}
    
    # Проверить флаг предвыбранного канала
    if filters.get("use_preselected_only"):
        channel_id = filters.get("preselected_channel_id")
        if channel_id:
            # Вернуть только один канал
            chat = await session.get(TelegramChat, channel_id)
            return [chat] if chat else []
    
    # Стандартная логика выбора каналов из каталога
    # ... existing code ...
```

---

### Этап 5: UI/UX улучшения (2-3 часа)

#### 5.1 Прогресс-бар визарда

**Файл:** `src/bot/keyboards/campaign.py`

```python
def get_campaign_step_kb(back: bool = True, step: int = 1, total: int = 7) -> InlineKeyboardMarkup:
    """Клавиатура с индикатором прогресса."""
    builder = InlineKeyboardBuilder()
    
    # Индикатор прогресса
    progress = "█" * step + "░" * (total - step)
    builder.button(
        text=f"Шаг {step}/{total}: {progress}",
        callback_data="noop",
    )
    
    if back:
        builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
    builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
    builder.adjust(1, 2)
    
    return builder.as_markup()
```

#### 5.2 Сообщение об успехе

```python
text = (
    f"✅ <b>Кампания создана!</b>\n\n"
    f"📡 Канал: @{preselected_channel_username}\n"
    f"💰 Стоимость: {channel_price} кр\n"
    f"📊 Охват: ~{member_count} подписчиков\n\n"
    f"Кампания запущена и пост будет опубликован в ближайшее время."
)
```

---

## 🧪 ТЕСТ-КЕЙСЫ

### TC1: Успешное создание кампании с каналом

**Шаги:**
1. Открыть детальную страницу канала
2. Нажать "📋 Добавить в кампанию"
3. Ввести заголовок
4. Ввести текст
5. Подтвердить запуск

**Ожидаемый результат:**
- Кампания создана
- В filters_json записан preselected_channel_id
- Mailing service отправляет пост только в этот канал

### TC2: Попытка с тарифом FREE

**Шаги:**
1. Пользователь с тарифом FREE нажимает "Добавить в кампанию"

**Ожидаемый результат:**
- Показать ошибку "На тарифе FREE создание кампаний недоступно"
- Кнопка "Сменить тариф"

### TC3: Превышен лимит кампаний

**Шаги:**
1. Пользователь достиг лимита кампаний
2. Нажимает "Добавить в кампанию"

**Ожидаемый результат:**
- Показать ошибку с текущим лимитом
- Кнопка "Мои кампании"

### TC4: Канал не принимает рекламу

**Шаги:**
1. Канал в статусе is_accepting_ads = False
2. Пользователь нажимает "Добавить в кампанию"

**Ожидаемый результат:**
- Показать предупреждение "Канал временно не принимает рекламу"

---

## 📁 СПИСОК ИЗМЕНЁННЫХ ФАЙЛОВ

| Файл | Изменения | Оценка |
|------|-----------|--------|
| `src/bot/handlers/channels_db.py` | Добавить handler `add_channel_to_campaign()` | 2ч |
| `src/bot/handlers/campaigns.py` | Модифицировать wizard для поддержки preselected_channel | 4ч |
| `src/bot/keyboards/channels.py` | Добавить кнопку "Начать создание" | 0.5ч |
| `src/bot/keyboards/campaign.py` | Добавить индикатор прогресса | 1ч |
| `src/core/services/mailing_service.py` | Поддержка use_preselected_only флага | 2ч |
| `src/db/models/campaign.py` | Документировать filters_json поля | 0.5ч |

**Итого:** ~10 часов (2-3 рабочих дня)

---

## 🚀 ПОРЯДОК ВЫПОЛНЕНИЯ

```
День 1:
├─ Этап 1: Handler (2ч)
└─ Этап 2: Модификация визарда (4ч)

День 2:
├─ Этап 3: _do_launch_campaign (2ч)
├─ Этап 4: Mailing service (3ч)
└─ Этап 5: UI/UX (2ч)

День 3:
├─ Тестирование (2ч)
├─ Фикс багов (2ч)
└─ Документация (1ч)
```

---

## ✅ КРИТЕРИИ ПРИЁМКИ

- [ ] Кнопка "Добавить в кампанию" работает
- [ ] Проверка тарифа (FREE блокируется)
- [ ] Проверка лимита кампаний
- [ ] Проверка статуса канала (is_accepting_ads)
- [ ] Канал автоматически добавляется в рассылку
- [ ] Визард показывает правильный прогресс
- [ ] Mailing service отправляет только в выбранный канал
- [ ] Успешное сообщение показывает детали кампании
- [ ] Кнопка "Отмена" работает на всех шагах
- [ ] Покрыто тестами (unit + integration)

---

## 🔗 СВЯЗАННЫЕ ЗАДАЧИ

- **Спринт 4:** Визард создания кампании ✅
- **Спринт 8:** Детальная страница канала ✅
- **Task 4:** Детальная страница кампании (в работе)
- **Task 7:** FSM тупики (кнопки отмены) ✅

---

**Готов к реализации. Приступить?**
