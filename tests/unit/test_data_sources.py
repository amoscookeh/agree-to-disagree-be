from unittest.mock import AsyncMock, Mock

import pytest

from src.data_sources.base import IdeologicalLean, SearchResult
from src.data_sources.left_leaning.guardian import GuardianSource
from src.data_sources.left_leaning.nyt import NYTSource
from src.data_sources.registry import DataSourceRegistry
from src.data_sources.right_leaning.newsapi import NewsAPISource
from src.data_sources.right_leaning.ny_post_rss import NYPostRSSSource


class TestSearchResult:
    def test_search_result_creation(self):
        result = SearchResult(
            title="Test Article",
            url="https://example.com",
            snippet="This is a test snippet",
            published_date="2026-01-02",
            source_name="Test Source",
            ideological_lean=IdeologicalLean.LEFT,
        )

        assert result.title == "Test Article"
        assert result.url == "https://example.com"
        assert result.snippet == "This is a test snippet"
        assert result.published_date == "2026-01-02"
        assert result.source_name == "Test Source"
        assert result.ideological_lean == IdeologicalLean.LEFT

    def test_search_result_optional_published_date(self):
        result = SearchResult(
            title="Test Article",
            url="https://example.com",
            snippet="This is a test snippet",
            source_name="Test Source",
            ideological_lean=IdeologicalLean.RIGHT,
        )

        assert result.published_date is None


class TestGuardianSource:
    @pytest.mark.asyncio
    async def test_guardian_search_success(self, mocker):
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": {
                "results": [
                    {
                        "webTitle": "Test Article 1",
                        "webUrl": "https://theguardian.com/article1",
                        "webPublicationDate": "2026-01-02T12:00:00Z",
                        "fields": {"trailText": "This is a test snippet"},
                    },
                    {
                        "webTitle": "Test Article 2",
                        "webUrl": "https://theguardian.com/article2",
                        "webPublicationDate": "2026-01-01T12:00:00Z",
                        "fields": {"bodyText": "This is body text for article 2"},
                    },
                ]
            }
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = GuardianSource(api_key="test_key")
        results = await source.search("test query", max_results=5)

        assert len(results) == 2
        assert results[0].title == "Test Article 1"
        assert results[0].url == "https://theguardian.com/article1"
        assert results[0].snippet == "This is a test snippet"
        assert results[0].source_name == "The Guardian"
        assert results[0].ideological_lean == IdeologicalLean.LEFT

    @pytest.mark.asyncio
    async def test_guardian_search_http_error(self, mocker):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("HTTP error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = GuardianSource(api_key="test_key")
        results = await source.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_guardian_search_empty_results(self, mocker):
        mock_response = Mock()
        mock_response.json.return_value = {"response": {"results": []}}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = GuardianSource(api_key="test_key")
        results = await source.search("test query")

        assert results == []

    def test_guardian_properties(self):
        source = GuardianSource(api_key="test_key")
        assert source.source_name == "The Guardian"
        assert source.ideological_lean == IdeologicalLean.LEFT
        assert source.enabled is True


class TestNYPostRSSSource:
    @pytest.mark.asyncio
    async def test_nypost_search_success(self, mocker):
        mock_feed_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test Immigration Article</title>
                    <link>https://nypost.com/article1</link>
                    <description>This is about immigration policy</description>
                    <pubDate>Wed, 01 Jan 2026 12:00:00 +0000</pubDate>
                </item>
                <item>
                    <title>Other Article</title>
                    <link>https://nypost.com/article2</link>
                    <description>This is about something else</description>
                    <pubDate>Wed, 01 Jan 2026 11:00:00 +0000</pubDate>
                </item>
            </channel>
        </rss>"""

        mock_response = Mock()
        mock_response.text = mock_feed_content
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NYPostRSSSource()
        results = await source.search("immigration", max_results=5)

        assert len(results) == 1
        assert results[0].title == "Test Immigration Article"
        assert results[0].url == "https://nypost.com/article1"
        assert "immigration policy" in results[0].snippet
        assert results[0].source_name == "NY Post"
        assert results[0].ideological_lean == IdeologicalLean.RIGHT

    @pytest.mark.asyncio
    async def test_nypost_search_http_error(self, mocker):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("HTTP error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NYPostRSSSource()
        results = await source.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_nypost_search_no_matches(self, mocker):
        mock_feed_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Other Article</title>
                    <link>https://nypost.com/article1</link>
                    <description>This is about something else</description>
                </item>
            </channel>
        </rss>"""

        mock_response = Mock()
        mock_response.text = mock_feed_content
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NYPostRSSSource()
        results = await source.search("immigration")

        assert results == []

    def test_nypost_properties(self):
        source = NYPostRSSSource()
        assert source.source_name == "NY Post"
        assert source.ideological_lean == IdeologicalLean.RIGHT
        assert source.enabled is True


class TestNewsAPISource:
    @pytest.mark.asyncio
    async def test_newsapi_search_success(self, mocker):
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Fox News Article",
                    "url": "https://foxnews.com/article1",
                    "publishedAt": "2026-01-02T12:00:00Z",
                    "description": "This is a test description",
                    "source": {"name": "Fox News"},
                },
                {
                    "title": "Test WSJ Article",
                    "url": "https://wsj.com/article1",
                    "publishedAt": "2026-01-01T12:00:00Z",
                    "content": "This is test content",
                    "source": {"name": "The Wall Street Journal"},
                },
            ],
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NewsAPISource(api_key="test_key")
        results = await source.search("test query", max_results=5)

        assert len(results) == 2
        assert results[0].title == "Test Fox News Article"
        assert results[0].url == "https://foxnews.com/article1"
        assert results[0].snippet == "This is a test description"
        assert results[0].source_name == "Fox News"
        assert results[0].ideological_lean == IdeologicalLean.RIGHT

    @pytest.mark.asyncio
    async def test_newsapi_search_error_status(self, mocker):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "error", "message": "API error"}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NewsAPISource(api_key="test_key")
        results = await source.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_newsapi_search_http_error(self, mocker):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("HTTP error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NewsAPISource(api_key="test_key")
        results = await source.search("test query")

        assert results == []

    def test_newsapi_properties(self):
        source = NewsAPISource(api_key="test_key")
        assert source.source_name == "NewsAPI (Conservative)"
        assert source.ideological_lean == IdeologicalLean.RIGHT
        assert source.enabled is True


class TestNYTSource:
    @pytest.mark.asyncio
    async def test_nyt_search_success(self, mocker):
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "headline": {"main": "Test NYT Article 1"},
                        "web_url": "https://nytimes.com/article1",
                        "pub_date": "2026-01-02T12:00:00Z",
                        "abstract": "This is a test abstract",
                    },
                    {
                        "headline": {"main": "Test NYT Article 2"},
                        "web_url": "https://nytimes.com/article2",
                        "pub_date": "2026-01-01T12:00:00Z",
                        "lead_paragraph": "This is a lead paragraph",
                    },
                ]
            }
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NYTSource(api_key="test_key")
        results = await source.search("test query", max_results=5)

        assert len(results) == 2
        assert results[0].title == "Test NYT Article 1"
        assert results[0].url == "https://nytimes.com/article1"
        assert results[0].snippet == "This is a test abstract"
        assert results[0].source_name == "The New York Times"
        assert results[0].ideological_lean == IdeologicalLean.LEFT

    @pytest.mark.asyncio
    async def test_nyt_search_http_error(self, mocker):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("HTTP error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NYTSource(api_key="test_key")
        results = await source.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_nyt_search_empty_results(self, mocker):
        mock_response = Mock()
        mock_response.json.return_value = {"response": {"docs": []}}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        source = NYTSource(api_key="test_key")
        results = await source.search("test query")

        assert results == []

    def test_nyt_properties(self):
        source = NYTSource(api_key="test_key")
        assert source.source_name == "The New York Times"
        assert source.ideological_lean == IdeologicalLean.LEFT
        assert source.enabled is True


class TestDataSourceRegistry:
    def test_register_sources(self):
        registry = DataSourceRegistry()
        guardian = GuardianSource(api_key="test_key")
        nypost = NYPostRSSSource()

        registry.register_left(guardian)
        registry.register_right(nypost)

        assert len(registry._left_sources) == 1
        assert len(registry._right_sources) == 1
        assert len(registry._academic_sources) == 0

    @pytest.mark.asyncio
    async def test_search_left_success(self, mocker):
        registry = DataSourceRegistry()
        guardian = GuardianSource(api_key="test_key")
        registry.register_left(guardian)

        mock_results = [
            SearchResult(
                title="Test Article",
                url="https://example.com",
                snippet="Test snippet",
                source_name="The Guardian",
                ideological_lean=IdeologicalLean.LEFT,
            )
        ]

        mocker.patch.object(guardian, "search", return_value=mock_results)

        results = await registry.search_left("test query")

        assert len(results) == 1
        assert results[0].title == "Test Article"

    @pytest.mark.asyncio
    async def test_search_right_success(self, mocker):
        registry = DataSourceRegistry()
        nypost = NYPostRSSSource()
        registry.register_right(nypost)

        mock_results = [
            SearchResult(
                title="Test Article",
                url="https://example.com",
                snippet="Test snippet",
                source_name="NY Post",
                ideological_lean=IdeologicalLean.RIGHT,
            )
        ]

        mocker.patch.object(nypost, "search", return_value=mock_results)

        results = await registry.search_right("test query")

        assert len(results) == 1
        assert results[0].title == "Test Article"

    @pytest.mark.asyncio
    async def test_search_with_source_failure(self, mocker):
        registry = DataSourceRegistry()
        guardian = GuardianSource(api_key="test_key")
        registry.register_left(guardian)

        mocker.patch.object(guardian, "search", side_effect=Exception("API error"))

        results = await registry.search_left("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_all_parallel(self, mocker):
        registry = DataSourceRegistry()
        guardian = GuardianSource(api_key="test_key")
        nypost = NYPostRSSSource()

        registry.register_left(guardian)
        registry.register_right(nypost)

        left_results = [
            SearchResult(
                title="Left Article",
                url="https://left.com",
                snippet="Left snippet",
                source_name="The Guardian",
                ideological_lean=IdeologicalLean.LEFT,
            )
        ]

        right_results = [
            SearchResult(
                title="Right Article",
                url="https://right.com",
                snippet="Right snippet",
                source_name="NY Post",
                ideological_lean=IdeologicalLean.RIGHT,
            )
        ]

        mocker.patch.object(guardian, "search", return_value=left_results)
        mocker.patch.object(nypost, "search", return_value=right_results)

        results = await registry.search_all("test query")

        assert len(results["left"]) == 1
        assert len(results["right"]) == 1
        assert len(results["academic"]) == 0
        assert results["left"][0].title == "Left Article"
        assert results["right"][0].title == "Right Article"

    @pytest.mark.asyncio
    async def test_search_empty_registry(self):
        registry = DataSourceRegistry()

        results = await registry.search_left("test query")
        assert results == []

        results = await registry.search_right("test query")
        assert results == []

    def test_list_sources(self):
        registry = DataSourceRegistry()
        guardian = GuardianSource(api_key="test_key")
        nypost = NYPostRSSSource()

        registry.register_left(guardian)
        registry.register_right(nypost)

        sources = registry.list_sources()

        assert len(sources) == 2
        assert sources[0]["name"] == "The Guardian"
        assert sources[0]["lean"] == "left"
        assert sources[0]["enabled"] is True
        assert sources[1]["name"] == "NY Post"
        assert sources[1]["lean"] == "right"
        assert sources[1]["enabled"] is True
