"""
Константы контент-фильтра Market Bot.
3-уровневая система проверки: regex → pymorphy3 → LLM
"""

# Пороги для перехода между уровнями
LEVEL1_THRESHOLD: float = 0.1  # Если score > 0.1, переходим на уровень 2
LEVEL2_THRESHOLD: float = 0.3  # Если score > 0.3, переходим на уровень 3
LEVEL3_THRESHOLD: float = 0.5  # Если LLM score > 0.5, контент блокируется

# Заблокированные категории (8 категорий)
BLOCKED_CATEGORIES: list[str] = [
    "drugs",  # Наркотики
    "terrorism",  # Терроризм
    "weapons",  # Оружие
    "adult",  # Контент 18+
    "fraud",  # Мошенничество
    "suicide",  # Суицид
    "extremism",  # Экстремизм
    "gambling",  # Азартные игры
]
