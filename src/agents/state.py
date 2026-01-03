from operator import add
from typing import Annotated, Literal, TypedDict


class SubQuery(TypedDict):
    id: str
    query: str
    angle: Literal["left", "right", "both"]
    status: Literal["pending", "researching", "complete"]


class Draft(TypedDict, total=False):
    sub_query_id: str
    sub_query: str
    angle: str
    left_results: list[dict]
    right_results: list[dict]
    summary: str
    key_findings: list[str]
    sources_count: int
    created_at: str


class AgentState(TypedDict, total=False):
    query: str
    thread_id: str
    clarification_response: str | None
    message_type: str

    needs_clarification: bool
    clarification_questions: list[str]
    clarification_suggestions: list[str]
    refined_query: str | None

    sub_queries: list[SubQuery]
    drafts: Annotated[list[Draft], add]
    supervisor_cycle: int
    supervisor_reasoning: str
    pending_sub_queries: list[SubQuery]
    current_sub_query: SubQuery | None
    ready_for_synthesis: bool

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

    followup_answer: str | None
    followup_citations: list[dict]

    messages: Annotated[list[dict], add]

    error: str | None
    current_agent: str | None
    progress_updates: Annotated[list[dict], add]
