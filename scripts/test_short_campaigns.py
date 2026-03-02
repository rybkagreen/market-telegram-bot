"""
Тест генерации коротких текстов кампаний с тематическими промптами.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.services.ai_service import AIService
from src.config.settings import settings


async def test_short_campaigns():
    print("=" * 60)
    print("Short Campaign Text Generation Test")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"   API Key: {'SET' if settings.openrouter_api_key else 'NOT SET'}")
    print(f"   Model Free: {settings.model_free}")
    print(f"   Fallback: {settings.model_free_fallback}")
    
    if not settings.openrouter_api_key:
        print("\nERROR: OPENROUTER_API_KEY not set")
        return False
    
    ai_service = AIService()
    
    # Тесты с тематиками
    test_cases = [
        {
            "topic": "education",
            "description": "Онлайн-курс по интернет-маркетингу. 2 месяца, сертификат, трудоустройство. Цена 49900 руб.",
        },
        {
            "topic": "retail",
            "description": "Магазин женской одежды. Новая коллекция, скидки до 50%, бесплатная доставка.",
        },
        {
            "topic": "finance",
            "description": "Криптобиржа. Бонус $100 за регистрацию, низкие комиссии, поддержка 24/7.",
        },
        {
            "topic": "default",
            "description": "Кофейня в центре города. Свежая обжарка, уютная атмосфера, бизнес-ланчи.",
        },
    ]
    
    for test in test_cases:
        print(f"\n{'-' * 60}")
        print(f"Topic: {test['topic'].upper()}")
        print(f"Description: {test['description'][:80]}...")
        print(f"{'-' * 60}")
        
        try:
            text = await ai_service.generate_ad_text(
                description=test['description'],
                user_plan="free",
                topic=test['topic'],
            )
            
            print(f"\nGenerated ({len(text)} chars):")
            print(f"{text}\n")
            
        except Exception as e:
            print(f"\nERROR: {e}")
    
    return True


async def test_ab_variants():
    print("\n" + "=" * 60)
    print("A/B Variants Test")
    print("=" * 60)
    
    ai_service = AIService()
    
    description = "Фитнес-клуб. Абонемент от 1500 руб/мес, бассейн, сауна, парковка."
    
    print(f"\nDescription: {description}")
    print("Generating 3 variants with topic=retail...\n")
    
    try:
        variants = await ai_service.generate_ab_variants(
            description=description,
            user_plan="free",
            count=3,
            topic="retail",
        )
        
        for i, variant in enumerate(variants, 1):
            print(f"\n--- Variant {i} ({len(variant)} chars) ---")
            print(f"{variant}\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")
    
    return True


async def main():
    print("\nShort Campaign Generation Test\n")
    
    await test_short_campaigns()
    await test_ab_variants()
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
