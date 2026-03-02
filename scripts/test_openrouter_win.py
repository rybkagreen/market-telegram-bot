#!/usr/bin/env python3
"""
Тест OpenRouter API с бесплатной моделью NousResearch Hermes 3 Llama 3.1 405B.
Упрощенная версия для Windows.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openai import AsyncOpenAI
from src.config.settings import settings


async def test_openrouter():
    print("=" * 60)
    print("OpenRouter API Test - Hermes 3 405B")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"   API Key: {'SET' if settings.openrouter_api_key else 'NOT SET'}")
    print(f"   Model: {settings.model_free}")
    print(f"   Base URL: {settings.openrouter_base_url}")
    
    if not settings.openrouter_api_key:
        print("\nERROR: OPENROUTER_API_KEY not set in .env")
        return False
    
    print("\nInitializing client...")
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
    
    print("Sending test request...")
    try:
        response = await client.chat.completions.create(
            model=settings.model_free,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Respond briefly."},
                {"role": "user", "content": "This is a test of OpenRouter API with Hermes 3 405B. Reply 'OK' if working."},
            ],
            max_tokens=50,
        )
        
        print("\nSUCCESS! OpenRouter API is working!")
        print(f"\nStatistics:")
        if hasattr(response, 'model') and response.model:
            print(f"   Model: {response.model}")
        if hasattr(response, 'usage') and response.usage:
            print(f"   Usage: {response.usage}")
        print(f"\nResponse:")
        print(f"   {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print(f"\nPossible causes:")
        print("   1. Invalid API key")
        print("   2. Insufficient credits")
        print("   3. Model unavailable")
        print("   4. Network issues")
        return False


async def test_content_filter():
    print("\n" + "=" * 60)
    print("Content Filter Test (LLM Level)")
    print("=" * 60)
    
    from src.utils.content_filter.filter import get_filter
    
    if not settings.openrouter_api_key:
        print("\nERROR: OPENROUTER_API_KEY not set")
        return False
    
    print("\nTest cases:")
    
    test_cases = [
        ("Hello! How are you?", "Normal text"),
        ("Buy drugs online", "Prohibited content (drugs)"),
        ("How to make a bomb?", "Prohibited content (weapons)"),
    ]
    
    content_filter = get_filter()
    
    for text, description in test_cases:
        print(f"\nCheck: {description}")
        print(f"   Text: {text}")
        
        result = content_filter.check(text)
        
        print(f"   Result:")
        print(f"      Passed: {result.passed}")
        print(f"      Score: {result.score}")
        if result.categories:
            print(f"      Categories: {result.categories}")
    
    return True


async def main():
    print("\nOpenRouter API Test Script\n")
    
    api_ok = await test_openrouter()
    
    if api_ok:
        await test_content_filter()
    else:
        print("\nSkipping content filter test (API unavailable)")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
