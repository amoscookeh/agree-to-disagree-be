from datetime import UTC, datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from pydantic import BaseModel

from src.agents.llm import llm
from src.agents.state import AgentState
from src.data_sources import get_default_registry
from src.utils.logger import logger

MAX_TOOL_CALLS = 10


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
    claim_a = (
        report.get("claim_a", {}) if isinstance(report.get("claim_a"), dict) else {}
    )
    claim_b = (
        report.get("claim_b", {}) if isinstance(report.get("claim_b"), dict) else {}
    )
    agreements = (
        report.get("agreements", [])
        if isinstance(report.get("agreements"), list)
        else []
    )
    disagreements = (
        report.get("disagreements", [])
        if isinstance(report.get("disagreements"), list)
        else []
    )

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


def _format_conversation_history(messages: list[dict]) -> str:
    """format conversation history for context"""
    if not messages:
        return "No previous conversation."

    formatted = []
    for msg in messages[-10:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", {})
        if isinstance(content, dict):
            if content.get("type") == "query":
                formatted.append(f"User: {content.get('query', '')}")
            elif content.get("type") == "clarification_response":
                formatted.append(f"User: {content.get('response', '')}")
            elif role == "followup":
                formatted.append(f"Assistant: {content.get('answer', '')}")
            elif role == "report":
                formatted.append("Assistant: [Generated research report]")
        elif isinstance(content, str):
            formatted.append(f"{role.title()}: {content[:200]}...")

    return "\n".join(formatted)


class ToolCall(BaseModel):
    tool: str  # "search_left", "search_right", "done"
    query: str | None = None
    answer: str | None = None
    reasoning: str


async def _search_sources(query: str, lean: str, writer) -> tuple[str, list[dict]]:
    """search sources by ideological lean (left or right)"""
    _emit_progress(
        writer,
        "followup",
        "searching",
        f"searching {lean}-leaning sources for: {query}",
        tool_call={"tool": f"search_{lean}", "query": query},
    )

    registry = get_default_registry()
    if lean == "left":
        results = await registry.search_left(query, max_results=5)
    else:
        results = await registry.search_right(query, max_results=5)

    if not results:
        return f"No results found from {lean}-leaning sources.", []

    citations = []
    formatted = []
    for r in results[:5]:
        formatted.append(
            f"- {r.title}\n  Source: {r.source_name}\n  Snippet: {r.snippet}\n  URL: {r.url}"
        )
        citations.append(
            {
                "source_name": r.source_name,
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "ideological_lean": lean,
            }
        )

    _emit_progress(
        writer,
        "followup",
        "complete",
        f"found {len(results)} results from {lean}-leaning sources",
        results_count=len(results),
    )

    return "\n\n".join(formatted), citations


async def followup_node(state: AgentState) -> dict:
    """
    handle follow-up questions using iterative tool calling

    the agent can:
    - search left-leaning sources (search_left)
    - search right-leaning sources (search_right)
    - finish with an answer (done)

    max 10 tool calls before forcing completion
    """
    writer = get_stream_writer()
    query = state.get("query", "").strip()
    messages = state.get("messages", [])

    _emit_progress(
        writer,
        "followup",
        "starting",
        f"processing follow-up question: {query}",
        query=query,
    )

    report_context = _format_report(state)
    messages_list = messages if isinstance(messages, list) else []
    conversation_history = _format_conversation_history(messages_list)

    system_prompt = f"""you are a helpful political research assistant answering follow-up questions.

you have access to these tools:
1. search_left - search left-leaning news sources (The Guardian, NYT)
2. search_right - search right-leaning news sources (NY Post, NewsAPI)
3. done - provide your final answer

previous report context:
{report_context}

conversation history:
{conversation_history}

guidelines:
- if the question can be answered from the report context, answer directly using "done"
- if you need more information, search left and/or right sources
- provide balanced answers citing both perspectives when relevant
- be concise but thorough
- cite sources when providing new information
- you can call search tools multiple times with different queries
- max {MAX_TOOL_CALLS} tool calls allowed

respond with a JSON object containing:
- "tool": one of "search_left", "search_right", or "done"
- "query": search query if using search tools (null for done)
- "answer": your final answer if using done (null otherwise)
- "reasoning": brief explanation of your choice"""

    chat_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User question: {query}"),
    ]

    tool_calls_made = 0
    search_results: list[str] = []
    all_citations: list[dict] = []
    structured_llm = llm.with_structured_output(ToolCall)

    while tool_calls_made < MAX_TOOL_CALLS:
        _emit_progress(
            writer,
            "followup",
            "analyzing",
            f"deciding next action (tool call {tool_calls_made + 1}/{MAX_TOOL_CALLS})...",
            tool_calls_made=tool_calls_made,
        )

        try:
            tool_call = await structured_llm.ainvoke(chat_messages)
            assert isinstance(tool_call, ToolCall)
            tool_calls_made += 1

            logger.info(
                f"followup tool call {tool_calls_made}: {tool_call.tool} "
                f"(reasoning: {tool_call.reasoning})"
            )

            if tool_call.tool == "done":
                answer = tool_call.answer or "I couldn't formulate an answer."

                _emit_progress(
                    writer,
                    "followup",
                    "complete",
                    "follow-up answer generated",
                    answer_length=len(answer),
                    tool_calls_made=tool_calls_made,
                    citations_count=len(all_citations),
                )

                return {
                    "followup_answer": answer,
                    "followup_citations": all_citations,
                    "current_agent": "followup",
                }

            elif tool_call.tool in ("search_left", "search_right"):
                lean = "left" if tool_call.tool == "search_left" else "right"
                search_query = tool_call.query or query
                result, citations = await _search_sources(search_query, lean, writer)
                search_results.append(
                    f"{lean.title()}-leaning sources for '{search_query}':\n{result}"
                )
                all_citations.extend(citations)

                chat_messages.append(
                    AIMessage(
                        content=f"Called {tool_call.tool} with query: {search_query}"
                    )
                )
                chat_messages.append(
                    HumanMessage(
                        content=f"Search results:\n{result}\n\nContinue or provide final answer."
                    )
                )

            else:
                logger.warning(f"unknown tool: {tool_call.tool}, treating as done")
                answer = tool_call.answer or "I couldn't process your request properly."
                return {
                    "followup_answer": answer,
                    "followup_citations": all_citations,
                    "current_agent": "followup",
                }

        except Exception as e:
            logger.error(f"followup tool call failed: {e}")
            _emit_progress(
                writer,
                "followup",
                "error",
                f"tool call failed: {e}",
            )
            break

    # max tool calls reached, force completion
    _emit_progress(
        writer,
        "followup",
        "analyzing",
        f"max tool calls ({MAX_TOOL_CALLS}) reached, generating final answer...",
    )

    final_prompt = f"""based on all the information gathered, provide a final answer to the user's question.

user question: {query}

search results gathered:
{chr(10).join(search_results) if search_results else "No additional searches performed."}

provide a concise, balanced answer citing relevant sources."""

    try:
        response = await llm.ainvoke([HumanMessage(content=final_prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        answer = content if isinstance(content, str) else str(content)

        _emit_progress(
            writer,
            "followup",
            "complete",
            "follow-up answer generated (forced completion)",
            answer_length=len(answer),
            tool_calls_made=tool_calls_made,
            citations_count=len(all_citations),
        )

        return {
            "followup_answer": answer,
            "followup_citations": all_citations,
            "current_agent": "followup",
        }

    except Exception as e:
        logger.error(f"followup final answer failed: {e}")

        _emit_progress(
            writer,
            "followup",
            "error",
            f"failed to answer follow-up: {e}",
        )

        return {
            "followup_answer": f"I encountered an error while processing your question: {e}",
            "followup_citations": all_citations,
            "error": str(e),
            "current_agent": "followup",
        }
