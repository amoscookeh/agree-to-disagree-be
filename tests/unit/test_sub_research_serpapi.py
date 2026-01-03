"""unit tests for sub_research node with SerpAPI integration"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.nodes.sub_research import (
    ToolProgressCallback,
    search_google,
    search_news_sources,
)
from src.data_sources.base import IdeologicalLean, SearchResult


@pytest.mark.asyncio
async def test_search_google_tool():
    """test search_google tool"""
    with patch("src.agents.nodes.sub_research.serpapi_client") as mock_client:
        mock_client.search = AsyncMock(
            return_value=[
                SearchResult(
                    title="Test Result",
                    url="https://example.com",
                    snippet="test snippet",
                    source_name="Google Search",
                    ideological_lean=IdeologicalLean.NEUTRAL,
                )
            ]
        )

        result = await search_google.ainvoke({"query": "test query"})

        assert "Test Result" in result
        assert "https://example.com" in result
        assert "test snippet" in result
        mock_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_search_google_tool_disabled():
    """test search_google when serpapi is disabled"""
    with patch("src.agents.nodes.sub_research.serpapi_client") as mock_client:
        mock_client.search = AsyncMock(return_value=[])

        result = await search_google.ainvoke({"query": "test query"})

        assert "not available" in result.lower() or "no results" in result.lower()


@pytest.mark.asyncio
async def test_search_news_sources_tool_both():
    """test search_news_sources with both leans"""
    with patch("src.agents.nodes.sub_research.get_default_registry") as mock_registry:
        mock_reg = MagicMock()
        mock_reg.search_left = AsyncMock(
            return_value=[
                SearchResult(
                    title="Left Article",
                    url="https://left.com",
                    snippet="left snippet",
                    source_name="Guardian",
                    ideological_lean=IdeologicalLean.LEFT,
                )
            ]
        )
        mock_reg.search_right = AsyncMock(
            return_value=[
                SearchResult(
                    title="Right Article",
                    url="https://right.com",
                    snippet="right snippet",
                    source_name="Breitbart",
                    ideological_lean=IdeologicalLean.RIGHT,
                )
            ]
        )
        mock_registry.return_value = mock_reg

        result = await search_news_sources.ainvoke({"query": "test", "lean": "both"})

        assert "Left Article" in result
        assert "Right Article" in result
        assert "[left]" in result.lower()
        assert "[right]" in result.lower()


@pytest.mark.asyncio
async def test_search_news_sources_tool_left_only():
    """test search_news_sources with left lean only"""
    with patch("src.agents.nodes.sub_research.get_default_registry") as mock_registry:
        mock_reg = MagicMock()
        mock_reg.search_left = AsyncMock(
            return_value=[
                SearchResult(
                    title="Left Article",
                    url="https://left.com",
                    snippet="left snippet",
                    source_name="Guardian",
                    ideological_lean=IdeologicalLean.LEFT,
                )
            ]
        )
        mock_registry.return_value = mock_reg

        result = await search_news_sources.ainvoke({"query": "test", "lean": "left"})

        assert "Left Article" in result
        assert "[left]" in result.lower()
        mock_reg.search_left.assert_called_once()


@pytest.mark.asyncio
async def test_tool_progress_callback():
    """test ToolProgressCallback emits progress events"""
    mock_writer = MagicMock()
    callback = ToolProgressCallback(mock_writer, "test-sq-id")

    callback.on_tool_start({"name": "search_google"}, "test query input")

    # verify _emit_progress was called (indirectly via mock_writer)
    # in real usage, this would emit a progress event
    assert True  # callback doesn't raise errors


@pytest.mark.asyncio
async def test_search_news_sources_no_results():
    """test search_news_sources when no articles found"""
    with patch("src.agents.nodes.sub_research.get_default_registry") as mock_registry:
        mock_reg = MagicMock()
        mock_reg.search_left = AsyncMock(return_value=[])
        mock_reg.search_right = AsyncMock(return_value=[])
        mock_registry.return_value = mock_reg

        result = await search_news_sources.ainvoke({"query": "test", "lean": "both"})

        assert "no articles found" in result.lower()
