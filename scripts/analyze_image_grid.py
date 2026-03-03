"""
Скрипт для анализа и нарезки сет изображений.

Автоматически определяет:
- Количество изображений в сете
- Пропорции каждого изображения
- Расположение (горизонтальное/вертикальное)
"""

from PIL import Image
from pathlib import Path
import sys


def analyze_image_grid(image_path: str) -> dict:
    """
    Анализировать изображение и определить структуру сетки.
    
    Returns:
        Словарь с информацией о сетке изображений.
    """
    img = Image.open(image_path)
    width, height = img.size
    
    print(f"\n{'='*60}")
    print(f"АНАЛИЗ ИЗОБРАЖЕНИЯ")
    print(f"{'='*60}")
    print(f"Файл: {image_path}")
    print(f"Общий размер: {width}x{height} px")
    print(f"Пропорции: {width/height:.2f}")
    
    # Определяем ориентацию
    is_horizontal = width > height
    
    print(f"\nОриентация: {'горизонтальная' if is_horizontal else 'вертикальная'}")
    
    # Предположения о сетке
    grids_to_try = []
    
    if is_horizontal:
        # Горизонтальное изображение - ищем 6 квадратных + 1 горизонтальное
        # Пробуем разные варианты
        grids_to_try = [
            # 6 squares horizontal + 1 horizontal banner
            {"layout": "6x1_horizontal + 1_banner", "squares": 6, "banner": True},
            # 7 squares horizontal
            {"layout": "7x1_horizontal", "squares": 7, "banner": False},
            # 3x2 grid + banner
            {"layout": "3x2_grid + banner", "squares": 6, "banner": True},
        ]
    else:
        # Вертикальное изображение
        grids_to_try = [
            # 6 squares vertical + 1 horizontal banner at top/bottom
            {"layout": "6x1_vertical + 1_banner", "squares": 6, "banner": True},
            # 7 squares vertical
            {"layout": "7x1_vertical", "squares": 7, "banner": False},
            # 2x3 grid + banner
            {"layout": "2x3_grid + banner", "squares": 6, "banner": True},
        ]
    
    print(f"\n{'='*60}")
    print(f"ВОЗМОЖНЫЕ ВАРИАНТЫ СЕТКИ")
    print(f"{'='*60}")
    
    results = []
    
    for grid in grids_to_try:
        print(f"\nВариант: {grid['layout']}")
        
        if grid['banner']:
            # С баннером
            if is_horizontal:
                # Горизонтальный баннер сверху/снизу
                # Пробуем разные высоты баннера
                for banner_height_ratio in [0.4, 0.35, 0.33]:
                    banner_height = int(height * banner_height_ratio)
                    remaining_height = height - banner_height
                    square_size = remaining_height // grid['squares']
                    
                    print(f"  - Баннер: {width}x{banner_height} (ratio: {banner_height_ratio})")
                    print(f"    Квадраты: {square_size}x{square_size} ({grid['squares']} шт)")
                    
                    results.append({
                        "type": "banner_horizontal",
                        "banner": (0, 0, width, banner_height),
                        "squares": grid['squares'],
                        "square_size": square_size,
                        "square_positions": calculate_square_positions(
                            width, remaining_height, grid['squares'], 
                            offset_y=banner_height,
                            orientation='horizontal'
                        )
                    })
            else:
                # Вертикальное - баннер слева/справа или сверху/снизу
                for banner_position in ['top', 'bottom']:
                    for banner_height_ratio in [0.14, 0.15, 0.16]:
                        banner_height = int(height * banner_height_ratio)
                        remaining_height = height - banner_height
                        
                        # 6 квадратов в 2 колонки
                        cols = 2
                        rows = 3
                        square_width = width // cols
                        square_height = remaining_height // rows
                        
                        print(f"  - Баннер ({banner_position}): {width}x{banner_height}")
                        print(f"    Квадраты: {square_width}x{square_height} ({grid['squares']} шт, {cols}x{rows})")
                        
                        results.append({
                            "type": f"banner_{banner_position}",
                            "banner": (0, 0 if banner_position == 'top' else height - banner_height, 
                                      width, banner_height),
                            "squares": grid['squares'],
                            "square_size": (square_width, square_height),
                            "square_positions": calculate_square_positions_2d(
                                width, remaining_height, cols, rows,
                                offset_y=0 if banner_position == 'bottom' else banner_height
                            )
                        })
        else:
            # Без баннера - просто квадраты
            if is_horizontal:
                square_size = height
                num_squares = width // square_size
                print(f"  - {num_squares} квадратов: {square_size}x{square_size}")
            else:
                square_size = width
                num_squares = height // square_size
                print(f"  - {num_squares} квадратов: {square_size}x{square_size}")
    
    return {
        "width": width,
        "height": height,
        "is_horizontal": is_horizontal,
        "variants": results
    }


def calculate_square_positions(width: int, height: int, num_squares: int, 
                               offset_x: int = 0, offset_y: int = 0,
                               orientation: str = 'horizontal') -> list:
    """
    Вычислить позиции для квадратных изображений.
    """
    positions = []
    
    if orientation == 'horizontal':
        # Горизонтальное расположение
        square_size = height
        for i in range(num_squares):
            x = offset_x + (i * square_size)
            y = offset_y
            positions.append((x, y, x + square_size, y + square_size))
    else:
        # Вертикальное расположение
        square_size = width
        for i in range(num_squares):
            x = offset_x
            y = offset_y + (i * square_size)
            positions.append((x, y, x + square_size, y + square_size))
    
    return positions


def calculate_square_positions_2d(width: int, height: int, 
                                   cols: int, rows: int,
                                   offset_x: int = 0, offset_y: int = 0) -> list:
    """
    Вычислить позиции для 2D сетки квадратов.
    """
    positions = []
    square_width = width // cols
    square_height = height // rows
    
    for row in range(rows):
        for col in range(cols):
            x = offset_x + (col * square_width)
            y = offset_y + (row * square_height)
            positions.append((x, y, x + square_width, y + square_height))
    
    return positions


def slice_image(image_path: str, variant: dict, output_dir: str = None):
    """
    Нарезать изображение по указанному варианту сетки.
    """
    img = Image.open(image_path)
    
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "src" / "bot" / "assets" / "images"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(image_path).stem
    
    print(f"\n{'='*60}")
    print(f"НАРЕЗКА ИЗОБРАЖЕНИЯ")
    print(f"{'='*60}")
    
    output_files = []
    
    # Вырезаем баннер если есть
    if 'banner' in variant:
        banner_box = variant['banner']
        banner = img.crop(banner_box)
        banner_path = output_dir / f"{base_name}_banner.jpg"
        banner.save(banner_path, quality=90, optimize=True)
        output_files.append(str(banner_path))
        print(f"[OK] Баннер: {banner.size[0]}x{banner.size[1]} -> {banner_path.name}")
    
    # Вырезаем квадраты
    if 'square_positions' in variant:
        positions = variant['square_positions']
        
        for i, (x1, y1, x2, y2) in enumerate(positions):
            square = img.crop((x1, y1, x2, y2))
            square_path = output_dir / f"{base_name}_square_{i+1}.jpg"
            square.save(square_path, quality=90, optimize=True)
            output_files.append(str(square_path))
            print(f"[OK] Квадрат {i+1}: {square.size[0]}x{square.size[1]} -> {square_path.name}")
    
    print(f"\n[OK] Всего создано файлов: {len(output_files)}")
    print(f"[OK] Папка: {output_dir}")
    
    return output_files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/analyze_image_grid.py <image.jpg>")
        print("  python scripts/analyze_image_grid.py <image.jpg> --slice <variant_number>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Анализируем
    analysis = analyze_image_grid(image_path)
    
    # Если есть аргумент --slice, нарезаем
    if "--slice" in sys.argv:
        try:
            variant_idx = int(sys.argv[sys.argv.index("--slice") + 1])
            if 0 <= variant_idx < len(analysis['variants']):
                slice_image(image_path, analysis['variants'][variant_idx])
            else:
                print(f"Ошибка: вариант {variant_idx} не найден")
        except (IndexError, ValueError):
            print("Ошибка: укажите номер варианта после --slice")
