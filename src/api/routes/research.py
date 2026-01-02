import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.graph import research_graph
from src.agents.nodes.research import _create_registry
from src.agents.state import AgentState
from src.api.deps import check_quota
from src.db.client import get_supabase
from src.utils.logger import logger

router = APIRouter(prefix="/api", tags=["research"])


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    clarification_response: str | None = None


class SourceInfo(BaseModel):
    name: str
    lean: str
    enabled: bool


@router.post("/research")
async def research(request: ResearchRequest, user: dict = Depends(check_quota)):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(f"research request: {query[:50]}...")

    initial_state: AgentState = {
        "query": query,
    }

    if request.clarification_response:
        initial_state["clarification_response"] = request.clarification_response

    async def event_generator():
        research_completed = False
        try:
            async for chunk in research_graph.astream(
                initial_state,
                stream_mode="custom",
            ):
                yield f"data: {json.dumps(chunk)}\n\n"

            final_state = await research_graph.ainvoke(initial_state)

            if (
                final_state.get("needs_clarification")
                and not request.clarification_response
            ):
                clarification_event = {
                    "type": "clarification",
                    "data": {
                        "thread_id": final_state.get("thread_id", ""),
                        "refined_query": final_state.get("refined_query", query),
                        "questions": final_state.get("clarification_questions", []),
                        "suggestions": final_state.get("clarification_suggestions", []),
                    },
                }
                yield f"data: {json.dumps(clarification_event)}\n\n"
            elif final_state.get("report"):
                report_event = {
                    "type": "report",
                    "data": final_state.get("report"),
                    "citations": final_state.get("citations", []),
                }
                yield f"data: {json.dumps(report_event)}\n\n"
                research_completed = True
            elif final_state.get("error"):
                error_event = {
                    "type": "error",
                    "data": {
                        "code": "RESEARCH_FAILED",
                        "message": final_state.get("error"),
                        "recoverable": True,
                    },
                }
                yield f"data: {json.dumps(error_event)}\n\n"

            done_event = {
                "type": "done",
                "data": {
                    "thread_id": final_state.get("thread_id"),
                    "success": research_completed,
                },
            }
            yield f"data: {json.dumps(done_event)}\n\n"

            if research_completed:
                supabase = get_supabase()
                supabase.table("users").update(
                    {"researches_used": user["researches_used"] + 1}
                ).eq("id", user["id"]).execute()

        except Exception as e:
            logger.error(f"research stream error: {e}")
            error_event = {
                "type": "error",
                "data": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "recoverable": False,
                },
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sources")
async def list_sources() -> list[SourceInfo]:
    registry = _create_registry()
    sources = registry.list_sources()
    return [SourceInfo(**s) for s in sources]
