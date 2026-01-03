from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.graph import _route_after_supervisor
from src.agents.nodes.sub_research import sub_research_node
from src.agents.nodes.supervisor import (
    SubQueryGeneration,
    SubQueryItem,
    SupervisorDecision,
    supervisor_node,
)
from src.agents.state import AgentState, Draft, SubQuery


class TestSupervisorNode:
    @pytest.fixture
    def mock_stream_writer(self):
        with patch("src.agents.nodes.supervisor.get_stream_writer") as mock:
            mock.return_value = MagicMock()
            yield mock.return_value

    @pytest.fixture
    def mock_llm(self):
        with patch("src.agents.nodes.supervisor.llm") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_initial_sub_query_generation(self, mock_stream_writer, mock_llm):
        """test supervisor generates sub-queries on first invocation (no drafts)"""
        state: AgentState = {
            "query": "What are perspectives on immigration policy?",
            "thread_id": "test-thread",
            "drafts": [],
        }

        mock_structured = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.ainvoke.return_value = SubQueryGeneration(
            sub_queries=[
                SubQueryItem(
                    query="Economic impacts of immigration",
                    angle="left",
                    rationale="Explore progressive economic arguments",
                ),
                SubQueryItem(
                    query="Fiscal costs of immigration",
                    angle="right",
                    rationale="Explore conservative fiscal concerns",
                ),
                SubQueryItem(
                    query="Peer-reviewed immigration research",
                    angle="both",
                    rationale="Get balanced academic data",
                ),
            ]
        )

        result = await supervisor_node(state)

        assert "sub_queries" in result
        assert len(result["sub_queries"]) == 3
        assert result["supervisor_cycle"] == 1
        assert result["ready_for_synthesis"] is False
        assert len(result["pending_sub_queries"]) == 3

        assert result["sub_queries"][0]["id"] == "sq-1"
        assert result["sub_queries"][0]["angle"] == "left"
        assert result["sub_queries"][1]["id"] == "sq-2"
        assert result["sub_queries"][1]["angle"] == "right"
        assert result["sub_queries"][2]["id"] == "sq-3"
        assert result["sub_queries"][2]["angle"] == "both"

    @pytest.mark.asyncio
    async def test_supervisor_decides_to_synthesize(self, mock_stream_writer, mock_llm):
        """test supervisor decides to synthesize when drafts are sufficient"""
        state: AgentState = {
            "query": "What are perspectives on immigration policy?",
            "thread_id": "test-thread",
            "supervisor_cycle": 1,
            "drafts": [
                Draft(
                    sub_query_id="sq-1",
                    sub_query="Economic impacts",
                    angle="left",
                    left_results=[],
                    right_results=[],
                    summary="Left perspective on economics",
                    key_findings=["Finding 1", "Finding 2"],
                    sources_count=3,
                    created_at="2026-01-03T12:00:00Z",
                ),
                Draft(
                    sub_query_id="sq-2",
                    sub_query="Fiscal costs",
                    angle="right",
                    left_results=[],
                    right_results=[],
                    summary="Right perspective on costs",
                    key_findings=["Finding 3"],
                    sources_count=2,
                    created_at="2026-01-03T12:00:00Z",
                ),
            ],
            "sub_queries": [
                SubQuery(
                    id="sq-1", query="Economic impacts", angle="left", status="complete"
                ),
                SubQuery(
                    id="sq-2", query="Fiscal costs", angle="right", status="complete"
                ),
            ],
        }

        mock_structured = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.ainvoke.return_value = SupervisorDecision(
            has_sufficient_info=True,
            reasoning="Both perspectives are well covered with sufficient evidence.",
            new_sub_queries=[],
        )

        result = await supervisor_node(state)

        assert result["ready_for_synthesis"] is True
        assert result["supervisor_cycle"] == 2
        assert "sufficient" in result["supervisor_reasoning"].lower()

    @pytest.mark.asyncio
    async def test_supervisor_continues_research(self, mock_stream_writer, mock_llm):
        """test supervisor generates more sub-queries when info is insufficient"""
        state: AgentState = {
            "query": "What are perspectives on immigration policy?",
            "thread_id": "test-thread",
            "supervisor_cycle": 1,
            "drafts": [
                Draft(
                    sub_query_id="sq-1",
                    sub_query="Economic impacts",
                    angle="left",
                    left_results=[],
                    right_results=[],
                    summary="Limited findings",
                    key_findings=["One finding"],
                    sources_count=1,
                    created_at="2026-01-03T12:00:00Z",
                ),
            ],
            "sub_queries": [
                SubQuery(
                    id="sq-1", query="Economic impacts", angle="left", status="complete"
                ),
            ],
        }

        mock_structured = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.ainvoke.return_value = SupervisorDecision(
            has_sufficient_info=False,
            reasoning="Need more data on conservative perspective and academic research.",
            new_sub_queries=[
                SubQueryItem(
                    query="Conservative fiscal concerns",
                    angle="right",
                    rationale="Missing right perspective",
                ),
            ],
        )

        result = await supervisor_node(state)

        assert result["ready_for_synthesis"] is False
        assert result["supervisor_cycle"] == 2
        assert len(result["pending_sub_queries"]) == 1
        assert result["pending_sub_queries"][0]["id"] == "sq-2"
        assert result["pending_sub_queries"][0]["angle"] == "right"

    @pytest.mark.asyncio
    async def test_max_cycles_enforced(self, mock_stream_writer, mock_llm):
        """test supervisor forces synthesis after max cycles (5)"""
        state: AgentState = {
            "query": "What are perspectives on immigration policy?",
            "thread_id": "test-thread",
            "supervisor_cycle": 4,
            "drafts": [
                Draft(
                    sub_query_id="sq-1",
                    sub_query="Test",
                    angle="both",
                    left_results=[],
                    right_results=[],
                    summary="Some findings",
                    key_findings=["Finding"],
                    sources_count=1,
                    created_at="2026-01-03T12:00:00Z",
                ),
            ],
            "sub_queries": [],
        }

        result = await supervisor_node(state)

        assert result["ready_for_synthesis"] is True
        assert result["supervisor_cycle"] == 5
        assert "max" in result["supervisor_reasoning"].lower()


class TestSubResearchNode:
    @pytest.fixture
    def mock_stream_writer(self):
        with patch("src.agents.nodes.sub_research.get_stream_writer") as mock:
            mock.return_value = MagicMock()
            yield mock.return_value

    @pytest.fixture
    def mock_registry(self):
        with patch("src.agents.nodes.sub_research.get_default_registry") as mock:
            registry = MagicMock()
            mock.return_value = registry
            yield registry

    @pytest.fixture
    def mock_search_result_to_dict(self):
        with patch("src.agents.nodes.sub_research.search_result_to_dict") as mock:
            mock.side_effect = lambda r: {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "published_date": r.published_date,
                "source_name": r.source_name,
                "ideological_lean": "left",
            }
            yield mock

    @pytest.mark.asyncio
    async def test_handles_empty_pending_queue(self, mock_stream_writer):
        """test sub_research handles empty pending queue gracefully"""
        state: AgentState = {
            "thread_id": "test-thread",
            "supervisor_cycle": 1,
            "pending_sub_queries": [],
        }

        result = await sub_research_node(state)

        assert result == {}


class TestRoutingLogic:
    def test_routes_to_sub_research_when_pending(self):
        """test routing to sub_research when pending sub-queries exist"""
        state: AgentState = {
            "pending_sub_queries": [
                SubQuery(id="sq-1", query="Test", angle="left", status="pending"),
            ],
            "ready_for_synthesis": False,
            "supervisor_cycle": 1,
        }

        result = _route_after_supervisor(state)

        assert result == "sub_research"

    def test_routes_to_synthesis_when_ready(self):
        """test routing to synthesis when ready_for_synthesis is True"""
        state: AgentState = {
            "pending_sub_queries": [],
            "ready_for_synthesis": True,
            "supervisor_cycle": 2,
        }

        result = _route_after_supervisor(state)

        assert result == "synthesis"

    def test_routes_to_synthesis_at_max_cycles(self):
        """test routing to synthesis when max cycles reached"""
        state: AgentState = {
            "pending_sub_queries": [],
            "ready_for_synthesis": False,
            "supervisor_cycle": 5,
        }

        result = _route_after_supervisor(state)

        assert result == "synthesis"

    def test_defaults_to_synthesis(self):
        """test default routing to synthesis"""
        state: AgentState = {
            "pending_sub_queries": [],
            "ready_for_synthesis": False,
            "supervisor_cycle": 1,
        }

        result = _route_after_supervisor(state)

        assert result == "synthesis"


class TestStateAccumulation:
    def test_drafts_accumulate_via_annotated_add(self):
        """test that drafts use Annotated[..., add] for accumulation"""
        from operator import add
        from typing import get_type_hints

        from src.agents.state import AgentState

        hints = get_type_hints(AgentState, include_extras=True)
        drafts_hint = hints.get("drafts")

        assert drafts_hint is not None
        assert hasattr(drafts_hint, "__metadata__")
        assert add in drafts_hint.__metadata__
