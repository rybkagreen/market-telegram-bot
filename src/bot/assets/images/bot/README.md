# 📸 Изображения для Market Bot

## 📁 Расположение файлов

**Папка:** `src/bot/assets/images/bot/`

| Файл | Размер | Назначение |
|------|--------|------------|
| `main_512x512.jpg` | 512×512 | Основное изображение (аватар, посты) |
| `sub_512x512.jpg` | 512×512 | Дополнительное изображение |
| `banner.jpg` | 784×116 | Баннер для меню |

---

## 💡 Как использовать в боте

### 1. Отправка изображения как фото

```python
from aiogram.types import FSInputFile
from pathlib import Path

# Путь к изображению
BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "assets" / "images" / "bot"

# Отправка основного изображения
async def send_main_image(message):
    photo = FSInputFile(IMAGE_DIR / "main_512x512.jpg")
    
    await message.answer_photo(
        photo=photo,
        caption="🏴 Добро пожаловать в Market Bot!"
    )
```

### 2. Баннер в inline-кнопках

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Создаём меню с баннером
async def show_menu_with_banner(message):
    # Сначала отправляем баннер
    banner = FSInputFile(IMAGE_DIR / "banner.jpg")
    
    # Создаём клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Создать кампанию", callback_data="create_campaign")],
        [InlineKeyboardButton(text="📊 Мои кампании", callback_data="my_campaigns")],
        [InlineKeyboardButton(text="👤 Кабинет", callback_data="cabinet")],
    ])
    
    await message.answer_photo(
        photo=banner,
        caption="Выберите действие:",
        reply_markup=keyboard
    )
```

### 3. Изображение в рассылке

```python
from aiogram.types import BufferedInputFile

# Для массовых рассылок
async def send_broadcast(bot, user_id):
    with open(IMAGE_DIR / "main_512x512.jpg", "rb") as f:
        photo = BufferedInputFile(f.read(), filename="market_bot.jpg")
    
    await bot.send_photo(
        chat_id=user_id,
        photo=photo,
        caption="📣 Новая кампания доступна!"
    )
```

---

## 🎨 Рекомендации

### Для аватара бота:
- Используйте `main_512x512.jpg`
- Загрузите через @BotFather → Edit Botpic
- Telegram автоматически обрежет в круг

### Для постов в канале:
- `main_512x512.jpg` — квадратные посты
- `banner.jpg` — горизонтальные объявления

### Для Mini App:
- Используйте `banner.jpg` в шапке
- `main_512x512.jpg` для иконок

---

## 🔧 Скрипты для обработки

### Изменение размера:
```bash
# Изменить размер изображения
python scripts/resize_for_telegram.py image.jpg 512 512
```

### Проверка требований Telegram:
```bash
# Проверить соответствие требованиям
python scripts/check_telegram_requirements.py image.jpg
```

---

## 📏 Требования Telegram к изображениям

| Тип | Размер | Формат | Макс. вес |
|-----|--------|--------|-----------|
| **Аватар** | 512×512 (мин. 100×100) | JPG, PNG | 5 МБ |
| **Фото в сообщении** | Любое | JPG, PNG | 10 МБ |
| **Preview ссылок** | 1200×630 (1.91:1) | JPG, PNG | 5 МБ |
| **Стикер** | 512×512 | PNG (прозрачность) | 512 КБ |

---

## 📊 Текущие изображения

### main_512x512.jpg
- **Размер:** 512×512 px
- **Формат:** JPEG
- **Вес:** ~50 KB
- **Использование:** Аватар, посты

### sub_512x512.jpg
- **Размер:** 512×512 px
- **Формат:** JPEG
- **Вес:** ~50 KB
- **Использование:** Дополнительные изображения

### banner.jpg
- **Размер:** 784×116 px
- **Формат:** JPEG
- **Вес:** ~20 KB
- **Использование:** Баннер в меню

---

## 🔄 Обновление изображений

1. Подготовьте новые изображения
2. Положите в `tmp/`
3. Запустите скрипт:
   ```bash
   python scripts/resize_for_telegram.py tmp/new_image.jpg 512 512
   ```
4. Переместите в `src/bot/assets/images/bot/`
5. Обновите код если нужно
