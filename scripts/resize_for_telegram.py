"""
Изменение размера изображений для Telegram Bot.

Простой resize без добавления полей.
"""

from PIL import Image
from pathlib import Path
import sys


def resize_image(image_path: str, target_size: tuple, output_dir: str = None):
    """
    Изменить размер изображения.
    
    Args:
        image_path: Путь к исходному изображению.
        target_size: Целевой размер (width, height).
        output_dir: Папка для сохранения.
    
    Returns:
        Путь к сохранённому файлу.
    """
    img = Image.open(image_path)
    original_size = img.size
    
    print(f"\n{'='*60}")
    print(f"ИЗМЕНЕНИЕ РАЗМЕРА")
    print(f"{'='*60}")
    print(f"Файл: {image_path}")
    print(f"Оригинал: {original_size[0]}x{original_size[1]}")
    print(f"Целевой размер: {target_size[0]}x{target_size[1]}")
    
    # Изменяем размер (игнорируем пропорции, просто resize)
    img = img.resize(target_size, Image.Resampling.LANCZOS)
    
    # Сохраняем
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "src" / "bot" / "assets" / "images" / "bot"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(image_path).stem
    output_filename = f"{base_name}_{target_size[0]}x{target_size[1]}.jpg"
    output_path = output_dir / output_filename
    
    # Конвертируем в RGB если нужно
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    img.save(output_path, quality=95, optimize=True)
    
    print(f"\n[OK] Сохранено: {output_path}")
    print(f"Итоговый размер: {img.size[0]}x{img.size[1]}")
    print(f"{'='*60}\n")
    
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/resize_for_telegram.py <image.jpg> [width] [height]")
        print("\nПримеры:")
        print("  python scripts/resize_for_telegram.py tmp/main.jpg 512 512")
        print("  python scripts/resize_for_telegram.py tmp/sub.jpg 512 512")
        sys.exit(1)
    
    image_path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 512
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    
    resize_image(image_path, (width, height))
