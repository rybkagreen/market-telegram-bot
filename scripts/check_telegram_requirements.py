"""
Проверка изображений на соответствие требованиям Telegram Bot.

Требования Telegram:
1. Avatar (BotPic): 640x640 (мин. 100x100), квадратный, PNG/JPG
2. Link Preview: 1200x630 (мин. 600x315), соотношение 1.91:1
3. Stickers: 512x512, PNG с прозрачностью, белый контур
4. Background: 1920x1080, JPG/PNG
"""

from PIL import Image
from pathlib import Path
import sys


# Требования Telegram
TELEGRAM_REQUIREMENTS = {
    "bot_avatar": {
        "name": "Аватар бота (BotPic)",
        "aspect_ratio": (1, 1),  # Квадрат
        "min_size": (100, 100),
        "recommended_size": (640, 640),
        "formats": [".png", ".jpg", ".jpeg"],
        "description": "Квадратное изображение для профиля бота",
    },
    "link_preview": {
        "name": "Preview для ссылок",
        "aspect_ratio": (1.91, 1),  # 1.91:1
        "min_size": (600, 315),
        "recommended_size": (1200, 630),
        "formats": [".png", ".jpg", ".jpeg"],
        "description": "Изображение для предпросмотра ссылок",
    },
    "mini_app_banner": {
        "name": "Баннер Mini App",
        "aspect_ratio": (1.91, 1),
        "min_size": (640, 336),
        "recommended_size": (1280, 672),
        "formats": [".png", ".jpg", ".jpeg"],
        "description": "Баннер для Telegram Mini App",
    },
    "sticker": {
        "name": "Стикер",
        "aspect_ratio": (1, 1),  # Квадрат
        "exact_size": (512, 512),
        "formats": [".png"],  # Только PNG с прозрачностью
        "description": "Стикер для Telegram (требует прозрачности)",
    },
    "chat_background": {
        "name": "Фон чата",
        "aspect_ratio": (16, 9),
        "min_size": (1280, 720),
        "recommended_size": (1920, 1080),
        "formats": [".png", ".jpg", ".jpeg"],
        "description": "Фон для чата бота",
    },
}


def check_aspect_ratio(width: int, height: int, target_ratio: tuple) -> tuple:
    """
    Проверить соотношение сторон.
    
    Returns:
        (is_match, actual_ratio, difference)
    """
    target = target_ratio[0] / target_ratio[1]
    actual = width / height
    diff = abs(actual - target)
    
    # Допускаем отклонение 5%
    is_match = diff < (target * 0.05)
    
    return is_match, actual, diff


def analyze_image(image_path: str) -> dict:
    """
    Проанализировать изображение на соответствие требованиям.
    """
    img = Image.open(image_path)
    width, height = img.size
    mode = img.mode
    format = img.format
    
    result = {
        "file": image_path,
        "size": (width, height),
        "aspect_ratio": width / height,
        "mode": mode,
        "format": format,
        "matches": {},
        "recommendations": [],
    }
    
    # Проверяем каждое требование
    for req_name, req in TELEGRAM_REQUIREMENTS.items():
        is_match = False
        reason = ""
        
        # Проверка формата
        format_match = Path(image_path).suffix.lower() in req["formats"]
        
        # Проверка размера
        if "exact_size" in req:
            size_match = (width, height) == req["exact_size"]
            if not size_match:
                reason = f"Точный размер должен быть {req['exact_size']}"
        else:
            min_w, min_h = req["min_size"]
            size_match = width >= min_w and height >= min_h
            if not size_match:
                reason = f"Минимальный размер {min_w}x{min_h}"
        
        # Проверка соотношения сторон
        ratio_match, actual_ratio, diff = check_aspect_ratio(width, height, req["aspect_ratio"])
        
        # Итоговое соответствие
        is_match = format_match and size_match and ratio_match
        
        result["matches"][req_name] = {
            "match": is_match,
            "name": req["name"],
            "reason": reason if not is_match else "OK",
            "recommended": req.get("recommended_size"),
        }
        
        # Если подходит, добавляем рекомендацию
        if is_match:
            result["recommendations"].append(f"✓ Подходит для: {req['name']}")
    
    # Дополнительные проверки
    if mode == "P" or (mode == "RGB" and "transparency" in img.info):
        result["has_transparency"] = True
    else:
        result["has_transparency"] = False
    
    # Проверка на стикер (требует прозрачности)
    if not result["has_transparency"] and Path(image_path).suffix.lower() == ".png":
        result["recommendations"].append("⚠ Для стикера нужна прозрачность (PNG с alpha)")
    
    # Проверка качества
    file_size = Path(image_path).stat().st_size / 1024  # KB
    result["file_size_kb"] = file_size
    
    if file_size > 512:
        result["recommendations"].append(f"⚠ Большой размер файла: {file_size:.1f} KB (рекомендуется < 512 KB)")
    
    return result


def print_analysis(analysis: dict):
    """
    Вывести результат анализа.
    """
    print(f"\n{'='*70}")
    print(f"АНАЛИЗ: {analysis['file']}")
    print(f"{'='*70}")
    print(f"Размер: {analysis['size'][0]}x{analysis['size'][1]} px")
    print(f"Соотношение: {analysis['aspect_ratio']:.2f}")
    print(f"Формат: {analysis['format']} ({analysis['mode']})")
    print(f"Размер файла: {analysis['file_size_kb']:.1f} KB")
    print(f"Прозрачность: {'Есть' if analysis.get('has_transparency') else 'Нет'}")
    
    print(f"\n{'='*70}")
    print(f"СООТВЕТСТВИЕ ТРЕБОВАНИЯМ TELEGRAM")
    print(f"{'='*70}")
    
    for req_name, match_info in analysis["matches"].items():
        status = "✓" if match_info["match"] else "✗"
        print(f"{status} {match_info['name']}")
        if not match_info["match"] and match_info["reason"]:
            print(f"    {match_info['reason']}")
        if match_info["recommended"]:
            print(f"    Рекомендуется: {match_info['recommended']}")
    
    print(f"\n{'='*70}")
    print(f"РЕКОМЕНДАЦИИ")
    print(f"{'='*70}")
    
    if analysis["recommendations"]:
        for rec in analysis["recommendations"]:
            print(f"{rec}")
    else:
        print("Все требования соблюдены!")


def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/check_telegram_requirements.py <image.jpg>")
        print("  python scripts/check_telegram_requirements.py tmp/*.jpg")
        sys.exit(1)
    
    image_files = sys.argv[1:]
    
    for image_file in image_files:
        if Path(image_file).exists():
            analysis = analyze_image(image_file)
            print_analysis(analysis)
        else:
            print(f"[ERROR] Файл не найден: {image_file}")


if __name__ == "__main__":
    main()
