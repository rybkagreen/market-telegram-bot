"""
Скрипт для нарезки сетки логотипов RekHarbor.

Структура: 2 колонки × 4 ряда
- Row 1 (0-25%): 2 логотипа (якорь+текст, якорь в круге)
- Row 2 (25-45%): 1 логотип на полную ширину (R + RekHarbor)
- Row 3 (45-70%): 2 логотипа (маяк, простой якорь)
- Row 4 (70-100%): 2 логотипа (R с якорем, якоря с цепями)

Итого: 7 логотипов
"""

from PIL import Image
from pathlib import Path
import sys


def slice_rekharbor_logos(image_path: str, output_dir: str = None):
    """
    Нарезать логотипы RekHarbor из сетки.
    
    Args:
        image_path: Путь к исходному изображению.
        output_dir: Папка для сохранения.
    
    Returns:
        Список путей к сохранённым файлам.
    """
    img = Image.open(image_path)
    width, height = img.size
    
    print(f"\n{'='*60}")
    print(f"НАРЕЗКА ЛОГОТИПОВ REKHARBOR")
    print(f"{'='*60}")
    print(f"Исходное изображение: {width}x{height} px")
    
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "src" / "bot" / "assets" / "images" / "branding"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(image_path).stem
    
    # Вычисляем координаты на основе структуры 2×4 с fullWidth row
    # Row heights (проценты от общей высоты)
    row1_height = int(height * 0.25)    # 0-25%
    row2_height = int(height * 0.20)    # 25-45%
    row3_height = int(height * 0.25)    # 45-70%
    row4_height = int(height * 0.30)    # 70-100%
    
    # Y координаты для каждого ряда
    row1_y = 0
    row2_y = row1_height
    row3_y = row1_height + row2_height
    row4_y = row1_height + row2_height + row3_height
    
    # Половина ширины
    half_width = width // 2
    
    # Определяем все логотипы
    logos = [
        {
            "name": "anchor_text",
            "description": "Якорь + RekHarbor текст",
            "box": (0, row1_y, half_width, row1_y + row1_height),
        },
        {
            "name": "anchor_circle",
            "description": "Якорь в круге",
            "box": (half_width, row1_y, width, row1_y + row1_height),
        },
        {
            "name": "full_logo",
            "description": "R + RekHarbor (полная ширина)",
            "box": (0, row2_y, width, row2_y + row2_height),
        },
        {
            "name": "lighthouse",
            "description": "Маяк с волной",
            "box": (0, row3_y, half_width, row3_y + row3_height),
        },
        {
            "name": "anchor_simple",
            "description": "Простой якорь",
            "box": (half_width, row3_y, width, row3_y + row3_height),
        },
        {
            "name": "r_anchor",
            "description": "Буква R с якорем",
            "box": (0, row4_y, half_width, row4_y + row4_height),
        },
        {
            "name": "anchor_chains",
            "description": "Якоря с цепями",
            "box": (half_width, row4_y, width, row4_y + row4_height),
        },
    ]
    
    print(f"\nСтруктура сетки:")
    print(f"  Row 1: 2 логотипа (0-{row1_height}px)")
    print(f"  Row 2: 1 логотип fullWidth ({row1_height}-{row2_y + row2_height}px)")
    print(f"  Row 3: 2 логотипа ({row3_y}-{row3_y + row3_height}px)")
    print(f"  Row 4: 2 логотипа ({row4_y}-{height}px)")
    print(f"\nВсего логотипов: {len(logos)}")
    print(f"\n{'='*60}")
    print(f"НАРЕЗКА")
    print(f"{'='*60}")
    
    output_files = []
    
    for logo in logos:
        box = logo["box"]
        logo_img = img.crop(box)
        
        # Сохраняем
        output_filename = f"{base_name}_{logo['name']}.jpg"
        output_path = output_dir / output_filename
        
        # Конвертируем в RGB если нужно
        if logo_img.mode in ('RGBA', 'P'):
            logo_img = logo_img.convert('RGB')
        
        logo_img.save(output_path, quality=95, optimize=True)
        output_files.append(str(output_path))
        
        print(f"[OK] {logo['name']}: {logo_img.size[0]}x{logo_img.size[1]} -> {output_filename}")
        print(f"     {logo['description']}")
    
    print(f"\n{'='*60}")
    print(f"[OK] ГОТОВО!")
    print(f"Всего создано файлов: {len(output_files)}")
    print(f"Папка: {output_dir}")
    print(f"{'='*60}\n")
    
    return output_files


def create_usage_guide(output_dir: str):
    """
    Создать руководство по использованию логотипов.
    """
    guide_path = Path(output_dir) / "LOGO_USAGE.md"
    
    content = """# 📐 Руководство по использованию логотипов RekHarbor

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
"""
    
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Создано руководство: {guide_path}")
    return str(guide_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/slice_rekharbor_logos.py <image.jpg>")
        print("\nПример:")
        print("  python scripts/slice_rekharbor_logos.py tmp/rekharbor_logos.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        print(f"[ERROR] Файл не найден: {image_path}")
        sys.exit(1)
    
    output_files = slice_rekharbor_logos(image_path)
    
    if output_files:
        # Создаём руководство
        output_dir = Path(output_files[0]).parent
        create_usage_guide(output_dir)
        
        print("\n💡 Следующие шаги:")
        print("1. Проверьте качество нарезки")
        print("2. При необходимости обрежьте белые поля")
        print("3. Конвертируйте в PNG для веба")
        print("4. Добавьте в бота через send_photo()")
