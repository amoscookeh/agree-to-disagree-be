import asyncio
from datetime import UTC, datetime

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from pydantic import BaseModel

from prompts.models import SUB_RESEARCH_MODEL, SUB_RESEARCH_TOOL_MODEL
from prompts.sub_research import (
    ANGLE_DESCRIPTIONS,
    DRAFT_SYNTHESIS_PROMPT,
    SUB_RESEARCH_SYSTEM_PROMPT,
)
from src.agents.llm import get_llm
from src.agents.state import AgentState, Draft, SubQuery
from src.data_sources import get_default_registry, search_result_to_dict
from src.data_sources.web.serpapi import serpapi_client
from src.utils.logger import logger


class DraftReport(BaseModel):
    summary: str
    key_findings: list[str]
    left_perspective: str | None = None
    right_perspective: str | None = None


class ToolProgressCallback(BaseCallbackHandler):
    """callback to emit progress events for tool usage"""

    def __init__(self, writer, sub_query_id: str):
        self.writer = writer
        self.sub_query_id = sub_query_id

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        tool_name = serialized.get("name", "unknown")
        _emit_progress(
            self.writer,
            "sub_research",
            "searching",
            f"using {tool_name}...",
            details={
                "sub_query_id": self.sub_query_id,
                "tool": tool_name,
                "query": input_str[:100]
                if isinstance(input_str, str)
                else str(input_str)[:100],
            },
        )

    def on_tool_end(self, output: str, **kwargs) -> None:
        pass


@tool
async def search_google(query: str) -> str:
    """
    search google for statistics, studies, or additional sources.
    use when:
    - news sources don't provide specific numbers/stats
    - need academic or government sources for data
    - not enough articles from news sources

    args:
        query: search query, be specific (e.g., "immigration GDP impact statistics 2024")
    """
    results = await serpapi_client.search(query, num_results=5)
    if not results:
        return "google search not available or returned no results."

    formatted = []
    for r in results:
        formatted.append(f"- {r.title}\n  URL: {r.url}\n  {r.snippet}")

    return "\n\n".join(formatted)


@tool
async def search_news_sources(query: str, lean: str = "both") -> str:
    """
    search news sources for articles.

    args:
        query: search query
        lean: "left", "right", or "both"
    """
    registry = get_default_registry()

    if lean == "left":
        results_raw = await registry.search_left(query, max_results=3)
    elif lean == "right":
        results_raw = await registry.search_right(query, max_results=3)
    else:
        left = await registry.search_left(query, max_results=3)
        right = await registry.search_right(query, max_results=3)
        results_raw = left + right

    if not results_raw:
        return "no articles found from news sources."

    formatted = []
    for r in results_raw:
        formatted.append(
            f"- [{r.ideological_lean.value}] {r.title}\n  URL: {r.url}\n  {r.snippet}"
        )

    return "\n\n".join(formatted)


def _emit_progress(
    writer, agent: str, status: str, message: str, details: dict | None = None
):
    event = {
        "type": "progress",
        "data": {
            "agent": agent,
            "status": status,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **({"details": details} if details else {}),
        },
    }
    if writer:
        writer(event)
    return event


def _emit_draft(
    writer,
    thread_id: str,
    sub_query_id: str,
    sub_query: str,
    angle: str,
    summary: str,
    key_findings: list[str],
    sources_count: int,
    cycle: int,
):
    event = {
        "type": "draft",
        "data": {
            "thread_id": thread_id,
            "sub_query_id": sub_query_id,
            "sub_query": sub_query,
            "angle": angle,
            "summary": summary,
            "key_findings": key_findings,
            "sources_count": sources_count,
            "cycle": cycle,
        },
    }
    if writer:
        writer(event)
    return event


def _format_results(results: list[dict]) -> str:
    if not results:
        return "No results found."

    formatted = []
    for r in results:
        formatted.append(
            f"- Title: {r.get('title', 'Unknown')}\n"
            f"  Source: {r.get('source_name', 'Unknown')}\n"
            f"  URL: {r.get('url', 'N/A')}\n"
            f"  Snippet: {r.get('snippet', 'N/A')}"
        )
    return "\n".join(formatted)


async def _research_single_query(
    sub_query: SubQuery, thread_id: str, cycle: int, writer
) -> Draft:
    """research a single sub-query using tool-calling approach"""
    sq_id = sub_query["id"]
    sq_query = sub_query["query"]
    sq_angle = sub_query["angle"]

    _emit_progress(
        writer,
        "sub_research",
        "starting",
        f"researching: {sq_query[:60]}...",
        details={
            "sub_query": sq_query,
            "sub_query_id": sq_id,
            "angle": sq_angle,
            "cycle": cycle,
        },
    )

    left_results: list[dict] = []
    right_results: list[dict] = []
    google_results_text: str = ""

    try:
        tools = [search_news_sources]
        if serpapi_client.enabled:
            tools.append(search_google)

        llm_instance = get_llm(SUB_RESEARCH_TOOL_MODEL)
        llm_with_tools = llm_instance.bind_tools(tools)

        callback = ToolProgressCallback(writer, sq_id)

        angle_desc = ANGLE_DESCRIPTIONS.get(sq_angle, "both perspectives")

        system_prompt = SUB_RESEARCH_SYSTEM_PROMPT.format(
            sub_query=sq_query,
            angle=sq_angle,
            angle_desc=angle_desc,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"research: {sq_query}"),
        ]

        max_iterations = 5
        iteration = 0
        research_content = []

        while iteration < max_iterations:
            iteration += 1

            response = await llm_with_tools.ainvoke(
                messages, config={"callbacks": [callback]}
            )

            if not response.tool_calls:
                if isinstance(response, AIMessage) and response.content:
                    research_content.append(str(response.content))
                break

            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                if tool_name == "search_news_sources":
                    result = await search_news_sources.ainvoke(tool_args)

                    if "left" in tool_args.get("lean", "both").lower():
                        registry = get_default_registry()
                        left_raw = await registry.search_left(sq_query, max_results=3)
                        left_results.extend(
                            [search_result_to_dict(r) for r in left_raw]
                        )

                    if "right" in tool_args.get("lean", "both").lower():
                        registry = get_default_registry()
                        right_raw = await registry.search_right(sq_query, max_results=3)
                        right_results.extend(
                            [search_result_to_dict(r) for r in right_raw]
                        )

                    if tool_args.get("lean") == "both":
                        registry = get_default_registry()
                        left_raw = await registry.search_left(sq_query, max_results=3)
                        right_raw = await registry.search_right(sq_query, max_results=3)
                        left_results.extend(
                            [search_result_to_dict(r) for r in left_raw]
                        )
                        right_results.extend(
                            [search_result_to_dict(r) for r in right_raw]
                        )

                elif tool_name == "search_google":
                    result = await search_google.ainvoke(tool_args)
                    google_results_text = str(result)
                else:
                    result = f"unknown tool: {tool_name}"

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

        total_sources = len(left_results) + len(right_results)

        _emit_progress(
            writer,
            "sub_research",
            "synthesizing",
            f"generating draft from {total_sources} sources...",
            details={"sub_query_id": sq_id, "sources_count": total_sources},
        )

        sources_section = ""
        if left_results:
            sources_section += (
                f"LEFT-LEANING SOURCES:\n{_format_results(left_results)}\n\n"
            )
        if right_results:
            sources_section += (
                f"RIGHT-LEANING SOURCES:\n{_format_results(right_results)}\n\n"
            )
        if google_results_text:
            sources_section += f"GOOGLE SEARCH RESULTS:\n{google_results_text}\n\n"
        if not sources_section:
            sources_section = "No sources found for this query."

        prompt = DRAFT_SYNTHESIS_PROMPT.format(
            sub_query=sq_query, angle=sq_angle, sources_section=sources_section
        )

        structured_llm = get_llm(SUB_RESEARCH_MODEL).with_structured_output(DraftReport)
        result = await structured_llm.ainvoke(prompt)
        draft_report = DraftReport.model_validate(result)

        draft: Draft = {
            "sub_query_id": sq_id,
            "sub_query": sq_query,
            "angle": sq_angle,
            "left_results": left_results,
            "right_results": right_results,
            "summary": draft_report.summary,
            "key_findings": draft_report.key_findings,
            "sources_count": total_sources,
            "created_at": datetime.now(UTC).isoformat(),
        }

        _emit_progress(
            writer,
            "sub_research",
            "complete",
            f"draft generated with {len(draft_report.key_findings)} findings",
            details={
                "sub_query_id": sq_id,
                "findings_count": len(draft_report.key_findings),
                "sources_count": total_sources,
            },
        )

        _emit_draft(
            writer,
            thread_id,
            sq_id,
            sq_query,
            sq_angle,
            draft_report.summary,
            draft_report.key_findings,
            total_sources,
            cycle,
        )

        logger.info(
            f"sub_research complete for {sq_id}: {len(draft_report.key_findings)} findings, "
            f"{total_sources} sources"
        )

        return draft

    except Exception as e:
        logger.error(f"sub_research failed for {sq_id}: {e}")
        _emit_progress(
            writer,
            "sub_research",
            "error",
            f"research failed for sub-query: {str(e)[:50]}",
            details={"sub_query_id": sq_id, "error": str(e)},
        )

        fallback_draft: Draft = {
            "sub_query_id": sq_id,
            "sub_query": sq_query,
            "angle": sq_angle,
            "left_results": left_results,
            "right_results": right_results,
            "summary": f"Research failed: {str(e)[:100]}",
            "key_findings": [],
            "sources_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
        }

        return fallback_draft


async def sub_research_node(state: AgentState) -> dict:
    """process all pending sub-queries in parallel"""
    writer = get_stream_writer()
    thread_id = state.get("thread_id", "")
    cycle = state.get("supervisor_cycle", 1)

    pending = state.get("pending_sub_queries", [])
    if not pending:
        logger.warning("sub_research called with no pending sub-queries")
        return {}

    _emit_progress(
        writer,
        "sub_research",
        "starting",
        f"researching {len(pending)} sub-queries in parallel...",
        details={"sub_query_count": len(pending), "cycle": cycle},
    )

    tasks = [_research_single_query(sq, thread_id, cycle, writer) for sq in pending]
    drafts = await asyncio.gather(*tasks)

    logger.info(
        f"sub_research completed {len(drafts)} drafts in parallel for cycle {cycle}"
    )

    return {
        "drafts": list(drafts),
        "pending_sub_queries": [],
    }
