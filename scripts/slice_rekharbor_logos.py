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
    
    Структура (в процентах):
    - Row 1 (0-28%): 2 логотипа (якорь+текст, якорь в круге)
    - Row 2 (28-42%): 1 логотип на полную ширину (R + RekHarbor)
    - Row 3 (42-68%): 2 логотипа (маяк, простой якорь)
    - Row 4 (68-100%): 2 логотипа (R с якорем, RH якоря)
    
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
    
    # Точные координаты в процентах [left, top, right, bottom]
    logos = [
        {
            "name": "anchor_with_text",
            "description": "Якорь + текст RekHarbor",
            "pct": (0, 0, 50, 28),
        },
        {
            "name": "anchor_in_circle",
            "description": "Якорь в круге",
            "pct": (50, 0, 100, 28),
        },
        {
            "name": "r_full_logo",
            "description": "R + RekHarbor (полная ширина)",
            "pct": (0, 28, 100, 42),
        },
        {
            "name": "lighthouse",
            "description": "Маяк с волной",
            "pct": (0, 42, 50, 68),
        },
        {
            "name": "simple_anchor",
            "description": "Простой якорь",
            "pct": (50, 42, 100, 68),
        },
        {
            "name": "r_with_anchor",
            "description": "Буква R с якорем",
            "pct": (0, 68, 50, 100),
        },
        {
            "name": "rh_anchors",
            "description": "RH якоря с цепями",
            "pct": (50, 68, 100, 100),
        },
    ]
    
    print(f"\nСтруктура сетки:")
    print(f"  Row 1: 2 логотипа (0-28%)")
    print(f"  Row 2: 1 логотип fullWidth (28-42%)")
    print(f"  Row 3: 2 логотипа (42-68%)")
    print(f"  Row 4: 2 логотипа (68-100%)")
    print(f"\nВсего логотипов: {len(logos)}")
    print(f"\n{'='*60}")
    print(f"НАРЕЗКА")
    print(f"{'='*60}")
    
    output_files = []
    
    for logo in logos:
        # Конвертация процентов в пиксели
        left_pct, top_pct, right_pct, bottom_pct = logo["pct"]
        
        box = (
            int(width * left_pct / 100),
            int(height * top_pct / 100),
            int(width * right_pct / 100),
            int(height * bottom_pct / 100),
        )
        
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
