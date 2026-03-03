"""
Подгонка изображений под требования Telegram.

Telegram требования:
1. Avatar: 640x640 (1:1 квадрат)
2. Link Preview: 1200x630 (1.91:1)
3. Post Image: 1080x1080 (1:1 квадрат) или 1080x1350 (4:5 вертикальный)
4. Banner: 1200x628 (1.91:1 горизонтальный)

Скрипт меняет пропорции через padding (добавление полей), а не обрезку.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys


# Целевые пропорции Telegram
TELEGRAM_FORMATS = {
    "square_1_1": {
        "name": "Квадрат (1:1)",
        "ratio": 1.0,
        "recommended_size": (1080, 1080),
        "use_case": "Аватар, посты в канале",
    },
    "portrait_4_5": {
        "name": "Портрет (4:5)",
        "ratio": 0.8,
        "recommended_size": (1080, 1350),
        "use_case": "Вертикальные посты",
    },
    "landscape_1_91_1": {
        "name": "Ландшафт (1.91:1)",
        "ratio": 1.91,
        "recommended_size": (1200, 628),
        "use_case": "Preview ссылок, баннеры",
    },
    "avatar_640": {
        "name": "Аватар (640x640)",
        "ratio": 1.0,
        "exact_size": (640, 640),
        "use_case": "Аватар бота",
    },
}


def add_padding(image: Image.Image, target_size: tuple, 
                color: tuple = (255, 255, 255)) -> Image.Image:
    """
    Добавить поля (padding) вокруг изображения до целевого размера.
    
    Args:
        image: Исходное изображение.
        target_size: Целевой размер (width, height).
        color: Цвет полей (RGB).
    
    Returns:
        Изображение с полями.
    """
    new_image = Image.new('RGB', target_size, color)
    
    # Вычисляем позицию для центрирования
    x = (target_size[0] - image.size[0]) // 2
    y = (target_size[1] - image.size[1]) // 2
    
    new_image.paste(image, (x, y))
    return new_image


def resize_to_fit(image: Image.Image, max_size: tuple) -> Image.Image:
    """
    Масштабировать изображение чтобы поместилось в max_size.
    """
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image


def adjust_proportions(image_path: str, output_format: str = "square_1_1",
                       output_dir: str = None, add_shadow: bool = True):
    """
    Подогнать пропорции изображения под формат Telegram.
    
    Args:
        image_path: Путь к исходному изображению.
        output_format: Целевой формат (square_1_1, portrait_4_5, landscape_1_91_1, avatar_640).
        output_dir: Папка для сохранения.
        add_shadow: Добавить тень для красоты.
    
    Returns:
        Путь к сохранённому файлу.
    """
    img = Image.open(image_path)
    original_size = img.size
    
    print(f"\n{'='*60}")
    print(f"ПОДГОНКА ПРОПОРЦИЙ")
    print(f"{'='*60}")
    print(f"Файл: {image_path}")
    print(f"Оригинал: {original_size[0]}x{original_size[1]}")
    
    if output_format not in TELEGRAM_FORMATS:
        print(f"[ERROR] Неизвестный формат: {output_format}")
        return None
    
    format_info = TELEGRAM_FORMATS[output_format]
    print(f"Целевой формат: {format_info['name']}")
    print(f"Использование: {format_info['use_case']}")
    
    # Определяем целевой размер
    if "exact_size" in format_info:
        target_width, target_height = format_info["exact_size"]
    else:
        target_width, target_height = format_info["recommended_size"]
    
    print(f"Целевой размер: {target_width}x{target_height}")
    
    # Вычисляем соотношение сторон
    original_ratio = original_size[0] / original_size[1]
    target_ratio = target_width / target_height
    
    print(f"Оригинал пропорция: {original_ratio:.2f}")
    print(f"Целевая пропорция: {target_ratio:.2f}")
    
    # Масштабируем изображение чтобы поместилось в целевой размер
    img = img.copy()
    
    if original_ratio > target_ratio:
        # Изображение шире чем нужно - масштабируем по ширине
        new_width = target_width
        new_height = int(target_width / original_ratio)
    else:
        # Изображение уже чем нужно - масштабируем по высоте
        new_height = target_height
        new_width = int(target_height * original_ratio)
    
    img = resize_to_fit(img, (new_width, new_height))
    print(f"После масштабирования: {img.size[0]}x{img.size[1]}")
    
    # Добавляем поля (padding)
    if add_shadow:
        # Добавляем тень для красоты
        shadow_offset = 10
        shadow_color = (0, 0, 0)
        padded_size = (target_width - shadow_offset * 2, target_height - shadow_offset * 2)
        
        # Создаём изображение с тенью
        shadow_img = Image.new('RGB', padded_size, (255, 255, 255))
        
        # Центрируем изображение
        x = (padded_size[0] - img.size[0]) // 2
        y = (padded_size[1] - img.size[1]) // 2
        
        # Добавляем тень
        for i in range(shadow_offset):
            shadow = Image.new('RGB', img.size, shadow_color)
            shadow_img.paste(shadow, (x + i, y + shadow_offset))
        
        # Вставляем основное изображение
        shadow_img.paste(img, (x, y))
        
        # Теперь добавляем белые поля
        final_img = add_padding(shadow_img, (target_width, target_height), color=(255, 255, 255))
    else:
        # Просто добавляем белые поля
        final_img = add_padding(img, (target_width, target_height), color=(255, 255, 255))
    
    # Сохраняем
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "tmp" / "adjusted"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(image_path).stem
    output_filename = f"{base_name}_{output_format}.jpg"
    output_path = output_dir / output_filename
    
    # Конвертируем в RGB если нужно
    if final_img.mode in ('RGBA', 'P'):
        final_img = final_img.convert('RGB')
    
    final_img.save(output_path, quality=95, optimize=True)
    
    print(f"\n[OK] Сохранено: {output_path}")
    print(f"Итоговый размер: {final_img.size[0]}x{final_img.size[1]}")
    print(f"{'='*60}\n")
    
    return str(output_path)


def batch_adjust(image_paths: list, output_format: str = "square_1_1"):
    """
    Обработать несколько изображений.
    """
    results = []
    
    for image_path in image_paths:
        if Path(image_path).exists():
            result = adjust_proportions(image_path, output_format)
            if result:
                results.append(result)
        else:
            print(f"[ERROR] Файл не найден: {image_path}")
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/adjust_telegram_proportions.py <image.jpg> [format]")
        print("\nФорматы:")
        print("  square_1_1      - Квадрат (1:1) для аватара и постов")
        print("  portrait_4_5    - Портрет (4:5) для вертикальных постов")
        print("  landscape_1_91_1 - Ландшафт (1.91:1) для баннеров и preview")
        print("  avatar_640      - Аватар 640x640")
        print("\nПримеры:")
        print("  python scripts/adjust_telegram_proportions.py tmp/banner.jpg landscape_1_91_1")
        print("  python scripts/adjust_telegram_proportions.py tmp/main.jpg square_1_1")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else "square_1_1"
    
    adjust_proportions(image_path, output_format)
