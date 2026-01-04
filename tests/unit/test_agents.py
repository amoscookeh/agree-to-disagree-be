from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents import AgentState
from src.agents.nodes import clarification_node, research_node
from src.agents.nodes.clarification import ClarificationAnalysis
from src.data_sources.base import IdeologicalLean, SearchResult


@pytest.fixture
def mock_search_results():
    return [
        SearchResult(
            title="Test Article 1",
            url="https://example.com/1",
            snippet="Test snippet about immigration policy",
            published_date="2025-12-01",
            source_name="Test Source",
            ideological_lean=IdeologicalLean.LEFT,
        ),
        SearchResult(
            title="Test Article 2",
            url="https://example.com/2",
            snippet="Another test snippet about policy",
            published_date="2025-12-02",
            source_name="Test Source",
            ideological_lean=IdeologicalLean.LEFT,
        ),
    ]


@pytest.fixture
def mock_stream_writer():
    return MagicMock()


def _create_mock_registry(search_results: dict, sources_list: list):
    mock_registry = MagicMock()
    mock_registry.search_all = AsyncMock(return_value=search_results)
    mock_registry.list_sources.return_value = sources_list
    return mock_registry


class TestResearchNode:
    @pytest.mark.asyncio
    async def test_research_node_returns_results(
        self, mock_search_results, mock_stream_writer
    ):
        with (
            patch(
                "src.agents.nodes.research.get_default_registry"
            ) as mock_create_registry,
            patch(
                "src.agents.nodes.research.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_registry = _create_mock_registry(
                {
                    "left": mock_search_results,
                    "right": mock_search_results,
                    "academic": [],
                },
                [{"name": "Test Source", "lean": "left", "enabled": True}],
            )
            mock_create_registry.return_value = mock_registry

            state: AgentState = {"query": "immigration policy"}
            result = await research_node(state)

            assert "left_results" in result
            assert "right_results" in result
            assert "academic_results" in result
            assert len(result["left_results"]) == 2
            assert len(result["right_results"]) == 2
            assert len(result["academic_results"]) == 0

    @pytest.mark.asyncio
    async def test_research_node_uses_refined_query(
        self, mock_search_results, mock_stream_writer
    ):
        with (
            patch(
                "src.agents.nodes.research.get_default_registry"
            ) as mock_create_registry,
            patch(
                "src.agents.nodes.research.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_registry = _create_mock_registry(
                {"left": [], "right": [], "academic": []}, []
            )
            mock_create_registry.return_value = mock_registry

            state: AgentState = {
                "query": "original query",
                "refined_query": "refined immigration policy",
            }
            await research_node(state)

            mock_registry.search_all.assert_called_once_with(
                "refined immigration policy", max_results=5
            )

    @pytest.mark.asyncio
    async def test_research_node_no_query(self, mock_stream_writer):
        with patch(
            "src.agents.nodes.research.get_stream_writer",
            return_value=mock_stream_writer,
        ):
            state: AgentState = {}
            result = await research_node(state)

            assert "error" in result
            assert result["error"] == "no query provided"

    @pytest.mark.asyncio
    async def test_research_node_streams_progress(
        self, mock_search_results, mock_stream_writer
    ):
        with (
            patch(
                "src.agents.nodes.research.get_default_registry"
            ) as mock_create_registry,
            patch(
                "src.agents.nodes.research.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_registry = _create_mock_registry(
                {"left": mock_search_results, "right": [], "academic": []},
                [{"name": "Test Source", "lean": "left", "enabled": True}],
            )
            mock_create_registry.return_value = mock_registry

            state: AgentState = {"query": "test query"}
            await research_node(state)

            assert mock_stream_writer.call_count >= 3
            calls = [call[0][0] for call in mock_stream_writer.call_args_list]
            statuses = [c["data"]["status"] for c in calls]
            assert "starting" in statuses
            assert "complete" in statuses

    @pytest.mark.asyncio
    async def test_research_node_converts_results_to_dicts(
        self, mock_search_results, mock_stream_writer
    ):
        with (
            patch(
                "src.agents.nodes.research.get_default_registry"
            ) as mock_create_registry,
            patch(
                "src.agents.nodes.research.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_registry = _create_mock_registry(
                {"left": mock_search_results, "right": [], "academic": []}, []
            )
            mock_create_registry.return_value = mock_registry

            state: AgentState = {"query": "test"}
            result = await research_node(state)

            assert isinstance(result["left_results"][0], dict)
            assert result["left_results"][0]["title"] == "Test Article 1"
            assert result["left_results"][0]["ideological_lean"] == "left"


class TestClarificationNode:
    @pytest.mark.asyncio
    async def test_clarification_with_llm_clear_query(self, mock_stream_writer):
        with (
            patch("src.agents.nodes.clarification.get_llm") as mock_get_llm,
            patch(
                "src.agents.nodes.clarification.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_llm = MagicMock()
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                return_value=ClarificationAnalysis(
                    needs_clarification=False,
                    refined_query="What are the perspectives on immigration policy reform?",
                    questions=[],
                    suggestions=[],
                )
            )
            mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)
            mock_get_llm.return_value = mock_llm

            state: AgentState = {
                "query": "What are the perspectives on immigration policy reform?"
            }
            result = await clarification_node(state)

            assert result["needs_clarification"] is False
            assert "refined_query" in result

    @pytest.mark.asyncio
    async def test_clarification_with_llm_vague_query(self, mock_stream_writer):
        with (
            patch("src.agents.nodes.clarification.get_llm") as mock_get_llm,
            patch(
                "src.agents.nodes.clarification.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                return_value=ClarificationAnalysis(
                    needs_clarification=True,
                    refined_query="healthcare policy",
                    questions=[
                        "Are you asking about federal or state-level policy?",
                        "Are you interested in the ACA specifically?",
                    ],
                    suggestions=["federal healthcare policy", "ACA debate"],
                )
            )
            mock_llm = MagicMock()
            mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)
            mock_get_llm.return_value = mock_llm

            state: AgentState = {"query": "what are perspectives on healthcare policy"}
            result = await clarification_node(state)

            assert result["needs_clarification"] is True
            assert len(result["clarification_questions"]) == 2

    @pytest.mark.asyncio
    async def test_clarification_obviously_vague_skips_llm(self, mock_stream_writer):
        with patch(
            "src.agents.nodes.clarification.get_stream_writer",
            return_value=mock_stream_writer,
        ):
            state: AgentState = {"query": "it"}
            result = await clarification_node(state)

            assert result["needs_clarification"] is True
            assert len(result["clarification_questions"]) > 0

    @pytest.mark.asyncio
    async def test_clarification_single_word_skips_llm(self, mock_stream_writer):
        with patch(
            "src.agents.nodes.clarification.get_stream_writer",
            return_value=mock_stream_writer,
        ):
            state: AgentState = {"query": "taxes"}
            result = await clarification_node(state)

            assert result["needs_clarification"] is True

    @pytest.mark.asyncio
    async def test_clarification_with_user_response(self, mock_stream_writer):
        with patch(
            "src.agents.nodes.clarification.get_stream_writer",
            return_value=mock_stream_writer,
        ):
            state: AgentState = {
                "query": "immigration policy",
                "clarification_response": "federal level, current policy",
            }
            result = await clarification_node(state)

            assert result["needs_clarification"] is False
            assert "federal level, current policy" in result["refined_query"]

    @pytest.mark.asyncio
    async def test_clarification_llm_failure_falls_back(self, mock_stream_writer):
        with (
            patch("src.agents.nodes.clarification.get_llm") as mock_get_llm,
            patch(
                "src.agents.nodes.clarification.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_llm = MagicMock()
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                side_effect=Exception("LLM API error")
            )
            mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)
            mock_get_llm.return_value = mock_llm

            state: AgentState = {"query": "What about healthcare policy in the US?"}
            result = await clarification_node(state)

            assert "refined_query" in result

    @pytest.mark.asyncio
    async def test_clarification_streams_progress(self, mock_stream_writer):
        with (
            patch("src.agents.nodes.clarification.get_llm") as mock_get_llm,
            patch(
                "src.agents.nodes.clarification.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_llm = MagicMock()
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                return_value=ClarificationAnalysis(
                    needs_clarification=False,
                    refined_query="What about healthcare policy in the US?",
                    questions=[],
                    suggestions=[],
                )
            )
            mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)
            mock_get_llm.return_value = mock_llm

            state: AgentState = {"query": "What about healthcare policy in the US?"}
            await clarification_node(state)

            assert mock_stream_writer.call_count >= 2
            calls = [call[0][0] for call in mock_stream_writer.call_args_list]
            assert calls[0]["data"]["agent"] == "clarification"

    @pytest.mark.asyncio
    async def test_clarification_llm_returns_questions(self, mock_stream_writer):
        with (
            patch("src.agents.nodes.clarification.get_llm") as mock_get_llm,
            patch(
                "src.agents.nodes.clarification.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                return_value=ClarificationAnalysis(
                    needs_clarification=True,
                    refined_query="tax policy",
                    questions=[
                        "Are you asking about federal or state taxes?",
                        "Income tax, corporate tax, or capital gains?",
                    ],
                    suggestions=["federal income tax policy"],
                )
            )
            mock_llm = MagicMock()
            mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)
            mock_get_llm.return_value = mock_llm

            state: AgentState = {"query": "what are perspectives on tax policy"}
            result = await clarification_node(state)

            assert result["needs_clarification"] is True
            assert "federal" in result["clarification_questions"][0].lower()

    @pytest.mark.asyncio
    async def test_clarification_empty_questions_when_clear(self, mock_stream_writer):
        with (
            patch("src.agents.nodes.clarification.get_llm") as mock_get_llm,
            patch(
                "src.agents.nodes.clarification.get_stream_writer",
                return_value=mock_stream_writer,
            ),
        ):
            mock_structured_llm = AsyncMock()
            mock_structured_llm.ainvoke = AsyncMock(
                return_value=ClarificationAnalysis(
                    needs_clarification=False,
                    refined_query="What are the perspectives on federal minimum wage policy?",
                    questions=[],
                    suggestions=[],
                )
            )
            mock_llm = MagicMock()
            mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)
            mock_get_llm.return_value = mock_llm

            state: AgentState = {"query": "What are the perspectives on minimum wage?"}
            result = await clarification_node(state)

            assert result["needs_clarification"] is False
            assert result["clarification_questions"] == []
