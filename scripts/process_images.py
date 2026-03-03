"""
Скрипт для обработки изображений для Market Bot.

Использование:
    python scripts/process_images.py <input_image.jpg>

Автоматически создаёт:
1. Баннер для кампаний (1200x628)
2. Квадратную версию (1080x1080)
3. Миниатюру (400x400)
4. Иконку (256x256)
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("❌ PIL не установлен! Установите: pip install Pillow")
    sys.exit(1)


# Размеры для разных типов изображений
SIZES = {
    "banner": (1200, 628),      # Баннер для кампаний (Telegram link preview)
    "square": (1080, 1080),     # Квадратное изображение (посты)
    "thumbnail": (400, 400),    # Миниатюра (превью)
    "icon": (256, 256),         # Иконка (кнопки, меню)
    "small_icon": (64, 64),     # Маленькая иконка
}


def crop_center(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """
    Обрезать изображение по центру до целевого размера.
    
    Args:
        image: Исходное изображение.
        target_size: Целевой размер (width, height).
    
    Returns:
        Обрезанное изображение.
    """
    original_width, original_height = image.size
    target_width, target_height = target_size
    
    # Вычисляем коэффициенты масштабирования
    width_ratio = target_width / original_width
    height_ratio = target_height / original_height
    
    # Выбираем больший коэффициент чтобы покрыть всю область
    scale_ratio = max(width_ratio, height_ratio)
    
    # Масштабируем изображение
    new_width = int(original_width * scale_ratio)
    new_height = int(original_height * scale_ratio)
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Обрезаем по центру
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    
    return image.crop((left, top, right, bottom))


def add_padding(image: Image.Image, target_size: tuple[int, int], 
                color: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """
    Добавить отступы (padding) вокруг изображения.
    
    Args:
        image: Исходное изображение.
        target_size: Целевой размер.
        color: Цвет отступов (RGB).
    
    Returns:
        Изображение с отступами.
    """
    new_image = Image.new('RGB', target_size, color)
    
    # Вычисляем позицию для центрирования
    x = (target_size[0] - image.size[0]) // 2
    y = (target_size[1] - image.size[1]) // 2
    
    new_image.paste(image, (x, y))
    return new_image


def process_image(input_path: str, output_dir: str = None) -> dict[str, str]:
    """
    Обработать изображение и создать все необходимые размеры.
    
    Args:
        input_path: Путь к исходному изображению.
        output_dir: Папка для сохранения (по умолчанию assets/images).
    
    Returns:
        Словарь с путями к созданным файлам.
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        return {}
    
    # Определяем output директорию
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "src" / "bot" / "assets" / "images"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Открываем изображение
    print(f"Processing: {input_path.name}")
    print(f"   Original size: {Image.open(input_path).size}")
    
    with Image.open(input_path) as img:
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        output_files = {}
        
        # Создаём все размеры
        for size_name, target_size in SIZES.items():
            print(f"   Creating {size_name}: {target_size[0]}x{target_size[1]}...")
            
            # Обрезаем по центру
            cropped = crop_center(img, target_size)
            
            # Сохраняем
            output_filename = f"{input_path.stem}_{size_name}{input_path.suffix}"
            output_path = output_dir / output_filename
            
            cropped.save(output_path, quality=90, optimize=True)
            output_files[size_name] = str(output_path)
            
            print(f"   [OK] {output_filename}")
        
        print(f"\n[OK] Done! Files saved to: {output_dir}")
        return output_files


def create_campaign_banner(input_path: str, title: str = "Market Bot", 
                           output_path: str = None) -> str:
    """
    Создать баннер для кампании с текстом.
    
    Args:
        input_path: Путь к исходному изображению.
        title: Заголовок для баннера.
        output_path: Путь для сохранения.
    
    Returns:
        Путь к сохранённому файлу.
    """
    from PIL import ImageDraw, ImageFont
    
    input_path = Path(input_path)
    
    if output_path is None:
        output_dir = Path(__file__).parent.parent / "src" / "bot" / "assets" / "images" / "campaigns"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_banner{input_path.suffix}"
    
    # Создаём баннер
    banner = crop_center(Image.open(input_path), SIZES["banner"])
    
    # Добавляем текст (опционально)
    draw = ImageDraw.Draw(banner)
    
    # Пытаемся загрузить шрифт
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    # Добавляем затемнение снизу для читаемости текста
    width, height = banner.size
    overlay = Image.new('RGBA', banner.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.rectangle([(0, height - 150), (width, height)], 
                          fill=(0, 0, 0, 128))
    banner = Image.alpha_composite(banner.convert('RGBA'), overlay)
    
    # Добавляем текст
    draw = ImageDraw.Draw(banner)
    draw.text((20, height - 130), title, font=font, fill=(255, 255, 255, 255))
    
    # Сохраняем
    banner.convert('RGB').save(output_path, quality=90, optimize=True)
    
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/process_images.py <image.jpg> [output_dir]")
        print("\nПример:")
        print("  python scripts/process_images.py tmp/my_image.jpg")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = process_image(input_file, output_dir)
    
    if result:
        print("\n📊 Созданные файлы:")
        for size_name, file_path in result.items():
            print(f"   {size_name}: {file_path}")
