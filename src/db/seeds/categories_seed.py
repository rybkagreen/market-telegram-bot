"""Seed script for categories table."""

import asyncio

from sqlalchemy import text

from src.db.session import async_session_factory

CATEGORIES = [
    {"slug": "business",      "name_ru": "Бизнес",        "emoji": "💼", "sort_order": 1},
    {"slug": "it",            "name_ru": "IT и технологии","emoji": "💻", "sort_order": 2},
    {"slug": "marketing",     "name_ru": "Маркетинг",     "emoji": "📢", "sort_order": 3},
    {"slug": "crypto",        "name_ru": "Криптовалюта",  "emoji": "₿",  "sort_order": 4},
    {"slug": "psychology",    "name_ru": "Психология",    "emoji": "🧠", "sort_order": 5},
    {"slug": "health",        "name_ru": "Здоровье",      "emoji": "🏥", "sort_order": 6},
    {"slug": "entertainment", "name_ru": "Развлечения",   "emoji": "🎭", "sort_order": 7},
    {"slug": "travel",        "name_ru": "Путешествия",   "emoji": "✈️", "sort_order": 8},
    {"slug": "food",          "name_ru": "Еда",           "emoji": "🍕", "sort_order": 9},
    {"slug": "fashion",       "name_ru": "Мода и стиль",  "emoji": "👗", "sort_order": 10},
    {"slug": "other",         "name_ru": "Другое",        "emoji": "🔹", "sort_order": 11},
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
