from datetime import UTC, datetime

from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from src.agents.llm import llm
from src.agents.state import AgentState, Draft, SubQuery
from src.utils.logger import logger


class SubQueryItem(BaseModel):
    query: str
    angle: str = Field(description="left, right, or both")
    rationale: str


class SubQueryGeneration(BaseModel):
    sub_queries: list[SubQueryItem]


class SupervisorDecision(BaseModel):
    has_sufficient_info: bool
    reasoning: str
    new_sub_queries: list[SubQueryItem] = []


SUPERVISOR_INITIAL_PROMPT = """you are a research supervisor planning a balanced political investigation.

given this query, generate 2-4 sub-queries that will help gather comprehensive perspectives:

query: {query}

guidelines:
- each sub-query should focus on a specific aspect or angle
- use "left" angle for questions best answered by progressive/liberal sources
- use "right" angle for questions best answered by conservative sources
- use "both" angle for factual/data questions that need all perspectives
- aim for balance between left, right, and both angles
- make sub-queries specific and searchable

respond with a list of sub-queries, each with:
- query: the specific question to research
- angle: "left", "right", or "both"
- rationale: why this sub-query is important
"""

SUPERVISOR_REVIEW_PROMPT = """you are a research supervisor reviewing collected drafts.

original query: {query}

drafts collected so far (cycle {cycle}):
{drafts_summary}

decide whether:
1. we have sufficient information to create a comprehensive balanced report
2. or we need more research on specific gaps

if more research is needed, suggest new sub-queries focusing on gaps.
max cycles allowed: 5, current cycle: {cycle}

respond with:
- has_sufficient_info: true if ready for synthesis, false if need more research
- reasoning: explain your decision
- new_sub_queries: only if has_sufficient_info is false, list 1-2 new sub-queries
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


def _emit_sub_queries(writer, thread_id: str, cycle: int, sub_queries: list[SubQuery]):
    event = {
        "type": "sub_queries",
        "data": {
            "thread_id": thread_id,
            "cycle": cycle,
            "sub_queries": [
                {"id": sq["id"], "query": sq["query"], "angle": sq["angle"]}
                for sq in sub_queries
            ],
        },
    }
    if writer:
        writer(event)
    return event


def _emit_supervisor_decision(
    writer,
    thread_id: str,
    cycle: int,
    decision: str,
    reasoning: str,
    drafts_collected: int,
    new_sub_queries_count: int = 0,
):
    event = {
        "type": "supervisor_decision",
        "data": {
            "thread_id": thread_id,
            "cycle": cycle,
            "decision": decision,
            "reasoning": reasoning,
            "drafts_collected": drafts_collected,
            "new_sub_queries_count": new_sub_queries_count,
        },
    }
    if writer:
        writer(event)
    return event


def _format_drafts_summary(drafts: list[Draft]) -> str:
    if not drafts:
        return "No drafts collected yet."

    summaries = []
    for d in drafts:
        summaries.append(
            f"- Sub-query ({d.get('angle', 'unknown')}): {d.get('sub_query', 'N/A')}\n"
            f"  Summary: {d.get('summary', 'N/A')[:200]}...\n"
            f"  Key findings: {len(d.get('key_findings', []))} items"
        )
    return "\n\n".join(summaries)


async def supervisor_node(state: AgentState) -> dict:
    writer = get_stream_writer()
    thread_id = state.get("thread_id", "")
    query = state.get("refined_query") or state.get("query", "")
    drafts = state.get("drafts", [])
    current_cycle = state.get("supervisor_cycle", 0)

    if not drafts:
        _emit_progress(
            writer,
            "supervisor",
            "analyzing",
            "analyzing query to plan research directions...",
            details={"query": query[:100]},
        )

        prompt = SUPERVISOR_INITIAL_PROMPT.format(query=query)

        try:
            structured_llm = llm.with_structured_output(SubQueryGeneration)
            result = await structured_llm.ainvoke(prompt)
            generation = SubQueryGeneration.model_validate(result)

            sub_queries: list[SubQuery] = []
            for i, sq in enumerate(generation.sub_queries, 1):
                sub_queries.append(
                    SubQuery(
                        id=f"sq-{i}",
                        query=sq.query,
                        angle=sq.angle
                        if sq.angle in ("left", "right", "both")
                        else "both",  # type: ignore[typeddict-item]
                        status="pending",
                    )
                )

            _emit_progress(
                writer,
                "supervisor",
                "generating",
                f"generated {len(sub_queries)} research directions",
                details={"sub_query_count": len(sub_queries), "cycle": 1},
            )

            _emit_sub_queries(writer, thread_id, 1, sub_queries)

            logger.info(
                f"supervisor generated {len(sub_queries)} sub-queries for: {query[:50]}..."
            )

            return {
                "sub_queries": sub_queries,
                "pending_sub_queries": sub_queries.copy(),
                "supervisor_cycle": 1,
                "ready_for_synthesis": False,
            }

        except Exception as e:
            logger.error(f"supervisor initial generation failed: {e}")
            _emit_progress(
                writer,
                "supervisor",
                "error",
                "failed to generate sub-queries",
                details={"error": str(e)},
            )
            return {"error": str(e), "ready_for_synthesis": True}

    else:
        new_cycle = current_cycle + 1

        _emit_progress(
            writer,
            "supervisor",
            "reviewing",
            f"reviewing {len(drafts)} collected drafts...",
            details={"draft_count": len(drafts), "cycle": new_cycle},
        )

        if new_cycle >= 5:
            logger.info(
                f"supervisor reached max cycles ({new_cycle}), forcing synthesis"
            )
            _emit_progress(
                writer,
                "supervisor",
                "complete",
                "max research cycles reached, proceeding to synthesis",
                details={"total_drafts": len(drafts), "cycles_used": new_cycle},
            )
            _emit_supervisor_decision(
                writer,
                thread_id,
                new_cycle,
                "synthesize",
                "reached maximum research cycles",
                len(drafts),
            )
            return {
                "supervisor_cycle": new_cycle,
                "supervisor_reasoning": "reached maximum research cycles",
                "ready_for_synthesis": True,
            }

        prompt = SUPERVISOR_REVIEW_PROMPT.format(
            query=query,
            cycle=new_cycle,
            drafts_summary=_format_drafts_summary(drafts),
        )

        try:
            structured_llm = llm.with_structured_output(SupervisorDecision)
            result = await structured_llm.ainvoke(prompt)
            decision = SupervisorDecision.model_validate(result)

            if decision.has_sufficient_info or not decision.new_sub_queries:
                _emit_progress(
                    writer,
                    "supervisor",
                    "complete",
                    "sufficient information gathered",
                    details={"total_drafts": len(drafts), "cycles_used": new_cycle},
                )
                _emit_supervisor_decision(
                    writer,
                    thread_id,
                    new_cycle,
                    "synthesize",
                    decision.reasoning,
                    len(drafts),
                )

                logger.info(
                    f"supervisor decided to synthesize after {new_cycle} cycles, "
                    f"{len(drafts)} drafts: {decision.reasoning[:100]}..."
                )

                return {
                    "supervisor_cycle": new_cycle,
                    "supervisor_reasoning": decision.reasoning,
                    "ready_for_synthesis": True,
                }

            else:
                existing_ids = {sq["id"] for sq in state.get("sub_queries", [])}
                start_id = len(existing_ids) + 1

                new_sub_queries: list[SubQuery] = []
                for i, sq in enumerate(decision.new_sub_queries):
                    new_sub_queries.append(
                        SubQuery(
                            id=f"sq-{start_id + i}",
                            query=sq.query,
                            angle=sq.angle
                            if sq.angle in ("left", "right", "both")
                            else "both",  # type: ignore[typeddict-item]
                            status="pending",
                        )
                    )

                _emit_progress(
                    writer,
                    "supervisor",
                    "generating",
                    f"generating {len(new_sub_queries)} additional sub-queries",
                    details={
                        "sub_query_count": len(new_sub_queries),
                        "cycle": new_cycle,
                        "reason": decision.reasoning[:100],
                    },
                )

                _emit_supervisor_decision(
                    writer,
                    thread_id,
                    new_cycle,
                    "continue",
                    decision.reasoning,
                    len(drafts),
                    len(new_sub_queries),
                )

                _emit_sub_queries(writer, thread_id, new_cycle, new_sub_queries)

                all_sub_queries = state.get("sub_queries", []) + new_sub_queries

                logger.info(
                    f"supervisor continuing research, cycle {new_cycle}, "
                    f"adding {len(new_sub_queries)} sub-queries: {decision.reasoning[:50]}..."
                )

                return {
                    "sub_queries": all_sub_queries,
                    "pending_sub_queries": new_sub_queries,
                    "supervisor_cycle": new_cycle,
                    "supervisor_reasoning": decision.reasoning,
                    "ready_for_synthesis": False,
                }

        except Exception as e:
            logger.error(f"supervisor review failed: {e}")
            _emit_progress(
                writer,
                "supervisor",
                "error",
                "failed to review drafts, proceeding to synthesis",
                details={"error": str(e)},
            )
            return {
                "supervisor_cycle": new_cycle,
                "supervisor_reasoning": f"review failed: {e}",
                "ready_for_synthesis": True,
            }
