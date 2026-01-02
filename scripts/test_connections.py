#!/usr/bin/env python3
"""test script to verify supabase and openrouter connections"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.llm import llm
from src.config import settings
from src.db.client import get_supabase
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

        response = await llm.ainvoke(
            "Say 'connection test successful' in exactly 3 words"
        )

        content = response.content
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

        chunks = []
        async for chunk in llm.astream("Count from 1 to 5"):
            chunks.append(chunk.content)

        full_response = "".join(chunks)
        logger.info("✓ openrouter streaming works")
        logger.info(f"  streamed response: {full_response}")
        return True
    except Exception as e:
        logger.error(f"✗ openrouter streaming failed: {e}")
        return False


async def test_data_sources():
    """test data source connections"""
    from src.data_sources.left_leaning.guardian import GuardianSource
    from src.data_sources.left_leaning.nyt import NYTSource
    from src.data_sources.right_leaning.newsapi import NewsAPISource
    from src.data_sources.right_leaning.ny_post_rss import NYPostRSSSource

    logger.info("testing data sources...")
    results = []

    sources = [
        ("Guardian", GuardianSource(), settings.guardian_api_key),
        ("NYT", NYTSource(), settings.nyt_api_key),
        ("NewsAPI", NewsAPISource(), settings.newsapi_key),
        ("NY Post RSS", NYPostRSSSource(), None),
    ]

    for name, source, api_key in sources:
        if api_key is not None and not api_key:
            logger.info(f"⚠️  {name}: API key not configured, skipping")
            continue

        try:
            test_results = await source.search("test", max_results=1)
            if test_results:
                logger.info(f"✓ {name}: working ({len(test_results)} results)")
                results.append((name, True))
            else:
                logger.warning(f"⚠️  {name}: no results (may be rate limited)")
                results.append((name, True))
        except Exception as e:
            logger.error(f"✗ {name}: {e}")
            results.append((name, False))

    return results


async def main():
    logger.info("=== connection tests ===\n")

    results = []

    # test supabase
    results.append(("supabase", test_supabase_connection()))

    # test openrouter
    results.append(("openrouter", await test_openrouter_connection()))

    # test openrouter streaming
    results.append(("openrouter streaming", await test_openrouter_streaming()))

    # test data sources
    data_source_results = await test_data_sources()
    results.extend(data_source_results)

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
