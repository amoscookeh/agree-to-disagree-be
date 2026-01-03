import asyncio
from datetime import UTC, datetime

from langgraph.config import get_stream_writer
from pydantic import BaseModel

from src.agents.llm import llm
from src.agents.state import AgentState, Draft, SubQuery
from src.data_sources import get_default_registry, search_result_to_dict
from src.utils.logger import logger


class DraftReport(BaseModel):
    summary: str
    key_findings: list[str]
    left_perspective: str | None = None
    right_perspective: str | None = None


DRAFT_SYNTHESIS_PROMPT = """you are synthesizing research results for a specific sub-query.

sub-query: {sub_query}
angle: {angle}

{sources_section}

create a brief synthesis covering:
1. main findings from the sources
2. key points relevant to the sub-query
3. any notable perspectives or disagreements found

respond with:
- summary: a 2-3 sentence synthesis of findings
- key_findings: 2-4 bullet points of important findings
- left_perspective: (if applicable) what left-leaning sources emphasized
- right_perspective: (if applicable) what right-leaning sources emphasized
"""


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
    """research a single sub-query and return draft"""
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

    registry = get_default_registry()
    left_results: list[dict] = []
    right_results: list[dict] = []

    try:
        if sq_angle in ("left", "both"):
            _emit_progress(
                writer,
                "sub_research",
                "searching",
                "searching left-leaning sources...",
                details={"sub_query_id": sq_id, "angle": "left"},
            )
            left_raw = await registry.search_left(sq_query, max_results=3)
            left_results = [search_result_to_dict(r) for r in left_raw]

        if sq_angle in ("right", "both"):
            _emit_progress(
                writer,
                "sub_research",
                "searching",
                "searching right-leaning sources...",
                details={"sub_query_id": sq_id, "angle": "right"},
            )
            right_raw = await registry.search_right(sq_query, max_results=3)
            right_results = [search_result_to_dict(r) for r in right_raw]

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
        if not sources_section:
            sources_section = "No sources found for this query."

        prompt = DRAFT_SYNTHESIS_PROMPT.format(
            sub_query=sq_query, angle=sq_angle, sources_section=sources_section
        )

        structured_llm = llm.with_structured_output(DraftReport)
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
