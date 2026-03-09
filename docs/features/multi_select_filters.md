# 📋 ПЛАН РЕАЛИЗАЦИИ: Мультивыбор фильтров каталога

**Файл:** `docs/features/multi_select_filters.md`  
**Приоритет:** P2 (средний)  
**Оценка:** 3-4 дня  
**Зависимости:** Спринт 0 (каталог каналов), Спринт 4 (детальная страница канала)

---

## 🎯 ОПИСАНИЕ ПРОБЛЕМЫ

### Текущее состояние (AS IS):

```
Пользователь → Каталог → Выбрать категорию → Выбрать тариф → Показать результат
                                              ↓
                                    (предыдущий фильтр сбрасывается)
```

**Проблема:** Фильтры применяются **последовательно**, каждый новый выбор заменяет предыдущий.

**Пример:**
1. Пользователь выбирает категорию "IT" → видит 150 каналов
2. Затем выбирает тариф "PRO" → видит 80 каналов **по тарифу**, но **без учёта категории**
3. Невозможно отфильтровать "IT каналы тарифа PRO"

### Желаемое состояние (TO BE):

```
Пользователь → Каталог → [Мультивыбор категорий] + [Мультивыбор тарифов] → Показать результат
                           ↓                    ↓
                      IT ✅, Бизнес ✅      FREE ✅, PRO ✅
                                              ↓
                                    25 каналов (IT+Бизнес + FREE+PRO)
```

**Преимущества:**
- Точная фильтрация по нескольким критериям
- Уменьшение времени поиска подходящих каналов
- Увеличение конверсии в создание кампаний

---

## 🏗 АРХИТЕКТУРА РЕШЕНИЯ

### Компоненты:

```
┌─────────────────────────────────────────────────────────────┐
│  UI Layer (клавиатуры)                                      │
│  ├─ get_multi_select_categories_kb()                        │
│  ├─ get_multi_select_tariffs_kb()                           │
│  └─ get_active_filters_bar()                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  FSM State (хранение выбранных фильтров)                    │
│  ├─ selected_categories: ["it", "бизнес"]                   │
│  ├─ selected_tariffs: ["free", "pro"]                       │
│  └─ selected_min_members: 1000                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Repository Layer (SQL запрос с несколькими IN)             │
│  ├─ topic IN ('it', 'бизнес')                               │
│  ├─ tariff_tier IN ('free', 'pro')                          │
│  └─ member_count >= 1000                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 ПОШАГОВЫЙ ПЛАН РЕАЛИЗАЦИИ

### Этап 1: Модификация CallbackData (1-2 часа)

**Файл:** `src/bot/keyboards/channels.py`

**Проблема:** Текущий `ChannelsCB` не поддерживает передачу нескольких значений.

**Решение:**

```python
class ChannelsCB(CallbackData, prefix="channels"):
    """CallbackData для базы каналов."""
    
    action: str
    value: str = ""  # Для одиночного выбора
    values: str = ""  # Для мультивыбора (JSON через запятую)
    page: int = 1
    filter_type: str = ""  # "category", "tariff", "members"
```

**Новые callback паттерны:**
- `channels:toggle_category:it` — переключить категорию
- `channels:toggle_tariff:pro` — переключить тариф
- `channels:apply_filters` — применить выбранные фильтры
- `channels:clear_filters` — сбросить все фильтры
- `channels:remove_filter:category:it` — удалить конкретный фильтр

---

### Этап 2: Клавиатуры с мультивыбором (3-4 часа)

**Файл:** `src/bot/keyboards/channels.py`

#### 2.1 get_multi_select_categories_kb()

```python
def get_multi_select_categories_kb(
    selected: list[str] | None = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура с мультивыбором категорий.
    
    Args:
        selected: Список выбранных категорий (коды).
    """
    builder = InlineKeyboardBuilder()
    selected = selected or []
    
    for label, code in CHANNEL_CATEGORIES:
        # Галочка если выбрано
        prefix = "✅ " if code in selected else ""
        builder.button(
            text=f"{prefix}{label}",
            callback_data=ChannelsCB(
                action="toggle_category",
                value=code,
            ).pack(),
        )
    
    # Кнопки действий
    builder.button(
        text="🔙 Назад",
        callback_data=ChannelsCB(action="categories").pack(),
    )
    builder.button(
        text="🎯 Применить фильтры",
        callback_data=ChannelsCB(action="apply_filters").pack(),
    )
    builder.adjust(2, 2, 2, 2, 2, 2, 2)
    
    return builder.as_markup()
```

#### 2.2 get_active_filters_bar()

```python
def get_active_filters_bar(
    categories: list[str],
    tariffs: list[str],
) -> str:
    """
    Сгенерировать строку активных фильтров.
    
    Returns:
        Текст для отображения над результатами.
    """
    filters = []
    
    if categories:
        cat_names = [cat.capitalize() for cat in categories]
        filters.append(f"📁 Категории: {', '.join(cat_names)}")
    
    if tariffs:
        tariff_names = [t.upper() for t in tariffs]
        filters.append(f"💎 Тарифы: {', '.join(tariff_names)}")
    
    if filters:
        return "🔍 <b>Активные фильтры:</b>\n" + "\n".join(filters)
    return ""
```

---

### Этап 3: FSM State для хранения фильтров (2-3 часа)

**Файл:** `src/bot/states/channels.py` (новый)

```python
"""FSM состояния для фильтров каталога."""

from aiogram.fsm.state import State, StatesGroup


class ChannelFilterStates(StatesGroup):
    """Состояния для фильтров каталога."""
    
    browsing = State()  # Просмотр без фильтров
    filtering = State()  # Режим выбора фильтров
```

**Хранение в state:**

```python
# В channels_db.py handler'ах
await state.update_data(
    filter_selected_categories=["it", "бизнес"],
    filter_selected_tariffs=["free", "pro"],
    filter_min_members=1000,
    filter_max_members=100000,
)
```

---

### Этап 4: Handler'ы для мультивыбора (4-5 часов)

**Файл:** `src/bot/handlers/channels_db.py`

#### 4.1 toggle_category handler

```python
@router.callback_query(ChannelsCB.filter(F.action == "toggle_category"))
async def toggle_category(
    callback: CallbackQuery,
    callback_data: ChannelsCB,
    state: FSMContext,
) -> None:
    """Переключить категорию (добавить/убрать)."""
    
    category = callback_data.value
    
    # Получить текущие фильтры
    data = await state.get_data()
    selected = data.get("filter_selected_categories", [])
    
    # Toggle
    if category in selected:
        selected.remove(category)
    else:
        selected.append(category)
    
    await state.update_data(filter_selected_categories=selected)
    
    # Перерисовать клавиатуру
    await safe_callback_edit(
        callback,
        "📁 <b>Выберите категории</b>\n\n"
        f"Выбрано: {len(selected)}\n\n"
        "Нажмите на категорию чтобы добавить/убрать.",
        reply_markup=get_multi_select_categories_kb(selected),
    )
    await callback.answer()
```

#### 4.2 apply_filters handler

```python
@router.callback_query(ChannelsCB.filter(F.action == "apply_filters"))
async def apply_filters(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Применить выбранные фильтры и показать результат."""
    
    data = await state.get_data()
    categories = data.get("filter_selected_categories", [])
    tariffs = data.get("filter_selected_tariffs", [])
    
    # Получить каналы с фильтрами
    async with async_session_factory() as session:
        channels = await get_channels_with_filters(
            session,
            categories=categories,
            tariffs=tariffs,
        )
    
    # Показать результат
    text = get_active_filters_bar(categories, tariffs)
    text += f"\n\n📡 <b>Найдено каналов: {len(channels)}</b>\n"
    
    # ... показать первый канал или список
    
    await safe_callback_edit(
        callback,
        text,
        reply_markup=get_channels_list_kb(channels[:10]),
    )
```

---

### Этап 5: Repository метод с несколькими IN (3-4 часа)

**Файл:** `src/db/repositories/chat_analytics.py`

```python
async def get_channels_with_multi_filters(
    self,
    categories: list[str] | None = None,
    tariffs: list[str] | None = None,
    min_members: int | None = None,
    max_members: int | None = None,
    limit: int = 100,
) -> list[TelegramChat]:
    """
    Получить каналы с несколькими фильтрами одновременно.
    
    Args:
        categories: Список категорий (IN operator).
        tariffs: Список тарифов (IN operator).
        min_members: Минимальное количество подписчиков.
        max_members: Максимальное количество подписчиков.
        limit: Лимит результатов.
    
    Returns:
        Список каналов.
    """
    from sqlalchemy import and_, or_, select
    
    filters = [TelegramChat.is_active == True]  # noqa: E712
    
    # Категории (OR внутри)
    if categories:
        filters.append(
            or_(*[func.lower(TelegramChat.topic) == cat.lower() for cat in categories])
        )
    
    # Тарифы (предполагается что tariff_tier хранится в БД)
    if tariffs:
        filters.append(TelegramChat.tariff_tier.in_(tariffs))
    
    # Размер аудитории
    if min_members:
        filters.append(TelegramChat.member_count >= min_members)
    if max_members:
        filters.append(TelegramChat.member_count <= max_members)
    
    stmt = (
        select(TelegramChat)
        .where(and_(*filters))
        .order_by(TelegramChat.member_count.desc())
        .limit(limit)
    )
    
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

---

### Этап 6: UI/UX улучшения (2-3 часа)

#### 6.1 Индикатор количества выбранных фильтров

**Файл:** `src/bot/keyboards/channels.py`

```python
def get_filter_indicator(selected_count: int) -> str:
    """Вернуть иконку с количеством выбранных фильтров."""
    if selected_count == 0:
        return "🔍 Фильтры"
    elif selected_count <= 3:
        return f"🔍 Фильтры ({selected_count})"
    else:
        return f"🔍 Фильтры ({selected_count}+)"
```

#### 6.2 Кнопка сброса фильтров

```python
def get_clear_filters_button() -> InlineKeyboardButton:
    """Кнопка для сброса всех фильтров."""
    return InlineKeyboardButton(
        text="❌ Сбросить фильтры",
        callback_data=ChannelsCB(action="clear_filters").pack(),
    )
```

#### 6.3 Handler для сброса

```python
@router.callback_query(ChannelsCB.filter(F.action == "clear_filters"))
async def clear_filters(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Сбросить все фильтры."""
    
    await state.clear()
    
    await callback.answer("✅ Фильтры сброшены", show_alert=False)
    
    # Вернуться к основному меню каталога
    await handle_categories(callback)
```

---

### Этап 7: Тестирование (1-2 дня)

#### Test Cases:

**TC1: Выбор одной категории**
- Выбрать "IT"
- Применить
- **Ожидаемый результат:** Только IT каналы

**TC2: Выбор нескольких категорий**
- Выбрать "IT", "Бизнес"
- Применить
- **Ожидаемый результат:** Каналы IT ИЛИ Бизнес

**TC3: Выбор категории + тарифа**
- Выбрать "IT"
- Выбрать "PRO"
- Применить
- **Ожидаемый результат:** Каналы (IT ИЛИ Бизнес) И (PRO тариф)

**TC4: Сброс фильтров**
- Выбрать фильтры
- Нажать "Сбросить"
- **Ожидаемый результат:** Все фильтры очищены, показаны все каналы

**TC5: Удаление конкретного фильтра**
- Выбрать 3 категории
- Удалить одну через "✕ IT"
- **Ожидаемый результат:** Осталось 2 категории

---

## 📁 СПИСОК ИЗМЕНЁННЫХ ФАЙЛОВ

| Файл | Изменения | Оценка |
|------|-----------|--------|
| `src/bot/keyboards/channels.py` | Мультивыбор клавиатуры + индикаторы | 4ч |
| `src/bot/states/channels.py` | Новый файл для FSM состояний | 1ч |
| `src/bot/handlers/channels_db.py` | Handler'ы для toggle/apply/clear | 6ч |
| `src/db/repositories/chat_analytics.py` | Метод get_channels_with_multi_filters | 3ч |
| `src/bot/keyboards/main_menu.py` | Обновление MainMenuCB (если нужно) | 1ч |

**Итого:** ~15 часов (3-4 рабочих дня)

---

## 🚀 ПОРЯДОК ВЫПОЛНЕНИЯ

```
День 1:
├─ Этап 1: CallbackData (1ч)
├─ Этап 2: Клавиатуры (4ч)
└─ Этап 3: FSM State (2ч)

День 2:
├─ Этап 4: Handler'ы (6ч)
└─ Этап 6: UI/UX (2ч)

День 3:
├─ Этап 5: Repository (3ч)
└─ Этап 7: Тестирование (4ч)

День 4:
└─ Фикс багов + документация (4ч)
```

---

## ✅ КРИТЕРИИ ПРИЁМКИ

- [ ] Можно выбрать несколько категорий одновременно
- [ ] Можно выбрать несколько тарифов одновременно
- [ ] Фильтры применяются через SQL IN (OR внутри группы)
- [ ] Группы фильтров комбинируются через AND
- [ ] Индикатор показывает количество выбранных фильтров
- [ ] Кнопка "Сбросить фильтры" работает
- [ ] Кнопка "Удалить фильтр" для конкретного фильтра работает
- [ ] Пагинация работает с фильтрами
- [ ] Производительность: запрос < 500ms для 10K каналов
- [ ] Покрыто тестами (unit + integration)

---

## 🔗 СВЯЗАННЫЕ ЗАДАЧИ

- **Спринт 0:** Базовый каталог каналов ✅
- **Спринт 4:** Детальная страница канала ✅
- **Task 4:** Детальная страница кампании (в работе)
- **Фильтр по размеру аудитории:** (будущий спринт)

---

## 🎯 ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ (Future)

### Фильтр по размеру аудитории (слайдер)

```
👥 Размер аудитории:
[1K]━━━━━●━━━━━[100K]
     10K выбрано
```

### Фильтр по рейтингу

```
⭐ Рейтинг канала:
   ⭐⭐⭐⭐⭐ (4.5+)
   ⭐⭐⭐⭐  (4.0+)
   ⭐⭐⭐   (3.0+)
```

### Сохранение пресетов фильтров

```
💾 Сохранить пресет:
"IT каналы PRO тарифа"
"Бизнес каналы 10K-50K"
```

---

**Готов к реализации. Приступить?**
