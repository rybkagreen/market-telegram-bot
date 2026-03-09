# 📋 ПЛАН РЕАЛИЗАЦИИ: Сравнение каналов

**Файл:** `docs/features/channel_comparison.md`  
**Приоритет:** P2 (средний) — полезно для рекламодателей  
**Оценка:** 3-4 дня  
**Зависимости:** Спринт 0 (каталог каналов), Спринт 9 (медиакиты)

---

## 🎯 ОПИСАНИЕ ФУНКЦИИ

**Сравнение каналов** — позволяет рекламодателю выбрать 2-5 каналов и увидеть их метрики в сравнительной таблице для принятия решения о размещении рекламы.

**Целевая аудитория:**
- Рекламодатели (сравнивают каналы перед покупкой)
- Владельцы каналов (могут посмотреть как их канал смотрится на фоне других)

**Ценность:**
- Быстрое принятие решений на основе данных
- Прозрачность метрик каналов
- Увеличение конверсии в размещения

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ (AS IS)

### Что есть:

```python
# Модель TelegramChat имеет метрики:
member_count: int          # Подписчики
last_avg_views: int        # Средние просмотры
last_er: float             # Engagement Rate
last_post_frequency: float # Постов в день
rating: float              # Рейтинг 0-10
price_per_post: Decimal    # Цена за пост
topic: str                 # Тематика
```

### Чего нет:

- ❌ UI для выбора нескольких каналов для сравнения
- ❌ Страница сравнения с таблицей метрик
- ❌ Визуализация различий (проценты, цвета)
- ❣️ Рекомендации "какой канал лучше"

---

## 🏗 АРХИТЕКТУРА РЕШЕНИЯ

```
┌─────────────────────────────────────────────────────────────┐
│  КАТАЛОГ КАНАЛОВ                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📡 Канал 1  [✅ Сравнить]                              │  │
│  │ 📡 Канал 2  [✅ Сравнить]                              │  │
│  │ 📡 Канал 3  [✅ Сравнить]                              │  │
│  │ ...                                                    │  │
│  │                                                        │  │
│  │ Выбрано: 3 канала                                      │  │
│  │ [📊 Сравнить выбранные]  [❌ Сбросить]                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  СТРАНИЦА СРАВНЕНИЯ                                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📊 Сравнение каналов (3)                               │  │
│  │                                                        │  │
│  │ ┌─────────────┬─────────┬─────────┬─────────┐         │  │
│  │ │ Метрика     │ Канал 1 │ Канал 2 │ Канал 3 │         │  │
│  │ ├─────────────┼─────────┼─────────┼─────────┤         │  │
│  │ │ Подписчики  │ 10K     │ 15K ✅  │ 8K      │         │  │
│  │ │ Просмотры   │ 1.5K    │ 2K ✅   │ 1K      │         │  │
│  │ │ ER          │ 15% ✅  │ 13%     │ 12%     │         │  │
│  │ │ Цена        │ 500 кр  │ 700 кр  │ 400 кр ✅│        │  │
│  │ │ Цена/1K подп│ 50 кр ✅│ 47 кр ✅│ 50 кр   │         │  │
│  │ └─────────────┴─────────┴─────────┴─────────┘         │  │
│  │                                                        │  │
│  │ 🏆 Рекомендация: Канал 2 (лучший охват)                │  │
│  │                                                        │  │
│  │ [📋 Добавить в кампанию] [🔙 В каталог]                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 ПОШАГОВЫЙ ПЛАН РЕАЛИЗАЦИИ

### Этап 1: FSM State для хранения выбранных каналов (1-2 часа)

**Файл:** `src/bot/states/comparison.py` (новый)

```python
"""FSM состояния для сравнения каналов."""

from aiogram.fsm.state import State, StatesGroup


class ChannelComparisonStates(StatesGroup):
    """Состояния для сравнения каналов."""
    
    selecting = State()  # Выбор каналов
    comparing = State()  # Просмотр сравнения
```

**Хранение в state:**

```python
# В session data
await state.update_data(
    comparison_selected_channels=[channel_id1, channel_id2, channel_id3],
)
```

---

### Этап 2: Сервис для сравнения (3-4 часа)

**Файл:** `src/core/services/comparison_service.py` (новый)

```python
"""Service для сравнения каналов."""

import logging
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class ComparisonService:
    """Сервис для сравнения каналов."""
    
    async def get_channels_for_comparison(
        self,
        channel_ids: list[int],
    ) -> list[dict[str, Any]]:
        """
        Получить данные каналов для сравнения.
        
        Args:
            channel_ids: Список ID каналов.
        
        Returns:
            Список словарей с данными каналов.
        """
        from sqlalchemy import select
        
        from src.db.models.analytics import TelegramChat
        
        async with async_session_factory() as session:
            stmt = select(TelegramChat).where(
                TelegramChat.id.in_(channel_ids)
            )
            result = await session.execute(stmt)
            channels = list(result.scalars().all())
            
            # Сортируем в порядке ID как передано
            channel_map = {ch.id: ch for ch in channels}
            return [
                self._channel_to_dict(channel_map[cid])
                for cid in channel_ids
                if cid in channel_map
            ]
    
    def _channel_to_dict(self, channel: TelegramChat) -> dict[str, Any]:
        """Конвертировать канал в словарь."""
        return {
            "id": channel.id,
            "username": channel.username,
            "title": channel.title,
            "member_count": channel.member_count or 0,
            "avg_views": channel.last_avg_views or 0,
            "er": channel.last_er or 0.0,
            "post_frequency": channel.last_post_frequency or 0.0,
            "rating": channel.rating or 0.0,
            "price_per_post": float(channel.price_per_post) if channel.price_per_post else 0,
            "topic": channel.topic,
        }
    
    def calculate_comparison_metrics(
        self,
        channels_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Рассчитать дополнительные метрики для сравнения.
        
        Args:
            channels_data: Данные каналов.
        
        Returns:
            dict с рассчитанными метриками.
        """
        if not channels_data:
            return {}
        
        # Цена за 1000 подписчиков (CPM)
        for ch in channels_data:
            if ch["member_count"] > 0:
                ch["price_per_1k_subscribers"] = round(
                    ch["price_per_post"] / (ch["member_count"] / 1000),
                    2
                )
            else:
                ch["price_per_1k_subscribers"] = 0
        
        # Найти лучшие значения по каждой метрике
        metrics = [
            "member_count",
            "avg_views",
            "er",
            "price_per_1k_subscribers",  # меньше = лучше
        ]
        
        best_values = {}
        for metric in metrics:
            values = [ch.get(metric, 0) for ch in channels_data]
            if metric == "price_per_1k_subscribers":
                best_values[metric] = min(values)  # меньше = лучше
            else:
                best_values[metric] = max(values)  # больше = лучше
        
        # Пометить лучшие значения
        for ch in channels_data:
            ch["is_best"] = {}
            for metric, best_value in best_values.items():
                ch["is_best"][metric] = (ch.get(metric, 0) == best_value)
        
        # Рекомендация
        recommendation = self._generate_recommendation(channels_data)
        
        return {
            "channels": channels_data,
            "best_values": best_values,
            "recommendation": recommendation,
        }
    
    def _generate_recommendation(
        self,
        channels_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Сгенерировать рекомендацию какой канал лучше.
        
        Логика:
        - Если важен охват → канал с максимальными avg_views
        - Если важна эффективность → канал с лучшим ER
        - Если важен бюджет → канал с минимальным price_per_1k_subscribers
        
        Returns:
            dict с рекомендацией.
        """
        if not channels_data:
            return {"channel_id": None, "reason": ""}
        
        # Простая эвристика: лучший по ER
        best_by_er = max(channels_data, key=lambda x: x.get("er", 0))
        
        return {
            "channel_id": best_by_er["id"],
            "reason": "Лучший Engagement Rate",
            "channel_name": best_by_er.get("title") or best_by_er.get("username"),
        }
```

---

### Этап 3: Клавиатуры для сравнения (2-3 часа)

**Файл:** `src/bot/keyboards/comparison.py` (новый)

```python
"""Клавиатуры для сравнения каналов."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.channels import ChannelsCB


class ComparisonCB(CallbackData, prefix="comparison"):
    """CallbackData для сравнения каналов."""
    
    action: str
    channel_id: str = ""


def get_channel_with_compare_kb(
    channel_id: int,
    channel_username: str,
    is_selected: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для канала с кнопкой "Сравнить".
    
    Args:
        channel_id: ID канала.
        channel_username: Username канала.
        is_selected: Выбран ли канал для сравнения.
    """
    builder = InlineKeyboardBuilder()
    
    compare_text = "✅ В сравнении" if is_selected else "📊 Сравнить"
    builder.button(
        text=compare_text,
        callback_data=ComparisonCB(
            action="toggle",
            channel_id=str(channel_id),
        ).pack(),
    )
    
    builder.button(
        text="📡 Открыть канал",
        callback_data=ChannelsCB(
            action="view_channel",
            value=str(channel_id),
        ).pack(),
    )
    
    builder.adjust(2)
    return builder.as_markup()


def get_comparison_bar_kb(selected_count: int) -> InlineKeyboardMarkup:
    """
    Панель управления сравнением.
    
    Args:
        selected_count: Количество выбранных каналов.
    """
    builder = InlineKeyboardBuilder()
    
    if selected_count > 0:
        builder.button(
            text=f"📊 Сравнить ({selected_count})",
            callback_data=ComparisonCB(action="compare").pack(),
        )
        builder.button(
            text="❌ Сбросить",
            callback_data=ComparisonCB(action="clear").pack(),
        )
        builder.adjust(2)
    else:
        builder.button(
            text="🔙 В каталог",
            callback_data=ChannelsCB(action="categories").pack(),
        )
        builder.adjust(1)
    
    return builder.as_markup()


def get_comparison_result_kb(channel_ids: list[int]) -> InlineKeyboardMarkup:
    """
    Клавиатура для страницы сравнения.
    
    Args:
        channel_ids: Список ID сравниваемых каналов.
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки для каждого канала
    for channel_id in channel_ids[:5]:  # Максимум 5
        builder.button(
            text=f"📋 Добавить в кампанию",
            callback_data=f"add_to_campaign:{channel_id}",
        )
    
    builder.button(
        text="🔙 В каталог",
        callback_data=ChannelsCB(action="categories").pack(),
    )
    builder.adjust(1)
    
    return builder.as_markup()
```

---

### Этап 4: Handler'ы для выбора каналов (3-4 часа)

**Файл:** `src/bot/handlers/comparison.py` (новый)

```python
"""Handler'ы для сравнения каналов."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage

from src.bot.keyboards.comparison import (
    ComparisonCB,
    get_channel_with_compare_kb,
    get_comparison_bar_kb,
)
from src.bot.keyboards.channels import ChannelsCB
from src.bot.states.comparison import ChannelComparisonStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(ComparisonCB.filter(F.action == "toggle"))
async def toggle_channel_for_comparison(
    callback: CallbackQuery,
    callback_data: ComparisonCB,
    state: FSMContext,
) -> None:
    """Добавить/убрать канал из сравнения."""
    channel_id = int(callback_data.channel_id)
    
    # Получить текущие выбранные каналы
    data = await state.get_data()
    selected = data.get("comparison_selected_channels", [])
    
    # Toggle
    if channel_id in selected:
        selected.remove(channel_id)
    else:
        # Максимум 5 каналов для сравнения
        if len(selected) >= 5:
            await callback.answer(
                "❌ Можно сравнивать максимум 5 каналов",
                show_alert=True,
            )
            return
        selected.append(channel_id)
    
    await state.update_data(comparison_selected_channels=selected)
    
    # Перерисовать кнопку
    await callback.answer(
        f"{'✅ Добавлен' if channel_id in selected else '❌ Убран'}",
        show_alert=False,
    )


@router.callback_query(ComparisonCB.filter(F.action == "compare"))
async def show_comparison(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать сравнение выбранных каналов."""
    data = await state.get_data()
    selected = data.get("comparison_selected_channels", [])
    
    if len(selected) < 2:
        await callback.answer(
            "❌ Выберите минимум 2 канала для сравнения",
            show_alert=True,
        )
        return
    
    # Получить данные каналов
    from src.core.services.comparison_service import comparison_service
    
    channels_data = await comparison_service.get_channels_for_comparison(selected)
    comparison = comparison_service.calculate_comparison_metrics(channels_data)
    
    # Сформировать текст сравнения
    text = "📊 <b>Сравнение каналов</b>\n\n"
    text += "━━━ ТАБЛИЦА ━━━\n\n"
    
    # Заголовок таблицы
    headers = ["Метрика"]
    for ch in comparison["channels"]:
        name = ch.get("title") or ch.get("username") or f"Канал {ch['id']}"
        headers.append(name[:20])
    
    text += " | ".join(headers) + "\n"
    text += " | ".join(["─" * 20] * len(headers)) + "\n"
    
    # Строки метрик
    metrics = [
        ("👥 Подписчики", "member_count", lambda x: f"{x:,}"),
        ("👁 Просмотры", "avg_views", lambda x: f"{x:,}"),
        ("📈 ER", "er", lambda x: f"{x:.1f}%"),
        ("📝 Постов/день", "post_frequency", lambda x: f"{x:.1f}"),
        ("💰 Цена", "price_per_post", lambda x: f"{x:.0f} кр"),
        ("💰 Цена/1К подп", "price_per_1k_subscribers", lambda x: f"{x:.0f} кр"),
    ]
    
    for label, metric, formatter in metrics:
        row = [label]
        for ch in comparison["channels"]:
            value = ch.get(metric, 0)
            formatted = formatter(value)
            # Пометить лучшее значение
            if ch.get("is_best", {}).get(metric):
                formatted = f"✅ {formatted}"
            row.append(formatted)
        text += " | ".join(row) + "\n"
    
    # Рекомендация
    rec = comparison.get("recommendation", {})
    if rec.get("channel_id"):
        text += f"\n🏆 <b>Рекомендация:</b> {rec.get('channel_name')}\n"
        text += f"   {rec.get('reason')}\n"
    
    from src.bot.keyboards.comparison import get_comparison_result_kb
    
    keyboard = get_comparison_result_kb(selected)
    
    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(ComparisonCB.filter(F.action == "clear"))
async def clear_comparison(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Сбросить выбранные каналы."""
    await state.update_data(comparison_selected_channels=[])
    await callback.answer("✅ Сравнение сброшено", show_alert=False)
    
    # Вернуться к каталогу
    from src.bot.handlers.channels_db import handle_categories
    await handle_categories(callback)
```

---

### Этап 5: Интеграция с каталогом (2-3 часа)

**Файл:** `src/bot/handlers/channels_db.py` (расширение)

Добавить кнопку "Сравнить" к каждому каналу в списке:

```python
# В handle_category_detail или show_channels_list
for channel in channels:
    # Проверить выбран ли канал
    is_selected = channel.id in selected_channels
    
    # Добавить кнопку с каналом
    keyboard = get_channel_with_compare_kb(
        channel_id=channel.id,
        channel_username=channel.username,
        is_selected=is_selected,
    )
    
    # ... показать канал
```

**Панель сравнения:**

```python
# В конце страницы каталога
selected_count = len(selected_channels)
if selected_count > 0:
    text += f"\n\n📊 <b>Сравнение:</b> выбрано {selected_count} каналов\n"
    text += "Минимум 2, максимум 5 каналов для сравнения."

keyboard = get_comparison_bar_kb(selected_count)
```

---

### Этап 6: Визуализация различий (2-3 часа)

**Файл:** `src/bot/keyboards/comparison.py` (расширение)

```python
def format_metric_with_indicator(
    value: float,
    best_value: float,
    metric_type: str = "higher_better",
) -> str:
    """
    Форматировать метрику с индикатором.
    
    Args:
        value: Значение метрики.
        best_value: Лучшее значение среди всех.
        metric_type: "higher_better" или "lower_better".
    
    Returns:
        Строка с индикатором.
    """
    if metric_type == "higher_better":
        if value == best_value:
            return f"✅ {value:.1f}"
        elif value >= best_value * 0.8:
            return f"🟢 {value:.1f}"  # 80%+ от лучшего
        elif value >= best_value * 0.5:
            return f"🟡 {value:.1f}"  # 50-80% от лучшего
        else:
            return f"🔴 {value:.1f}"  # < 50% от лучшего
    else:
        # lower_better (например, цена)
        if value == best_value:
            return f"✅ {value:.1f}"
        elif value <= best_value * 1.2:
            return f"🟢 {value:.1f}"
        elif value <= best_value * 1.5:
            return f"🟡 {value:.1f}"
        else:
            return f"🔴 {value:.1f}"
```

---

## 📁 СПИСОК ИЗМЕНЁННЫХ ФАЙЛОВ

| Файл | Изменения | Оценка |
|------|-----------|--------|
| `src/bot/states/comparison.py` | Новый файл | 1ч |
| `src/core/services/comparison_service.py` | Новый сервис | 4ч |
| `src/bot/keyboards/comparison.py` | Новые клавиатуры | 3ч |
| `src/bot/handlers/comparison.py` | Новые handler'ы | 4ч |
| `src/bot/handlers/channels_db.py` | Интеграция кнопки | 2ч |

**Итого:** ~14 часов (3-4 рабочих дня)

---

## 🚀 ПОРЯДОК ВЫПОЛНЕНИЯ

```
День 1:
├─ Этап 1: FSM State (1ч)
├─ Этап 2: ComparisonService (4ч)
└─ Этап 3: Клавиатуры (3ч)

День 2:
├─ Этап 4: Handler'ы (4ч)
└─ Этап 5: Интеграция (2ч)

День 3:
├─ Этап 6: Визуализация (3ч)
├─ Тестирование (2ч)
└─ Фикс багов (1ч)
```

---

## ✅ КРИТЕРИИ ПРИЁМКИ

### Базовый функционал:
- [ ] Можно выбрать канал для сравнения (toggle)
- [ ] Минимум 2 канала для сравнения
- [ ] Максимум 5 каналов для сравнения
- [ ] Сравнение показывает таблицу метрик
- [ ] Лучшие значения помечены ✅

### Метрики для сравнения:
- [ ] Подписчики (member_count)
- [ ] Средние просмотры (avg_views)
- [ ] ER (last_er)
- [ ] Частота постов (post_frequency)
- [ ] Цена за пост (price_per_post)
- [ ] Цена за 1000 подписчиков (расчётная)

### UI/UX:
- [ ] Кнопка "Сравнить" у каждого канала
- [ ] Панель с количеством выбранных
- [ ] Кнопка "Сбросить" для очистки
- [ ] Рекомендация лучшего канала
- [ ] Кнопки "Добавить в кампанию" для каждого

### Интеграция:
- [ ] Работает из каталога каналов
- [ ] Работает из поиска по категориям
- [ ] State сохраняется между переходами
- [ ] Сброс при выходе из бота

---

## 🔗 СВЯЗАННЫЕ ЗАДАЧИ

- **Спринт 0:** Каталог каналов ✅
- **Спринт 9:** Медиакиты (интеграция кнопки)
- **Task 4:** Детальная страница канала ✅
- **Фильтры каталога:** (можно комбинировать с сравнением)

---

## 🎯 ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ (Future)

### Экспорт сравнения в PDF

```
Кнопка "📤 Скачать сравнение":
• Генерирует PDF с таблицей
• Включает графики и рекомендации
• Можно отправить менеджеру/клиенту
```

### Сохранение сравнений

```
"💾 Сохранить сравнение":
• Пользователь может сохранить текущее сравнение
• Доступ к сохранённым из /saved_comparisons
• Уведомление если канал изменил метрики
```

### Расширенные метрики

```
Дополнительные метрики для сравнения:
• Динамика подписчиков (рост/падение)
• Лучшее время для постинга
• Тематика постов (LLM анализ)
• Аудитория (пол, возраст, гео)
```

### Умные рекомендации

```
AI-рекомендации на основе:
• Целей кампании (охват vs конверсия)
• Бюджета рекламодателя
• Исторических данных по кампаниям
• Отзывов других рекламодателей
```

---

## 📊 MOCKUP ДАННЫХ ДЛЯ ТЕСТИРОВАНИЯ

```python
MOCK_COMPARISON_DATA = {
    "channels": [
        {
            "id": 1,
            "username": "tech_channel",
            "title": "IT Новости",
            "member_count": 15000,
            "avg_views": 2500,
            "er": 16.7,
            "post_frequency": 3.5,
            "price_per_post": 500,
            "price_per_1k_subscribers": 33.3,
            "is_best": {
                "member_count": False,
                "avg_views": False,
                "er": True,
                "price_per_1k_subscribers": False,
            },
        },
        {
            "id": 2,
            "username": "biz_channel",
            "title": "Бизнес Сегодня",
            "member_count": 20000,
            "avg_views": 3500,
            "er": 17.5,
            "post_frequency": 2.0,
            "price_per_post": 800,
            "price_per_1k_subscribers": 40.0,
            "is_best": {
                "member_count": True,
                "avg_views": True,
                "er": False,
                "price_per_1k_subscribers": False,
            },
        },
        {
            "id": 3,
            "username": "cheap_ads",
            "title": "Дешёвая Реклама",
            "member_count": 8000,
            "avg_views": 1000,
            "er": 12.5,
            "post_frequency": 5.0,
            "price_per_post": 200,
            "price_per_1k_subscribers": 25.0,
            "is_best": {
                "member_count": False,
                "avg_views": False,
                "er": False,
                "price_per_1k_subscribers": True,
            },
        },
    ],
    "recommendation": {
        "channel_id": 2,
        "reason": "Лучший охват и Engagement Rate",
        "channel_name": "Бизнес Сегодня",
    },
}
```

---

**Готов к реализации. Приступить?**
