"""Seed script for categories table."""

import asyncio

from sqlalchemy import text

from src.db.session import async_session_factory

CATEGORIES = [
    {"slug": "business",  "name_ru": "Бизнес",          "emoji": "💼", "sort_order": 1},
    {"slug": "marketing", "name_ru": "Маркетинг",       "emoji": "📣", "sort_order": 2},
    {"slug": "it",        "name_ru": "IT и технологии", "emoji": "💻", "sort_order": 3},
    {"slug": "finance",   "name_ru": "Финансы",         "emoji": "💰", "sort_order": 4},
    {"slug": "crypto",    "name_ru": "Крипто",          "emoji": "₿",  "sort_order": 5},
    {"slug": "education", "name_ru": "Образование",     "emoji": "📚", "sort_order": 6},
    {"slug": "health",    "name_ru": "Здоровье",        "emoji": "❤️", "sort_order": 7},
    {"slug": "news",      "name_ru": "Новости",         "emoji": "📰", "sort_order": 8},
    {"slug": "other",     "name_ru": "Другое",          "emoji": "🔹", "sort_order": 9},
]


async def seed() -> None:
    async with async_session_factory() as session:
        for cat in CATEGORIES:
            await session.execute(
                text(
                    "INSERT INTO categories (slug, name_ru, emoji, is_active, sort_order) "
                    "VALUES (:slug, :name_ru, :emoji, true, :sort_order) "
                    "ON CONFLICT (slug) DO NOTHING"
                ),
                cat,
            )
        await session.commit()
        result = await session.execute(text("SELECT count(*) FROM categories"))
        count = result.scalar()
        print(f"Categories seeded. Total rows: {count}")


if __name__ == "__main__":
    asyncio.run(seed())
