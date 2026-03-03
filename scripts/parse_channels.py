"""
Скрипт для обновления данных каналов через Telegram API.
Запускает парсер для указанных категорий с соблюдением лимитов Telegram.

Использование:
    python scripts/parse_channels.py --category бизнес
    python scripts/parse_channels.py --category all
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tasks.parser_tasks import refresh_chat_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Категории для парсинга (в порядке приоритета)
CATEGORIES = [
    "business",      # Бизнес
    "marketing",     # Маркетинг
    "it",            # IT
    "lifestyle",     # Lifestyle
    "health",        # Здоровье
    "education",     # Образование
    "news",          # Новости
]

def main():
    parser = argparse.ArgumentParser(description='Parse Telegram channels')
    parser.add_argument(
        '--category',
        type=str,
        default='all',
        help='Category to parse (or "all" for all categories)'
    )
    args = parser.parse_args()

    if args.category == 'all':
        logger.info('Starting parser for ALL categories...')
        for category in CATEGORIES:
            logger.info(f'Parsing category: {category}')
            try:
                result = refresh_chat_database(query_category=category)
                logger.info(f'Category {category} completed: {result}')
            except Exception as e:
                logger.error(f'Error parsing {category}: {e}')
    else:
        logger.info(f'Starting parser for category: {args.category}')
        result = refresh_chat_database(query_category=args.category)
        logger.info(f'Completed: {result}')

if __name__ == '__main__':
    main()
