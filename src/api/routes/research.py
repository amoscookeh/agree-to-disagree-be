import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.graph import build_research_graph
from src.agents.nodes.research import _create_registry
from src.agents.state import AgentState
from src.api.deps import check_quota
from src.db.checkpointer import get_checkpointer
from src.db.client import get_supabase
from src.utils.logger import logger

router = APIRouter(prefix="/api", tags=["research"])


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    thread_id: str | None = None
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

    supabase = get_supabase()

    thread_id = request.thread_id or str(uuid4())
    query_id: str | None = None

    if request.thread_id:
        existing = (
            supabase.table("queries")
            .select("id")
            .eq("thread_id", thread_id)
            .eq("user_id", user["id"])
            .maybe_single()
            .execute()
        )
        if existing.data:
            query_id = existing.data["id"]
            supabase.table("queries").update({"query_text": query}).eq(
                "id", query_id
            ).execute()

    if not query_id:
        query_result = (
            supabase.table("queries")
            .insert(
                {
                    "user_id": user["id"],
                    "thread_id": thread_id,
                    "query_text": query,
                    "title": query[:50] + ("..." if len(query) > 50 else ""),
                    "is_completed": False,
                }
            )
            .execute()
        )
        query_id = query_result.data[0]["id"]

    logger.info(f"research request: {query[:50]}... (thread={thread_id})")

    # save initial user query message
    supabase.table("messages").insert(
        {
            "query_id": str(query_id),
            "role": "user",
            "content": {"type": "query", "query": query},
        }
    ).execute()

    initial_state: AgentState = {
        "query": query,
        "thread_id": thread_id,
    }

    if request.clarification_response:
        initial_state["clarification_response"] = request.clarification_response
        # save user's clarification response
        supabase.table("messages").insert(
            {
                "query_id": str(query_id),
                "role": "user",
                "content": {
                    "type": "clarification_response",
                    "response": request.clarification_response,
                },
            }
        ).execute()

    async def event_generator():
        research_completed = False
        checkpointer = get_checkpointer()
        graph = build_research_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        thread_event = {
            "type": "thread",
            "data": {"query_id": str(query_id), "thread_id": thread_id},
        }
        yield f"data: {json.dumps(thread_event)}\n\n"

        try:
            async for chunk in graph.astream(initial_state, config, stream_mode="custom"):
                # save progress events to database
                if chunk.get("type") == "progress":
                    supabase.table("messages").insert(
                        {
                            "query_id": str(query_id),
                            "role": "agent",
                            "content": chunk.get("data", {}),
                        }
                    ).execute()

                yield f"data: {json.dumps(chunk)}\n\n"

            state_snapshot = await graph.aget_state(config)
            final_state = state_snapshot.values if state_snapshot else {}

            if (
                final_state.get("needs_clarification")
                and not request.clarification_response
            ):
                clarification_data = {
                    "thread_id": thread_id,
                    "refined_query": final_state.get("refined_query", query),
                    "questions": final_state.get("clarification_questions", []),
                    "suggestions": final_state.get("clarification_suggestions", []),
                }
                clarification_event = {
                    "type": "clarification",
                    "data": clarification_data,
                }

                # save clarification request
                supabase.table("messages").insert(
                    {
                        "query_id": str(query_id),
                        "role": "clarification",
                        "content": clarification_data,
                    }
                ).execute()

                yield f"data: {json.dumps(clarification_event)}\n\n"

            elif final_state.get("report"):
                report = final_state.get("report", {})
                report_with_thread = {**report, "thread_id": thread_id}
                report_event = {
                    "type": "report",
                    "data": report_with_thread,
                    "citations": final_state.get("citations", []),
                }

                # save report message
                supabase.table("messages").insert(
                    {
                        "query_id": str(query_id),
                        "role": "report",
                        "content": report_with_thread,
                    }
                ).execute()

                yield f"data: {json.dumps(report_event)}\n\n"
                research_completed = True

                supabase.table("reports").insert(
                    {
                        "query_id": str(query_id),
                        "summary": report.get("summary", ""),
                        "claim_a": report.get("claim_a", {}),
                        "claim_b": report.get("claim_b", {}),
                        "agreements": report.get("agreements", []),
                        "disagreements": report.get("disagreements", []),
                        "uncertainties": report.get("uncertainties", []),
                        "citations": final_state.get("citations", []),
                    }
                ).execute()

                supabase.table("queries").update({"is_completed": True}).eq(
                    "id", str(query_id)
                ).execute()

                supabase.table("users").update(
                    {"researches_used": user["researches_used"] + 1}
                ).eq("id", user["id"]).execute()

            elif final_state.get("error"):
                error_data = {
                    "code": "RESEARCH_FAILED",
                    "message": final_state.get("error"),
                    "recoverable": True,
                    "thread_id": thread_id,
                }
                error_event = {
                    "type": "error",
                    "data": error_data,
                }

                # save error message
                supabase.table("messages").insert(
                    {
                        "query_id": str(query_id),
                        "role": "error",
                        "content": error_data,
                    }
                ).execute()

                yield f"data: {json.dumps(error_event)}\n\n"

            done_event = {
                "type": "done",
                "data": {
                    "thread_id": thread_id,
                    "query_id": str(query_id),
                    "success": research_completed,
                },
            }
            yield f"data: {json.dumps(done_event)}\n\n"

        except Exception as e:
            logger.error(f"research stream error: {e}")
            error_event = {
                "type": "error",
                "data": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "recoverable": False,
                    "thread_id": thread_id,
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
