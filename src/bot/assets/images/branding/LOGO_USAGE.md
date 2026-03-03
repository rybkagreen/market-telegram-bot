# 📐 Руководство по использованию логотипов RekHarbor

## 📁 Файлы логотипов

| Файл | Описание | Использование |
|------|----------|---------------|
| `*_anchor_text.jpg` | Якорь + текст RekHarbor | Основное лого, шапка бота |
| `*_anchor_circle.jpg` | Якорь в круге | Иконка профиля, аватар |
| `*_full_logo.jpg` | R + RekHarbor (широкий) | Баннеры, заголовки |
| `*_lighthouse.jpg` | Маяк с волной | Тематический контент |
| `*_anchor_simple.jpg` | Простой якорь | Минималистичный дизайн |
| `*_r_anchor.jpg` | Буква R с якорем | Брендирование |
| `*_anchor_chains.jpg` | Якоря с цепями | Декоративный элемент |

## 🎨 Рекомендации

### Для Telegram бота:
- **Аватар бота**: `anchor_circle` (квадратный, хорошо масштабируется)
- **Посты**: `full_logo` или `anchor_text`
- **Кнопки (inline)**: `anchor_simple` (минималистичный)

### Для Mini App:
- **Header**: `full_logo`
- **Favicon**: `anchor_circle` или `r_anchor`
- **Фон**: `lighthouse` или `anchor_chains` (с прозрачностью)

### Для документации:
- **Заголовки**: `full_logo`
- **Иконки разделов**: `anchor_simple`, `lighthouse`

## 📏 Размеры

Все логотипы нарезаны из исходной сетки. 
Рекомендуется использовать SVG/PNG версии для веба.

## 🔄 Конвертация в PNG

```bash
python scripts/convert_to_png.py src/bot/assets/images/branding/
```
