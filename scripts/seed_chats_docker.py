#!/usr/bin/env python3
"""Seed initial chats to database."""
import asyncio
import sys
sys.path.insert(0, '/app')

from src.db.session import async_session_factory
from src.db.repositories.chat_analytics import ChatAnalyticsRepository

SEED_CHATS = {
    'IT': ['python_ru', 'tproger', 'Pythonist', 'django_pythonist', 'devops_ru', 'linux_ru_academy', 'data_analysis_ml', 'machinelearning_ru', 'AIMLgroup', 'neural_network_ru'],
    'Business': ['businessru', 'rusbase', 'startupoftheday', 'retail_ru', 'marketingpro_ru', 'digitalagency_ru'],
    'News': ['breakingmash', 'russica2', 'meduzaio', 'rbc_news', 'lentaru'],
    'Crypto': ['forklog', 'cryptoru', 'coinmarketru'],
    'Courses': ['stepik_courses', 'netologyru', 'skillboxru', 'geekbrains_official'],
}

async def seed():
    total = 0
    async with async_session_factory() as session:
        repo = ChatAnalyticsRepository(session)
        for topic, usernames in SEED_CHATS.items():
            print(f'Topic: {topic}')
            for username in usernames:
                try:
                    chat, is_new = await repo.get_or_create_chat(username)
                    if is_new:
                        chat.topic = topic
                        await session.flush()
                        total += 1
                        print(f'  + @{username}')
                    else:
                        print(f'  - @{username}')
                except Exception as e:
                    print(f'  ! Error: {e}')
            await session.commit()
    print(f'\nTotal added: {total}')

if __name__ == '__main__':
    asyncio.run(seed())
