# 📋 ПЛАН РЕАЛИЗАЦИИ: Медиакит канала

**Файл:** `docs/features/channel_mediakit.md`  
**Приоритет:** P1 (высокий) — важно для B2B сегмента  
**Оценка:** 4-5 дней  
**Зависимости:** Спринт 0 (каналы владельцев), Спринт 4 (детальная страница), Спринт 8 (отзывы)

---

## 🎯 ОПИСАНИЕ ФУНКЦИИ

**Медиакит канала** — это публичная страница/документ с ключевыми метриками канала для привлечения рекламодателей.

**Целевая аудитория:**
- Владельцы каналов (создают и настраивают)
- Рекламодатели (просматривают перед покупкой размещения)

**Ценность:**
- Для владельцев: автоматическая генерация презентации канала
- Для рекламодателей: прозрачная информация о канале перед покупкой

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ (AS IS)

### Что есть в модели `TelegramChat`:

```python
# Базовая информация
username: str
title: str | None
description: str | None
topic: str | None
subcategory: str | None
language: str
member_count: int

# Метрики
rating: float  # 0-10
last_avg_views: int  # средние просмотры
last_er: float  # Engagement Rate
last_post_frequency: float  # постов в день

# Реклама
price_per_post: Decimal
is_accepting_ads: bool
owner_user_id: int | None

# История постов (для LLM)
recent_posts: list[RecentPostJSON] | None
```

### Чего нет:

- ❌ Отдельная страница медиакита
- ❌ PDF генерация медиакита
- ❌ Публичная ссылка на медиакит
- ❌ Кастомизация медиакита владельцем
- ❌ Статистика по рекламным интеграциям
- ❌ Динамические графики (просмотры, ER, постинг)

---

## 🏗 АРХИТЕКТУРА РЕШЕНИЯ

```
┌─────────────────────────────────────────────────────────────┐
│  ВЛАДЕЛЕЦ КАНАЛА                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ /my_channels → Выбрать канал → [📊 Медиакит]          │  │
│  │                                                        │  │
│  │ Редактор медиакита:                                   │  │
│  │ • Загрузить логотип                                   │  │
│  │ • Добавить описание                                   │  │
│  │ • Выбрать метрики для отображения                     │  │
│  │ • Настроить цвета/стиль                               │  │
│  │                                                        │  │
│  │ [💾 Сохранить] [📤 Скачать PDF] [🔗 Получить ссылку]  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  РЕКЛАМОДАТЕЛЬ                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Каталог → Выбрать канал → [📊 Просмотр медиакита]     │  │
│  │                                                        │  │
│  │ Публичная страница:                                   │  │
│  │ • Логотип + название                                  │  │
│  │ • Описание                                            │  │
│  │ • Метрики (подписчики, просмотры, ER)                 │  │
│  │ • График активности                                   │  │
│  │ • Цена за пост                                        │  │
│  │ • Отзывы                                              │  │
│  │                                                        │  │
│  │ [📤 Скачать PDF] [📋 Добавить в кампанию]              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 ПОШАГОВЫЙ ПЛАН РЕАЛИЗАЦИИ

### Этап 1: Модель ChannelMediakit (3-4 часа)

**Файл:** `src/db/models/channel_mediakit.py` (новый)

```python
class ChannelMediakit(Base, TimestampMixin):
    """
    Медиакит канала — настраиваемая презентация для рекламодателей.
    
    Attributes:
        channel_id: ID канала (FK на telegram_chats.id).
        owner_user_id: ID владельца (FK на users.id).
        
        # Контент
        custom_description: Кастомное описание (если отличается от description).
        logo_file_id: Telegram file ID логотипа.
        banner_file_id: Telegram file ID баннера.
        
        # Настройки отображения
        show_metrics: JSON с флагами какие метрики показывать.
        theme_color: HEX цвет темы (например, "#1a73e8").
        is_public: Публичный ли медиакит (доступен по ссылке).
        
        # Статистика
        views_count: Количество просмотров медиакита.
        downloads_count: Количество скачиваний PDF.
    """
    
    __tablename__ = "channel_mediakits"
    
    id: Mapped[int] = primary_key
    channel_id: Mapped[int] = ForeignKey("telegram_chats.id")
    owner_user_id: Mapped[int] = ForeignKey("users.id")
    
    # Контент
    custom_description: Mapped[str | None]
    logo_file_id: Mapped[str | None]
    banner_file_id: Mapped[str | None]
    
    # Настройки
    show_metrics: Mapped[dict] = JSONB  # {"subscribers": true, "views": true, ...}
    theme_color: Mapped[str] = "#1a73e8"
    is_public: Mapped[bool] = True
    
    # Статистика
    views_count: Mapped[int] = 0
    downloads_count: Mapped[int] = 0
```

**Миграция:** `src/db/migrations/versions/202603XX_0013_add_channel_mediakit.py`

---

### Этап 2: Сервис для генерации медиакита (4-5 часов)

**Файл:** `src/core/services/mediakit_service.py` (новый)

```python
class MediakitService:
    """Сервис для работы с медиакитами каналов."""
    
    async def get_or_create_mediakit(self, channel_id: int) -> ChannelMediakit:
        """Получить или создать медиакит для канала."""
        
    async def update_mediakit(
        self,
        mediakit_id: int,
        owner_user_id: int,
        updates: dict,
    ) -> ChannelMediakit:
        """Обновить медиакит (только владелец)."""
        
    async def get_mediakit_data(self, channel_id: int) -> dict:
        """
        Получить полные данные для медиакита.
        
        Returns:
            {
                "channel": {...},
                "mediakit": {...},
                "metrics": {
                    "subscribers": 10000,
                    "avg_views": 1500,
                    "er": 15.0,
                    "post_frequency": 2.5,
                    "top_posts": [...],
                },
                "reviews": {...},
                "price": {...},
            }
        """
    
    async def track_view(self, mediakit_id: int) -> None:
        """Засчитать просмотр медиакита."""
        
    async def track_download(self, mediakit_id: int) -> None:
        """Засчитать скачивание PDF."""
```

---

### Этап 3: Генерация PDF (5-6 часов)

**Файл:** `src/utils/mediakit_pdf.py` (новый)

```python
"""Генерация PDF медиакита с помощью reportlab."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)


def generate_mediakit_pdf(mediakit_data: dict, logo_bytes: bytes | None = None) -> bytes:
    """
    Сгенерировать PDF медиакита.
    
    Args:
        mediakit_data: Данные из MediakitService.get_mediakit_data().
        logo_bytes: Опционально, логотип в bytes.
    
    Returns:
        PDF файл в bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # 1. Заголовок с логотипом
    if logo_bytes:
        logo = Image(logo_bytes, width=2*cm, height=2*cm)
        elements.append(logo)
    
    # 2. Название и описание
    elements.append(Paragraph(f"📡 {mediakit_data['channel']['title']}", title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # 3. Ключевые метрики (таблица)
    metrics_table = Table([
        ["Подписчики", f"{mediakit_data['metrics']['subscribers']:,}"],
        ["Ср. просмотры", f"{mediakit_data['metrics']['avg_views']:,}"],
        ["ER", f"{mediakit_data['metrics']['er']:.1f}%"],
        ["Постов в день", f"{mediakit_data['metrics']['post_frequency']:.1f}"],
        ["Цена за пост", f"{mediakit_data['price']['amount']} кр"],
    ])
    elements.append(metrics_table)
    
    # 4. График активности (если есть данные)
    # ... использовать reportlab.graphics
    
    # 5. Последние посты (топ-3)
    # ...
    
    # 6. Отзывы (если есть)
    # ...
    
    # 7. Контакты для связи
    elements.append(Paragraph(f"📧 Связь: @{mediakit_data['channel']['username']}", footer_style))
    
    doc.build(elements)
    return buffer.getvalue()
```

**Зависимость:** `reportlab` уже установлен в проекте (проверено в CODE_AUDIT_REPORT).

---

### Этап 4: Handler'ы для владельца (4-5 часов)

**Файл:** `src/bot/handlers/channel_owner.py` (расширение)

```python
@router.callback_query(F.data.startswith("ch_mediakit:"))
async def show_channel_mediakit(callback: CallbackQuery) -> None:
    """Показать медиакит канала (режим редактирования для владельца)."""
    
    channel_id = int(callback.data.split(":")[1])
    
    # Проверить что пользователь владелец
    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        if not channel or channel.owner_user_id != callback.from_user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return
        
        # Получить или создать медиакит
        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)
    
    # Показать меню редактирования
    text = (
        f"📊 <b>Медиакит канала</b>\n\n"
        f"📡 @{channel.username}\n\n"
        f"Статус: {'✅ Публичный' if mediakit.is_public else '🔒 Приватный'}\n"
        f"Просмотров: {mediakit.views_count}\n"
        f"Скачиваний: {mediakit.downloads_count}\n\n"
        f"Настройте медиакит чтобы привлечь больше рекламодателей."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"mediakit_edit:{channel_id}")],
        [InlineKeyboardButton(text="📤 Скачать PDF", callback_data=f"mediakit_download:{channel_id}")],
        [InlineKeyboardButton(text="🔗 Получить ссылку", callback_data=f"mediakit_link:{channel_id}")],
        [InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"mediakit_preview:{channel_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"channel_menu:{channel_id}")],
    ])
    
    await safe_callback_edit(callback, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("mediakit_edit:"))
async def edit_mediakit(callback: CallbackQuery) -> None:
    """Редактирование медиакита."""
    
    channel_id = int(callback.data.split(":")[1])
    
    text = (
        "✏️ <b>Редактирование медиакита</b>\n\n"
        "Выберите что хотите изменить:\n\n"
        "📝 Описание\n"
        "🖼 Логотип\n"
        "🎨 Цвет темы\n"
        "📊 Метрики для отображения\n"
        "🔒 Настройки приватности"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Описание", callback_data=f"mediakit_desc:{channel_id}")],
        [InlineKeyboardButton(text="🖼 Логотип", callback_data=f"mediakit_logo:{channel_id}")],
        [InlineKeyboardButton(text="🎨 Цвет темы", callback_data=f"mediakit_color:{channel_id}")],
        [InlineKeyboardButton(text="📊 Метрики", callback_data=f"mediakit_metrics:{channel_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_mediakit:{channel_id}")],
    ])
    
    await safe_callback_edit(callback, text, reply_markup=keyboard)
```

---

### Этап 5: Публичная страница медиакита (3-4 часа)

**Файл:** `src/bot/handlers/channels_db.py` (расширение)

```python
@router.callback_query(F.data.startswith("channel_mediakit_public:"))
async def show_public_mediakit(callback: CallbackQuery) -> None:
    """Показать публичную страницу медиакита (для рекламодателей)."""
    
    channel_id = int(callback.data.split(":")[1])
    
    # Засчитать просмотр
    await mediakit_service.track_view(channel_id)
    
    # Получить данные
    mediakit_data = await mediakit_service.get_mediakit_data(channel_id)
    
    # Проверить публичность
    if not mediakit_data["mediakit"]["is_public"]:
        await callback.answer("❌ Медиакит недоступен", show_alert=True)
        return
    
    # Сформировать текст
    text = (
        f"📊 <b>Медиакит канала</b>\n\n"
        f"📡 {mediakit_data['channel']['title']}\n"
        f"@{mediakit_data['channel']['username']}\n\n"
        f"{mediakit_data['mediakit']['custom_description'] or mediakit_data['channel']['description']}\n\n"
        f"━━ МЕТРИКИ ━━\n"
        f"👥 Подписчики: {mediakit_data['metrics']['subscribers']:,}\n"
        f"👁 Средние просмотры: {mediakit_data['metrics']['avg_views']:,}\n"
        f"📈 ER: {mediakit_data['metrics']['er']:.1f}%\n"
        f"📝 Постов в день: {mediakit_data['metrics']['post_frequency']:.1f}\n\n"
        f"💰 Цена за пост: {mediakit_data['price']['amount']} кр\n\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Скачать PDF", callback_data=f"mediakit_download_public:{channel_id}")],
        [InlineKeyboardButton(text="📋 Добавить в кампанию", callback_data=f"add_to_campaign:{channel_id}")],
        [InlineKeyboardButton(text="🔙 В каталог", callback_data=ChannelsCB(action="categories"))],
    ])
    
    await safe_callback_edit(callback, text, reply_markup=keyboard)
```

---

### Этап 6: Интеграция с существующими страницами (2-3 часа)

#### 6.1 Детальная страница канала

**Файл:** `src/bot/handlers/channels_db.py`

Добавить кнопку в `view_channel_detail`:

```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 Медиакит", callback_data=f"channel_mediakit_public:{channel_id}")],
    [InlineKeyboardButton(text="📋 Добавить в кампанию", callback_data=f"add_to_campaign:{channel_id}")],
    [InlineKeyboardButton(text="🔙 Назад к каталогу", callback_data=ChannelsCB(action="top_channels"))],
])
```

#### 6.2 Меню канала владельца

**Файл:** `src/bot/handlers/channel_owner.py`

Добавить кнопку в `show_channel_menu`:

```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"ch_settings:{channel_id}"),
        InlineKeyboardButton(text="📊 Медиакит", callback_data=f"ch_mediakit:{channel_id}"),
    ],
    # ... остальные кнопки
])
```

---

### Этап 7: UI/UX улучшения (2-3 часа)

#### 7.1 Загрузка логотипа

```python
@router.callback_query(F.data.startswith("mediakit_logo:"))
async def upload_logo(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить загрузку логотипа."""
    
    await state.set_state(MediakitStates.waiting_logo)
    await state.update_data(mediakit_channel_id=channel_id)
    
    text = (
        "🖼 <b>Загрузка логотипа</b>\n\n"
        "Отправьте изображение логотипа канала.\n\n"
        "Требования:\n"
        "• Формат: PNG, JPG\n"
        "• Размер: до 5 MB\n"
        "• Соотношение: 1:1 (квадрат)\n\n"
        "👇 Отправьте изображение:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"ch_mediakit:{channel_id}")],
    ])
    
    await safe_callback_edit(callback, text, reply_markup=keyboard)


@router.message(MediakitStates.waiting_logo, F.photo)
async def process_logo_upload(message: Message, state: FSMContext) -> None:
    """Обработать загруженный логотип."""
    
    # Получить file_id самого большого фото
    image_file_id = message.photo[-1].file_id
    
    # Сохранить в медиакит
    data = await state.get_data()
    channel_id = data.get("mediakit_channel_id")
    
    async with async_session_factory() as session:
        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)
        mediakit.logo_file_id = image_file_id
        await session.commit()
    
    await message.answer("✅ Логотип сохранён!")
    await state.clear()
```

#### 7.2 Выбор цвета темы

```python
COLOR_PRESETS = [
    ("🔵 Синий", "#1a73e8"),
    ("🔴 Красный", "#d93025"),
    ("🟢 Зелёный", "#188038"),
    ("🟡 Жёлтый", "#f9ab00"),
    ("🟣 Фиолетовый", "#7c4dff"),
    ("⚫ Чёрный", "#202124"),
]

def get_color_selector_kb(channel_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора цвета темы."""
    builder = InlineKeyboardBuilder()
    
    for label, color in COLOR_PRESETS:
        builder.button(
            text=label,
            callback_data=f"mediakit_color_set:{channel_id}:{color}",
        )
    
    builder.button(
        text="🔙 Назад",
        callback_data=f"mediakit_edit:{channel_id}",
    )
    builder.adjust(2, 2, 2)
    
    return builder.as_markup()
```

---

## 📁 СПИСОК ИЗМЕНЁННЫХ ФАЙЛОВ

| Файл | Изменения | Оценка |
|------|-----------|--------|
| `src/db/models/channel_mediakit.py` | Новая модель | 2ч |
| `src/db/migrations/versions/202603XX_0013_*.py` | Миграция | 1ч |
| `src/core/services/mediakit_service.py` | Новый сервис | 5ч |
| `src/utils/mediakit_pdf.py` | Генерация PDF | 5ч |
| `src/bot/handlers/channel_owner.py` | Handler'ы владельца | 4ч |
| `src/bot/handlers/channels_db.py` | Публичная страница | 3ч |
| `src/bot/states/mediakit.py` | FSM состояния | 1ч |
| `src/bot/keyboards/mediakit.py` | Клавиатуры | 2ч |

**Итого:** ~23 часа (4-5 рабочих дней)

---

## 🚀 ПОРЯДОК ВЫПОЛНЕНИЯ

```
День 1:
├─ Этап 1: Модель + миграция (3ч)
└─ Этап 2: MediakitService (5ч)

День 2:
├─ Этап 3: Генерация PDF (5ч)
└─ Этап 4: Handler'ы владельца (4ч)

День 3:
├─ Этап 5: Публичная страница (3ч)
├─ Этап 6: Интеграция (2ч)
└─ Этап 7: UI/UX (3ч)

День 4:
├─ Тестирование (3ч)
└─ Фикс багов + документация (3ч)

День 5:
└─ Резерв на доработки (6ч)
```

---

## ✅ КРИТЕРИИ ПРИЁМКИ

### Базовый функционал:
- [ ] Модель ChannelMediakit создана и миграция применена
- [ ] MediakitService.get_or_create_mediakit() работает
- [ ] MediakitService.get_mediakit_data() возвращает полные данные
- [ ] PDF генерация работает (reportlab)
- [ ] Handler'ы для владельца работают

### Редактирование:
- [ ] Владелец может изменить описание
- [ ] Владелец может загрузить логотип
- [ ] Владелец может выбрать цвет темы
- [ ] Владелец может настроить какие метрики показывать
- [ ] Владелец может включить/выключить публичность

### Публичная страница:
- [ ] Рекламодатель может просмотреть медиакит
- [ ] Счётчик просмотров обновляется
- [ ] Кнопка "Скачать PDF" работает
- [ ] Кнопка "Добавить в кампанию" работает
- [ ] Приватные медиакиты недоступны

### Интеграция:
- [ ] Кнопка "Медиакит" в детальной странице канала
- [ ] Кнопка "Медиакит" в меню владельца
- [ ] Ссылка на медиакит генерируется корректно

### Производительность:
- [ ] Генерация PDF < 3 секунд
- [ ] Загрузка страницы медиакита < 1 секунды
- [ ] Track view/download не блокирует основной поток

---

## 🔗 СВЯЗАННЫЕ ЗАДАЧИ

- **Спринт 0:** Каналы владельцев ✅
- **Спринт 4:** Детальная страница канала ✅
- **Спринт 8:** Отзывы (интеграция в медиакит) ✅
- **B2B Маркетплейс:** (будущий спринт, медиакит — основа)

---

## 🎯 ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ (Future)

### QR-код для скачивания медиакита

```
Генерация QR-кода со ссылкой на медиакит:
• Владелец может распечатать и разместить
• Сканирование → переход на страницу медиакита
```

### A/B тестирование медиакита

```
Владелец может создать 2 версии медиакита:
• Версия A: синий цвет, акцент на ER
• Версия B: красный цвет, акцент на просмотры

Сравнение конверсии в размещения.
```

### Экспорт в другие форматы

```
• PNG (для соцсетей)
• PowerPoint (для презентаций)
• Google Slides (интеграция)
```

### Аналитика медиакита

```
Владелец видит:
• Количество просмотров по дням
• Количество скачиваний PDF
• Конверсия в размещения
• Источники трафика (из каталога, по ссылке, и т.д.)
```

---

## 📊 MOCKUP ДАННЫХ ДЛЯ ТЕСТИРОВАНИЯ

```python
MOCK_MEDIKIT_DATA = {
    "channel": {
        "username": "example_channel",
        "title": "Пример Канала",
        "description": "Канал о технологиях и инновациях",
        "member_count": 15000,
    },
    "mediakit": {
        "custom_description": "Лучший канал о технологиях!",
        "theme_color": "#1a73e8",
        "is_public": True,
        "show_metrics": {
            "subscribers": True,
            "views": True,
            "er": True,
            "frequency": True,
        },
    },
    "metrics": {
        "subscribers": 15000,
        "avg_views": 2500,
        "er": 16.7,
        "post_frequency": 3.5,
        "top_posts": [
            {"text": "Пост 1", "views": 5000, "date": "2026-03-01"},
            {"text": "Пост 2", "views": 4500, "date": "2026-03-05"},
        ],
    },
    "price": {
        "amount": 500,
        "currency": "кр",
    },
    "reviews": {
        "average_rating": 4.8,
        "count": 12,
    },
}
```

---

**Готов к реализации. Приступить?**
