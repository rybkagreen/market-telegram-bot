import asyncio
import sys
sys.path.insert(0, '/app')

from src.db.session import async_session_factory
from src.db.models.analytics import TelegramChat
from sqlalchemy import select
from src.utils.categories import classify_subcategory, SUBCATEGORIES

async def test():
    async with async_session_factory() as session:
        result = await session.execute(
            select(TelegramChat.id, TelegramChat.title, TelegramChat.description, TelegramChat.topic)
            .where(TelegramChat.description.like('%малый бизнес%'))
            .limit(2)
        )
        chats = result.all()
        
        print(f"SUBCATEGORIES keys: {list(SUBCATEGORIES.keys())}")
        
        for chat_id, title, desc, topic in chats:
            print(f"ID: {chat_id}, Topic: '{topic}', Desc: '{desc[:30]}'")
            subcat = classify_subcategory(title or "", desc or "", topic or "")
            print(f"  -> subcat: {subcat}")

if __name__ == '__main__':
    asyncio.run(test())
