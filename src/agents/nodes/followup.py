from datetime import UTC, datetime

from langchain.tools import ToolRuntime, tool
from langchain_core.prompts import ChatPromptTemplate
from langgraph.config import get_stream_writer

from src.agents.llm import llm
from src.agents.state import AgentState
from src.data_sources import DataSourceRegistry
from src.data_sources.left_leaning import GuardianSource, NYTSource
from src.data_sources.right_leaning import NewsAPISource, NYPostRSSSource
from src.utils.logger import logger


def _create_registry() -> DataSourceRegistry:
    """create data source registry with left/right sources"""
    registry = DataSourceRegistry()

    registry.register_left(GuardianSource())
    registry.register_left(NYTSource())

    registry.register_right(NYPostRSSSource())
    registry.register_right(NewsAPISource())

    return registry


def _emit_progress(writer, agent: str, status: str, message: str, **extra):
    event = {
        "type": "progress",
        "agent": agent,
        "status": status,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
        **extra,
    }
    if writer:
        writer(event)
    return event


def _format_report(state: AgentState) -> str:
    """format the report for context"""
    report = state.get("report")
    if not report or not isinstance(report, dict):
        return "No report available."

    summary = report.get("summary", "")
    claim_a = report.get("claim_a", {}) if isinstance(report.get("claim_a"), dict) else {}
    claim_b = report.get("claim_b", {}) if isinstance(report.get("claim_b"), dict) else {}
    agreements = report.get("agreements", []) if isinstance(report.get("agreements"), list) else []
    disagreements = report.get("disagreements", []) if isinstance(report.get("disagreements"), list) else []

    formatted = f"""
Report Summary:
{summary}

Left Perspective ({claim_a.get("stance", "N/A")}): {claim_a.get("title", "N/A")}
Evidence:
"""
    for i, evidence in enumerate(claim_a.get("evidence", [])[:3], 1):
        formatted += f"{i}. {evidence.get('claim', 'N/A')} (Source: {evidence.get('source', 'N/A')})\n"

    formatted += f"\nRight Perspective ({claim_b.get('stance', 'N/A')}): {claim_b.get('title', 'N/A')}\nEvidence:\n"
    for i, evidence in enumerate(claim_b.get("evidence", [])[:3], 1):
        formatted += f"{i}. {evidence.get('claim', 'N/A')} (Source: {evidence.get('source', 'N/A')})\n"

    formatted += f"\nAgreements: {', '.join(agreements[:3])}\n"
    formatted += f"Disagreements: {len(disagreements)} key points of disagreement\n"

    return formatted.strip()


# create tools for the follow-up agent
@tool
async def search_left_sources(query: str, runtime: ToolRuntime) -> str:
    """search left-leaning news sources for information"""
    writer = runtime.stream_writer

    writer(
        {
            "type": "progress",
            "agent": "followup_tool",
            "status": "searching",
            "message": f"searching left-leaning sources for: {query}",
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_call": {
                "tool": "search_left_sources",
                "query": query,
                "sources": ["The Guardian", "New York Times"],
            },
        }
    )

    registry = _create_registry()
    results = await registry.search_left(query, max_results=5)

    if not results:
        return "no results found from left-leaning sources."

    formatted = []
    for r in results[:5]:
        formatted.append(
            f"- {r.title}\n"
            f"  Source: {r.source_name}\n"
            f"  Snippet: {r.snippet}\n"
            f"  URL: {r.url}"
        )

    writer(
        {
            "type": "progress",
            "agent": "followup_tool",
            "status": "complete",
            "message": f"found {len(results)} results from left-leaning sources",
            "timestamp": datetime.now(UTC).isoformat(),
            "results_count": len(results),
        }
    )

    return "\n\n".join(formatted)


@tool
async def search_right_sources(query: str, runtime: ToolRuntime) -> str:
    """search right-leaning news sources for information"""
    writer = runtime.stream_writer

    writer(
        {
            "type": "progress",
            "agent": "followup_tool",
            "status": "searching",
            "message": f"searching right-leaning sources for: {query}",
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_call": {
                "tool": "search_right_sources",
                "query": query,
                "sources": ["NY Post", "NewsAPI"],
            },
        }
    )

    registry = _create_registry()
    results = await registry.search_right(query, max_results=5)

    if not results:
        return "no results found from right-leaning sources."

    formatted = []
    for r in results[:5]:
        formatted.append(
            f"- {r.title}\n"
            f"  Source: {r.source_name}\n"
            f"  Snippet: {r.snippet}\n"
            f"  URL: {r.url}"
        )

    writer(
        {
            "type": "progress",
            "agent": "followup_tool",
            "status": "complete",
            "message": f"found {len(results)} results from right-leaning sources",
            "timestamp": datetime.now(UTC).isoformat(),
            "results_count": len(results),
        }
    )

    return "\n\n".join(formatted)


@tool
def get_report_context(runtime: ToolRuntime) -> str:
    """get the full context of the previously generated research report"""
    state_dict = runtime.state if hasattr(runtime, "state") else {}
    return _format_report(state_dict)  # type: ignore[arg-type]


async def followup_node(state: AgentState) -> dict:
    """
    handle follow-up questions using a general agent with access to tools

    the agent can:
    - search left-leaning sources
    - search right-leaning sources
    - access the full report context
    """
    writer = get_stream_writer()
    query = state.get("query", "").strip()

    _emit_progress(
        writer,
        "followup",
        "starting",
        f"processing follow-up question: {query}",
        query=query,
    )

    # simplified implementation without langchain agents (not available in current version)
    # tools = [search_left_sources, search_right_sources, get_report_context]

    # get report context
    report_context = _format_report(state)

    # format conversation history
    messages_obj = state.get("messages", [])
    messages_list = messages_obj if isinstance(messages_obj, list) else []
    chat_history_lines = []
    for msg in messages_list[-5:]:  # last 5 messages
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                chat_history_lines.append(f"User: {content}")
            elif role == "assistant":
                chat_history_lines.append(f"Assistant: {content}")

    prompt_text = f"""you are a helpful political research assistant answering follow-up questions.

previous report context:
{report_context}

conversation history:
{chr(10).join(chat_history_lines) if chat_history_lines else "No previous conversation."}

user question: {query}

provide a concise, balanced answer based on the report context. if the question requires information not in the report, acknowledge that and suggest what additional research would be needed."""

    # placeholder for proper prompt template
    _unused_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """you are a helpful political research assistant answering follow-up questions.

you have access to:
1. the previous research report (use get_report_context)
2. left-leaning news sources (use search_left_sources)
3. right-leaning news sources (use search_right_sources)

guidelines:
- always start by getting the report context if the question is about the report
- search additional sources if needed for more details
- provide balanced answers citing both perspectives when relevant
- be concise but thorough
- cite sources when providing new information

previous report is available in the conversation context.""",
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    _emit_progress(
        writer,
        "followup",
        "analyzing",
        "generating answer based on report context...",
        query=query,
    )

    try:
        # use llm directly for now (agent executor not available in current langchain version)
        from langchain_core.messages import HumanMessage

        response = await llm.ainvoke([HumanMessage(content=prompt_text)])

        result = {"output": response.content}

        answer = result.get("output", "I couldn't find an answer to your question.")

        logger.info(f"followup agent completed: {len(answer)} chars")

        _emit_progress(
            writer,
            "followup",
            "complete",
            "follow-up answer generated",
            query=query,
            answer_length=len(answer),
        )

        return {
            "followup_answer": answer,
            "current_agent": "followup",
        }

    except Exception as e:
        logger.error(f"followup agent failed: {e}")

        _emit_progress(
            writer,
            "followup",
            "error",
            f"failed to answer follow-up: {e}",
        )

        return {
            "followup_answer": f"I encountered an error while trying to answer your question: {e}",
            "error": str(e),
            "current_agent": "followup",
        }
