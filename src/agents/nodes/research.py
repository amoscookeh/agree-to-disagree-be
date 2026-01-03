from datetime import UTC, datetime

from langgraph.config import get_stream_writer

from src.agents.state import AgentState
from src.data_sources import DataSourceRegistry
from src.data_sources.left_leaning import GuardianSource, NYTSource
from src.data_sources.right_leaning import NewsAPISource, NYPostRSSSource
from src.utils.logger import logger


def _create_registry() -> DataSourceRegistry:
    registry = DataSourceRegistry()

    registry.register_left(GuardianSource())
    registry.register_left(NYTSource())

    registry.register_right(NYPostRSSSource())
    registry.register_right(NewsAPISource())

    return registry


def _search_result_to_dict(result) -> dict:
    return {
        "title": result.title,
        "url": result.url,
        "snippet": result.snippet,
        "published_date": result.published_date,
        "source_name": result.source_name,
        "ideological_lean": result.ideological_lean.value,
    }


def _emit_progress(
    writer, agent: str, status: str, message: str, details: dict | None = None, **extra
):
    event = {
        "type": "progress",
        "data": {
            "agent": agent,
            "status": status,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **({"details": details} if details else {}),
            **extra,
        },
    }
    if writer:
        writer(event)
    return event


async def research_node(state: AgentState) -> dict:
    writer = get_stream_writer()
    query = state.get("refined_query") or state.get("query", "")

    if not query:
        _emit_progress(
            writer,
            "research",
            "error",
            "No query provided for research",
            details={"error": "missing query"},
        )
        return {"error": "no query provided"}

    _emit_progress(
        writer,
        "research",
        "starting",
        "Starting research for query",
        details={"query": query, "stage": "initialization"},
    )

    registry = _create_registry()
    sources = registry.list_sources()
    left_sources = [s for s in sources if s["lean"] == "left"]
    right_sources = [s for s in sources if s["lean"] == "right"]

    _emit_progress(
        writer,
        "research",
        "searching",
        f"Searching {len(sources)} data sources in parallel",
        details={
            "query_sent": query,
            "left_sources": [s["name"] for s in left_sources],
            "right_sources": [s["name"] for s in right_sources],
        },
        sources_searched=[s["name"] for s in sources],
    )

    try:
        for source in left_sources:
            _emit_progress(
                writer,
                "left_research",
                "searching",
                f"Searching {source['name']}",
                details={
                    "source": source["name"],
                    "query_sent": query,
                    "lean": "left",
                },
            )

        for source in right_sources:
            _emit_progress(
                writer,
                "right_research",
                "searching",
                f"Searching {source['name']}",
                details={
                    "source": source["name"],
                    "query_sent": query,
                    "lean": "right",
                },
            )

        all_results = await registry.search_all(query, max_results=5)

        left_results = [_search_result_to_dict(r) for r in all_results.get("left", [])]
        right_results = [
            _search_result_to_dict(r) for r in all_results.get("right", [])
        ]
        academic_results = [
            _search_result_to_dict(r) for r in all_results.get("academic", [])
        ]

        _emit_progress(
            writer,
            "left_research",
            "complete",
            f"Found {len(left_results)} results from left-leaning sources",
            details={
                "result_count": len(left_results),
                "sample_titles": [r["title"][:60] for r in left_results[:3]],
                "sources_with_results": list({r["source_name"] for r in left_results}),
            },
            results_count=len(left_results),
        )

        _emit_progress(
            writer,
            "right_research",
            "complete",
            f"Found {len(right_results)} results from right-leaning sources",
            details={
                "result_count": len(right_results),
                "sample_titles": [r["title"][:60] for r in right_results[:3]],
                "sources_with_results": list({r["source_name"] for r in right_results}),
            },
            results_count=len(right_results),
        )

        total_results = len(left_results) + len(right_results) + len(academic_results)

        logger.info(
            f"research complete: {len(left_results)} left, {len(right_results)} right, {len(academic_results)} academic"
        )

        _emit_progress(
            writer,
            "research",
            "complete",
            f"Research complete - found {total_results} total results",
            details={
                "left_count": len(left_results),
                "right_count": len(right_results),
                "academic_count": len(academic_results),
                "total_count": total_results,
            },
            results_count=total_results,
        )

        return {
            "left_results": left_results,
            "right_results": right_results,
            "academic_results": academic_results,
            "current_agent": "research",
        }

    except Exception as e:
        logger.error(f"research node error: {e}")
        _emit_progress(
            writer,
            "research",
            "error",
            "Research failed",
            details={"error": str(e), "query": query},
        )
        return {
            "left_results": [],
            "right_results": [],
            "academic_results": [],
            "error": str(e),
        }
