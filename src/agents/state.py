from operator import add
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    # input
    query: str
    thread_id: str
    clarification_response: str | None

    # classification
    message_type: str  # "research_prompt" or "follow_up_question"

    # clarification
    needs_clarification: bool
    clarification_questions: list[str]
    clarification_suggestions: list[str]
    refined_query: str | None

    # research results
    left_results: list[dict]
    right_results: list[dict]
    academic_results: list[dict]

    # synthesis output
    summary: str
    claim_a: dict
    claim_b: dict
    agreements: list[str]
    disagreements: list[dict]
    uncertainties: list[str]

    # quality check
    citation_score: float
    needs_more_research: bool
    research_loop_count: int

    # output
    citations: list[dict]
    report: dict | None

    # followup output
    followup_answer: str | None
    followup_citations: list[dict]

    # conversation history (for classification context)
    messages: Annotated[list[dict], add]

    # tracking
    error: str | None
    current_agent: str | None
    progress_updates: Annotated[list[dict], add]
