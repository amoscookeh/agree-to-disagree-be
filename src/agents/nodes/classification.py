from datetime import UTC, datetime

from langgraph.config import get_stream_writer
from pydantic import BaseModel

from prompts.classification import CLASSIFICATION_PROMPT
from prompts.models import CLASSIFICATION_MODEL
from src.agents.llm import get_llm
from src.agents.state import AgentState
from src.utils.logger import logger


class MessageClassification(BaseModel):
    message_type: str  # "research_prompt" or "follow_up_question"
    confidence: float
    reasoning: str


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


def _format_conversation_history(messages: list[dict]) -> str:
    """format conversation history for llm context"""
    if not messages:
        return "No previous conversation."

    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if isinstance(content, dict):
            if content.get("type") == "query":
                content = content.get("query", "")
            elif content.get("type") == "clarification_response":
                content = content.get("response", "")
            elif "answer" in content:
                content = content.get("answer", "")
            elif "summary" in content:
                content = f"[Report: {content.get('summary', '')[:100]}...]"
            else:
                content = str(content)

        content_str = str(content)[:200]
        formatted.append(f"{role}: {content_str}...")

    return "\n".join(formatted[-10:])


def _format_report(state: AgentState) -> str:
    """format the generated report if it exists"""
    report = state.get("report")
    if not report:
        return "No report generated yet."

    summary = report.get("summary", "")
    claim_a = report.get("claim_a", {})
    claim_b = report.get("claim_b", {})

    formatted = f"""
Previous Report Summary:
{summary}

Left Perspective: {claim_a.get("title", "N/A")}
Right Perspective: {claim_b.get("title", "N/A")}

Agreements: {len(report.get("agreements", []))} points
Disagreements: {len(report.get("disagreements", []))} points
"""
    return formatted.strip()


async def classification_node(state: AgentState) -> dict:
    """classify incoming message as research prompt or follow-up question"""
    writer = get_stream_writer()
    query = state.get("query", "").strip()
    messages = state.get("messages", [])

    _emit_progress(
        writer,
        "classification",
        "starting",
        "classifying message type...",
        query=query,
    )

    messages_list = messages if isinstance(messages, list) else []
    if not messages_list or len(messages_list) == 0:
        logger.info("first message in conversation, classifying as research_prompt")

        _emit_progress(
            writer,
            "classification",
            "complete",
            "classified as new research prompt",
            message_type="research_prompt",
            is_first_message=True,
        )

        return {
            "message_type": "research_prompt",
            "current_agent": "classification",
        }

    _emit_progress(
        writer,
        "classification",
        "analyzing",
        "using llm to classify message type...",
        query=query,
        tool_call={
            "tool": "llm_classify_message",
            "model": CLASSIFICATION_MODEL.model_id,
            "query": query,
            "context_messages": len(messages_list),
            "output_schema": "MessageClassification",
        },
    )

    conversation_history = _format_conversation_history(messages_list)
    report_context = _format_report(state)

    prompt = CLASSIFICATION_PROMPT.format(
        conversation_history=conversation_history,
        report_context=report_context,
        query=query,
    )

    try:
        llm = get_llm(CLASSIFICATION_MODEL)
        structured_llm = llm.with_structured_output(MessageClassification)
        classification = await structured_llm.ainvoke(prompt)

        assert isinstance(classification, MessageClassification)

        logger.info(
            f"message classified as {classification.message_type} "
            f"(confidence: {classification.confidence:.2f})"
        )

        _emit_progress(
            writer,
            "classification",
            "complete",
            f"classified as {classification.message_type}",
            message_type=classification.message_type,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
        )

        return {
            "message_type": classification.message_type,
            "current_agent": "classification",
        }

    except Exception as e:
        logger.error(f"classification failed: {e}, defaulting to research_prompt")

        _emit_progress(
            writer,
            "classification",
            "error",
            f"classification failed: {e}, defaulting to research_prompt",
        )

        return {
            "message_type": "research_prompt",
            "current_agent": "classification",
        }
