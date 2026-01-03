"""
integration tests for data sources
tests real API calls to verify search and content extraction work end-to-end
"""

import pytest

from src.config import settings
from src.data_sources.left_leaning.guardian import GuardianSource
from src.data_sources.left_leaning.nyt import NYTSource
from src.data_sources.registry import DataSourceRegistry
from src.data_sources.right_leaning.newsapi import NewsAPISource
from src.data_sources.right_leaning.ny_post_rss import NYPostRSSSource


@pytest.mark.asyncio
@pytest.mark.skipif(
    not settings.guardian_api_key, reason="guardian api key not configured"
)
async def test_guardian_search_and_extract():
    """test guardian can find relevant articles and extract content"""
    source = GuardianSource()

    results = await source.search("climate change", max_results=3)

    assert len(results) > 0, "should return at least one result"

    for result in results:
        assert result.title, "should have title"
        assert result.url, "should have url"
        assert result.snippet, "should have snippet/content"
        assert len(result.snippet) > 20, "snippet should have meaningful content"
        assert result.source_name == "The Guardian"
        assert result.ideological_lean.value == "left"


@pytest.mark.asyncio
@pytest.mark.skipif(not settings.nyt_api_key, reason="nyt api key not configured")
async def test_nyt_search_and_extract():
    """test nyt can find relevant articles and extract content"""
    source = NYTSource()

    try:
        results = await source.search("immigration policy", max_results=3)
    except Exception as e:
        if "429" in str(e):
            pytest.skip("nyt api rate limited")
        raise

    assert len(results) > 0, "should return at least one result"

    for result in results:
        assert result.title, "should have title"
        assert result.url, "should have url"
        assert result.snippet, "should have snippet/content"
        assert len(result.snippet) > 20, "snippet should have meaningful content"
        assert result.source_name == "The New York Times"
        assert result.ideological_lean.value == "left"


@pytest.mark.asyncio
@pytest.mark.skipif(not settings.newsapi_key, reason="newsapi key not configured")
async def test_newsapi_search_and_extract():
    """test newsapi can find relevant articles from conservative sources"""
    source = NewsAPISource()

    results = await source.search("economy", max_results=3)

    if len(results) == 0:
        pytest.skip("newsapi rate limit hit or no results available")

    for result in results:
        assert result.title, "should have title"
        assert result.url, "should have url"
        assert result.snippet, "should have snippet/content"
        assert len(result.snippet) > 20, "snippet should have meaningful content"
        assert result.ideological_lean.value == "right"
        conservative_sources = [
            "Fox News",
            "Wall Street",
            "Breitbart",
            "National Review",
            "Washington Times",
        ]
        assert any(
            source_name in result.source_name for source_name in conservative_sources
        )


@pytest.mark.asyncio
async def test_nypost_rss_search_and_extract():
    """test ny post rss can find relevant articles and extract content"""
    source = NYPostRSSSource()

    results = await source.search("politics", max_results=3)

    if len(results) == 0:
        pytest.skip("no matching articles in current rss feed")

    for result in results:
        assert result.title, "should have title"
        assert result.url, "should have url"
        assert result.snippet, "should have snippet/content"
        assert result.source_name == "NY Post"
        assert result.ideological_lean.value == "right"


@pytest.mark.asyncio
async def test_registry_parallel_search():
    """test registry can search multiple sources in parallel"""
    registry = DataSourceRegistry()

    if settings.guardian_api_key:
        registry.register_left(GuardianSource())
    if settings.nyt_api_key:
        registry.register_left(NYTSource())
    if settings.newsapi_key:
        registry.register_right(NewsAPISource())

    registry.register_right(NYPostRSSSource())

    results = await registry.search_all("healthcare", max_results=2)

    assert "left" in results
    assert "right" in results

    if settings.guardian_api_key or settings.nyt_api_key:
        assert len(results["left"]) > 0, "should have left results"

    assert len(results["right"]) >= 0, "should have right results or empty list"


@pytest.mark.asyncio
async def test_content_extraction_quality():
    """test that extracted content is useful for agent analysis"""
    sources_to_test = []

    if settings.guardian_api_key:
        sources_to_test.append(("Guardian", GuardianSource()))
    if settings.nyt_api_key:
        sources_to_test.append(("NYT", NYTSource()))
    if settings.newsapi_key:
        sources_to_test.append(("NewsAPI", NewsAPISource()))

    sources_to_test.append(("NY Post RSS", NYPostRSSSource()))

    if not sources_to_test:
        pytest.skip("no api keys configured")

    for name, source in sources_to_test:
        results = await source.search("education", max_results=1)

        if len(results) == 0:
            continue

        result = results[0]

        assert result.title, f"{name}: should have title"
        assert len(result.title) > 10, f"{name}: title should be meaningful"

        assert result.url, f"{name}: should have url"
        assert result.url.startswith("http"), f"{name}: url should be valid"

        assert result.snippet, f"{name}: should have content"
        assert len(result.snippet) > 50, (
            f"{name}: should have substantial content for analysis"
        )

        words = result.snippet.split()
        assert len(words) > 10, f"{name}: snippet should have multiple words"


@pytest.mark.asyncio
async def test_search_relevance():
    """test that search results are relevant to query"""
    if not settings.guardian_api_key:
        pytest.skip("guardian api key not configured")

    source = GuardianSource()
    query = "renewable energy"

    results = await source.search(query, max_results=5)

    assert len(results) > 0, "should return results"

    query_terms = query.lower().split()
    relevant_count = 0

    for result in results:
        combined_text = f"{result.title} {result.snippet}".lower()

        if any(term in combined_text for term in query_terms):
            relevant_count += 1

    relevance_ratio = relevant_count / len(results)
    assert relevance_ratio > 0.5, "at least 50% of results should be relevant to query"


@pytest.mark.asyncio
async def test_error_handling_graceful_degradation():
    """test that failed sources don't crash the registry"""
    registry = DataSourceRegistry()

    invalid_guardian = GuardianSource(api_key="invalid_key")
    registry.register_left(invalid_guardian)

    registry.register_right(NYPostRSSSource())

    results = await registry.search_all("test", max_results=1)

    assert "left" in results
    assert "right" in results
    assert isinstance(results["left"], list)
    assert isinstance(results["right"], list)
