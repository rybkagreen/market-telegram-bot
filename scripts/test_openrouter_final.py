"""
Test OpenRouter API with Hermes 3 405B using OpenAI SDK.
"""
import asyncio
import os
from openai import OpenAI

# Load .env file
from dotenv import load_dotenv
load_dotenv()

async def test_openrouter():
    print("=" * 60)
    print("OpenRouter API Test - Hermes 3 405B")
    print("=" * 60)
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = "nousresearch/hermes-3-llama-3.1-405b:free"
    
    print(f"\nConfiguration:")
    print(f"   API Key: {'SET' if api_key else 'NOT SET'}")
    print(f"   Model: {model}")
    print(f"   Base URL: https://openrouter.ai/api/v1")
    
    if not api_key:
        print("\nERROR: OPENROUTER_API_KEY not set in .env")
        return False
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    print("\nSending test request...")
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://github.com/rybkagreen/market-telegram-bot",
                "X-OpenRouter-Title": "Market Telegram Bot",
            },
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "This is a test. Reply 'OK' if working."
                }
            ],
            max_tokens=10,
        )
        
        print("\nSUCCESS! OpenRouter API is working!")
        print(f"\nResponse: {completion.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nPossible causes:")
        print("  1. Invalid API key")
        print("  2. Insufficient credits")
        print("  3. Model unavailable")
        print("  4. Network issues")
        return False


if __name__ == "__main__":
    asyncio.run(test_openrouter())
