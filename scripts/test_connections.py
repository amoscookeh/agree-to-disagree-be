#!/usr/bin/env python3
"""test script to verify supabase and openrouter connections"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.db.client import get_supabase
from src.llm.client import OpenRouterClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def test_supabase_connection():
    """test supabase connection"""
    try:
        logger.info("testing supabase connection...")
        _ = get_supabase()

        # test connection by checking health endpoint
        # supabase client is initialized successfully if we get here
        logger.info(f"✓ supabase client initialized for {settings.supabase_url}")
        logger.info("  note: create tables to test full functionality")
        return True
    except Exception as e:
        logger.error(f"✗ supabase connection failed: {e}")
        return False


async def test_openrouter_connection():
    """test openrouter api connection"""
    try:
        logger.info("testing openrouter connection...")
        client = OpenRouterClient()

        messages = [
            {
                "role": "user",
                "content": "Say 'connection test successful' in exactly 3 words",
            }
        ]

        response = await client.chat_completion(
            messages=messages, model="openai/gpt-4o-mini", max_tokens=50
        )

        content = response["choices"][0]["message"]["content"]
        logger.info("✓ openrouter connected successfully")
        logger.info(f"  response: {content}")
        return True
    except Exception as e:
        logger.error(f"✗ openrouter connection failed: {e}")
        return False


async def test_openrouter_streaming():
    """test openrouter streaming"""
    try:
        logger.info("testing openrouter streaming...")
        client = OpenRouterClient()

        messages = [{"role": "user", "content": "Count from 1 to 5"}]

        chunks = []
        async for chunk in await client.chat_completion(
            messages=messages, model="openai/gpt-4o-mini", stream=True, max_tokens=50
        ):
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    chunks.append(delta["content"])

        full_response = "".join(chunks)
        logger.info("✓ openrouter streaming works")
        logger.info(f"  streamed response: {full_response}")
        return True
    except Exception as e:
        logger.error(f"✗ openrouter streaming failed: {e}")
        return False


async def main():
    logger.info("=== connection tests ===\n")

    results = []

    # test supabase
    results.append(("supabase", test_supabase_connection()))

    # test openrouter
    results.append(("openrouter", await test_openrouter_connection()))

    # test openrouter streaming
    results.append(("openrouter streaming", await test_openrouter_streaming()))

    # summary
    logger.info("\n=== test summary ===")
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 all connections working!")
        return 0
    else:
        logger.error("\n❌ some connections failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
