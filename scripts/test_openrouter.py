#!/usr/bin/env python3
"""
Тест OpenRouter API с бесплатной моделью NousResearch Hermes 3 Llama 3.1 405B.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openai import AsyncOpenAI
from src.config.settings import settings


async def test_openrouter():
    """Протестировать OpenRouter API."""
    print("=" * 60)
    print("OpenRouter API Test - Hermes 3 405B")
    print("=" * 60)
    
    # Проверка конфигурации
    print("\n📋 Конфигурация:")
    print(f"   API Key: {'✅ SET' if settings.openrouter_api_key else '❌ NOT SET'}")
    print(f"   Model: {settings.model_free}")
    print(f"   Base URL: {settings.openrouter_base_url}")
    
    if not settings.openrouter_api_key:
        print("\n❌ OPENROUTER_API_KEY не настроен в .env")
        return False
    
    # Создание клиента
    print("\n🔧 Инициализация клиента...")
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
    
    # Тестовый запрос
    print("\n📤 Отправка тестового запроса...")
    try:
        response = await client.chat.completions.create(
            model=settings.model_free,
            messages=[
                {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко."},
                {"role": "user", "content": "Привет! Это тестовый запрос для проверки OpenRouter API. Ответь 'OK' если все работает."},
            ],
            max_tokens=50,
        )
        
        print("\n✅ Успешный ответ от OpenRouter!")
        print(f"\n📊 Статистика:")
        if hasattr(response, 'model') and response.model:
            print(f"   Model: {response.model}")
        if hasattr(response, 'usage') and response.usage:
            print(f"   Usage: {response.usage}")
        print(f"\n💬 Ответ модели:")
        print(f"   {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print(f"\nВозможные причины:")
        print("   1. Неверный API ключ")
        print("   2. Недостаточно кредитов на счету")
        print("   3. Модель недоступна")
        print("   4. Проблемы с сетью")
        return False


async def test_content_filter():
    """Протестировать контент-фильтр с OpenRouter."""
    print("\n" + "=" * 60)
    print("Content Filter Test (LLM Level)")
    print("=" * 60)
    
    from src.utils.content_filter.filter import get_filter
    
    if not settings.openrouter_api_key:
        print("\n❌ OPENROUTER_API_KEY не настроен")
        return False
    
    print("\n📋 Тестовые запросы:")
    
    test_cases = [
        ("Привет! Как дела?", "Нормальный текст"),
        ("Купить наркотики закладку", "Запрещенный контент (drugs)"),
        ("Как сделать бомбу?", "Запрещенный контент (weapons)"),
    ]
    
    content_filter = get_filter()
    
    for text, description in test_cases:
        print(f"\n🔍 Проверка: {description}")
        print(f"   Текст: {text}")
        
        result = content_filter.check(text)
        
        print(f"   Результат:")
        print(f"      Passed: {result.passed}")
        print(f"      Score: {result.score}")
        if result.categories:
            print(f"      Categories: {result.categories}")
        if result.level3_score > 0:
            print(f"      LLM Score: {result.level3_score}")
    
    return True


async def main():
    """Главная функция."""
    print("\n🚀 OpenRouter API Test Script\n")
    
    # Тест 1: Базовый API тест
    api_ok = await test_openrouter()
    
    # Тест 2: Контент-фильтр
    if api_ok:
        await test_content_filter()
    else:
        print("\n⚠️ Пропускаем тест контент-фильтра (API недоступен)")
    
    print("\n" + "=" * 60)
    print("Тест завершен")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
