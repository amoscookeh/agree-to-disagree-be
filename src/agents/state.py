from operator import add
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    query: str
    thread_id: str
    clarification_response: str | None

    needs_clarification: bool
    clarification_questions: list[str]
    refined_query: str

    left_results: list[dict]
    right_results: list[dict]
    academic_results: list[dict]

    summary: str
    claim_a: dict
    claim_b: dict
    agreements: list[str]
    disagreements: list[dict]
    uncertainties: list[str]

    citation_score: float
    needs_more_research: bool
    research_loop_count: int

    citations: list[dict]
    report: dict | None

    error: str | None
    current_agent: str

    progress_updates: Annotated[list[dict], add]
