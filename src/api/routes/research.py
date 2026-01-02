import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.graph import research_graph
from src.agents.nodes.research import _create_registry
from src.agents.state import AgentState
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
async def research(request: ResearchRequest):
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
                    "type": "clarification_needed",
                    "questions": final_state.get("clarification_questions", []),
                    "refined_query": final_state.get("refined_query", query),
                }
                yield f"data: {json.dumps(clarification_event)}\n\n"
            elif final_state.get("report"):
                report_event = {
                    "type": "report",
                    "data": final_state.get("report"),
                    "citations": final_state.get("citations", []),
                }
                yield f"data: {json.dumps(report_event)}\n\n"
            elif final_state.get("error"):
                error_event = {
                    "type": "error",
                    "message": final_state.get("error"),
                }
                yield f"data: {json.dumps(error_event)}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"research stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

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
