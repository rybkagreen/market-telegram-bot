"""
Заполняет поле subcategory для существующих каналов в БД.
Запускать один раз после применения миграции из шага B.3.

Использование (из корня проекта):
    .venv\\Scripts\\python scripts/backfill_subcategories.py   # Windows
    .venv/bin/python scripts/backfill_subcategories.py          # Linux/Mac
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from src.db.models.analytics import TelegramChat
from src.db.session import async_session_factory
from src.utils.categories import classify_subcategory


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(
                TelegramChat.id,
                TelegramChat.title,
                TelegramChat.description,
                TelegramChat.topic,
            )
            .where(
                TelegramChat.is_active == True,  # noqa: E712
                TelegramChat.subcategory.is_(None),
            )
        )
        chats = result.all()

    print(f"Каналов без подкатегории: {len(chats)}")

    classified = 0
    by_subcat: dict[str, int] = {}

    async with async_session_factory() as session:
        for chat_id, title, description, topic in chats:
            subcat = classify_subcategory(
                title=title or "",
                description=description or "",
                topic=topic or "",
            )
            if subcat:
                await session.execute(
                    update(TelegramChat)
                    .where(TelegramChat.id == chat_id)
                    .values(subcategory=subcat)
                )
                classified += 1
                by_subcat[subcat] = by_subcat.get(subcat, 0) + 1

        await session.commit()

    print(f"✅ Классифицировано: {classified} из {len(chats)}")
    print(f"❓ Без подкатегории: {len(chats) - classified}")
    print("\nРаспределение по подкатегориям:")
    for subcat, count in sorted(by_subcat.items(), key=lambda x: -x[1]):
        print(f"  {subcat:20s}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
