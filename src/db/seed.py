"""Seed script for initial database data."""

import asyncio

from src.db.models.category import Category
from src.db.models.platform_account import PlatformAccount
from src.db.session import async_session_factory

CATEGORIES = [
    {"key": "it", "name_ru": "IT и технологии", "emoji": "💻"},
    {"key": "business", "name_ru": "Бизнес и финансы", "emoji": "💰"},
    {"key": "education", "name_ru": "Образование", "emoji": "🎓"},
    {"key": "retail", "name_ru": "Розница и магазины", "emoji": "👗"},
    {"key": "beauty", "name_ru": "Красота и здоровье", "emoji": "💄"},
    {"key": "food", "name_ru": "Еда и рестораны", "emoji": "🍔"},
    {"key": "travel", "name_ru": "Путешествия", "emoji": "✈️"},
    {"key": "realty", "name_ru": "Недвижимость", "emoji": "🏠"},
    {"key": "auto", "name_ru": "Автомобили", "emoji": "🚗"},
    {"key": "sport", "name_ru": "Спорт", "emoji": "⚽"},
    {"key": "entertainment", "name_ru": "Развлечения", "emoji": "🎬"},
]


async def seed():
    """Seed the database with initial data."""
    async with async_session_factory() as session:
        for data in CATEGORIES:
            session.add(Category(**data))
        session.add(PlatformAccount(id=1))
        await session.commit()
    print("Seed OK")


if __name__ == "__main__":
    asyncio.run(seed())  # type: ignore[no-untyped-call]
