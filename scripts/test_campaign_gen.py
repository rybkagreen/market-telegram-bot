"""
Тест генерации текстов кампаний через OpenRouter с Hermes 3 405B.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.services.ai_service import AIService
from src.config.settings import settings


async def test_campaign_generation():
    print("=" * 60)
    print("Campaign Text Generation Test - Hermes 3 405B")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"   API Key: {'SET' if settings.openrouter_api_key else 'NOT SET'}")
    print(f"   Model Free: {settings.model_free}")
    print(f"   Model Paid: {settings.model_paid}")
    
    if not settings.openrouter_api_key:
        print("\nERROR: OPENROUTER_API_KEY not set in .env")
        return False
    
    ai_service = AIService()
    
    # Тестовые запросы
    test_prompts = [
        {
            "description": "Курс по маркетингу",
            "prompt": "Напиши рекламный текст для онлайн-курса по интернет-маркетингу. Длительность 2 месяца, сертификат, трудоустройство. Цена 49900 руб.",
        },
        {
            "description": "Магазин одежды",
            "prompt": "Напиши рекламный текст для магазина женской одежды. Новая коллекция, скидки до 50%, бесплатная доставка.",
        },
        {
            "description": "Криптобиржа",
            "prompt": "Напиши рекламный текст для криптобиржи. Бонус 100$ за регистрацию, низкие комиссии, поддержка 24/7.",
        },
    ]
    
    for test in test_prompts:
        print(f"\n{'-' * 60}")
        print(f"Test: {test['description']}")
        print(f"Prompt: {test['prompt'][:100]}...")
        print(f"{'-' * 60}")
        
        try:
            text = await ai_service.generate(
                prompt=test['prompt'],
                user_plan="free",  # Используем бесплатную модель
                use_cache=False,   # Не использовать кэш для теста
            )
            
            print(f"\nGenerated text ({len(text)} chars):")
            print(f"{text}\n")
            
        except Exception as e:
            print(f"\nERROR: {e}")
            print(f"Type: {type(e).__name__}")
    
    return True


async def test_content_filter():
    print("\n" + "=" * 60)
    print("Content Filter Test - Campaign Texts")
    print("=" * 60)
    
    from src.utils.content_filter.filter import check as content_filter_check
    
    test_texts = [
        ("Привет! У нас отличный курс по маркетингу!", "Нормальный текст"),
        ("Купить наркотики легко! Закладки по городу!", "Запрещенный контент"),
        ("Заработай миллион за неделю! Схема здесь!", "Подозрительный текст (fraud)"),
    ]
    
    for text, description in test_texts:
        print(f"\nTest: {description}")
        print(f"Text: {text}")
        
        result = content_filter_check(text)
        
        print(f"Result:")
        print(f"   Passed: {result.passed}")
        print(f"   Score: {result.score}")
        if result.categories:
            print(f"   Categories: {result.categories}")
        if result.level3_score > 0:
            print(f"   LLM Score: {result.level3_score}")
    
    return True


async def main():
    print("\nCampaign Generation Test Script\n")
    
    gen_ok = await test_campaign_generation()
    
    if gen_ok:
        await test_content_filter()
    else:
        print("\nSkipping content filter test (generation failed)")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
