from datetime import UTC, datetime

from langgraph.config import get_stream_writer
from pydantic import BaseModel

from src.agents.llm import llm
from src.agents.prompts import CLARIFICATION_PROMPT
from src.agents.state import AgentState
from src.utils.logger import logger


class ClarificationAnalysis(BaseModel):
    needs_clarification: bool
    refined_query: str
    questions: list[str]
    suggestions: list[str] = []


def _emit_progress(writer, agent: str, status: str, message: str, **extra):
    event = {
        "agent": agent,
        "status": status,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
        **extra,
    }
    writer(event)


async def clarification_node(state: AgentState) -> dict:
    """
    analyze query clarity and refine it

    uses heuristics first, then llm if needed
    """
    query = state.get("query", "").strip()
    clarification_response = state.get("clarification_response")

    writer = get_stream_writer()
    _emit_progress(writer, "clarification", "starting", "analyzing query...")

    # if user provided clarification, incorporate it
    if clarification_response:
        refined_query = f"{query} - specifically: {clarification_response}"
        logger.info(f"query refined with clarification: {refined_query}")

        _emit_progress(
            writer, "clarification", "complete", "query refined with user clarification"
        )

        return {
            "refined_query": refined_query,
            "needs_clarification": False,
        }

    # basic heuristic checks
    if _obviously_needs_clarification(query):
        questions = _generate_clarification_questions(query)
        refined_query = _basic_query_refinement(query)

        logger.info(f"query obviously vague: {query}")
        _emit_progress(writer, "clarification", "complete", "query needs clarification")

        return {
            "refined_query": refined_query,
            "needs_clarification": True,
            "clarification_questions": questions,
        }

    # use llm for deeper analysis
    _emit_progress(
        writer, "clarification", "analyzing", "using llm to analyze query clarity..."
    )

    try:
        structured_llm = llm.with_structured_output(ClarificationAnalysis)

        prompt = CLARIFICATION_PROMPT.format(query=query)
        analysis = await structured_llm.ainvoke(prompt)

        # type assertion for mypy
        assert isinstance(analysis, ClarificationAnalysis)

        logger.info(f"llm analysis: needs_clarification={analysis.needs_clarification}")

        _emit_progress(
            writer,
            "clarification",
            "complete",
            f"query {'needs clarification' if analysis.needs_clarification else 'is clear'}",
        )

        return {
            "refined_query": analysis.refined_query,
            "needs_clarification": analysis.needs_clarification,
            "clarification_questions": analysis.questions
            if analysis.needs_clarification
            else [],
        }

    except Exception as e:
        logger.error(f"llm analysis failed: {e}")
        # fallback to basic refinement
        refined_query = _basic_query_refinement(query)

        _emit_progress(writer, "clarification", "error", f"llm analysis failed: {e}")

        return {
            "refined_query": refined_query,
            "needs_clarification": False,
        }


def _obviously_needs_clarification(query: str) -> bool:
    """heuristic check for obviously vague queries"""
    query_lower = query.lower()

    # check for vague terms
    vague_terms = ("this", "that", "it", "stuff", "things", "something")
    for term in vague_terms:
        if f" {term} " in f" {query_lower} ":
            return True

    # check for very short queries
    return len(query.split()) < 3


def _basic_query_refinement(query: str) -> str:
    """basic query cleanup"""
    refined = query.strip()
    refined = " ".join(refined.split())

    # add question mark if it looks like a question
    if not refined.endswith("?"):
        if any(
            refined.lower().startswith(w)
            for w in ["what", "why", "how", "when", "where", "who", "which", "should"]
        ):
            refined = refined + "?"

    return refined


def _generate_clarification_questions(query: str) -> list[str]:
    """generate clarification questions based on query content"""
    questions = []
    query_lower = query.lower()

    if any(
        term in query_lower
        for term in ["policy", "law", "regulation", "legislation", "bill"]
    ):
        questions.append("are you asking about federal or state-level policy?")
        questions.append("are you interested in current policy or proposed changes?")

    if any(term in query_lower for term in ["immigration", "border", "visa", "asylum"]):
        questions.append(
            "are you focused on legal immigration, illegal immigration, or both?"
        )

    if any(term in query_lower for term in ["healthcare", "health care", "medical"]):
        questions.append(
            "are you asking about private healthcare, public programs (medicare/medicaid), or the system as a whole?"
        )

    if any(term in query_lower for term in ["tax", "taxes", "taxation"]):
        questions.append(
            "are you interested in income taxes, corporate taxes, or all types?"
        )

    if len(questions) == 0:
        questions.append(
            "could you provide more specific details about what you're looking for?"
        )
        questions.append("what specific aspect of this topic interests you most?")

    return questions[:3]
