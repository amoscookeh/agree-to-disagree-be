import json
from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.graph import build_research_graph
from src.agents.state import AgentState
from src.api.deps import check_quota
from src.data_sources import get_default_registry
from src.db.checkpointer import get_fresh_checkpointer
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


def _load_messages_for_state(messages: list[dict]) -> list[dict]:
    """convert db messages to state messages format for classification"""
    state_messages = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", {})

        if role == "user":
            state_messages.append({"role": "user", "content": content})
        elif role == "followup":
            state_messages.append({"role": "assistant", "content": content})
        elif role == "report":
            state_messages.append({"role": "assistant", "content": content})
        elif role == "clarification":
            state_messages.append({"role": "system", "content": content})

    return state_messages


@router.post("/research")
async def research(request: ResearchRequest, user: dict = Depends(check_quota)):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    supabase = get_supabase()

    is_new_thread = request.thread_id is None
    thread_id = request.thread_id or str(uuid4())
    query_id: str | None = None
    existing_messages: list[dict] = []
    existing_report: dict | None = None

    if not is_new_thread:
        existing = (
            supabase.table("queries")
            .select("id, is_completed")
            .eq("thread_id", thread_id)
            .eq("user_id", user["id"])
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            existing_data = cast(dict[str, Any], existing.data)
            query_id = str(existing_data["id"])

            msg_response = (
                supabase.table("messages")
                .select("*")
                .eq("query_id", query_id)
                .order("created_at")
                .execute()
            )
            existing_messages = (
                cast(list[dict[str, Any]], msg_response.data)
                if msg_response.data
                else []
            )

            if existing_data.get("is_completed"):
                report_response = (
                    supabase.table("reports")
                    .select("*")
                    .eq("query_id", query_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if report_response.data:
                    existing_report = cast(dict[str, Any], report_response.data[0])

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
        query_result_data = cast(list[dict[str, Any]], query_result.data)
        query_id = str(query_result_data[0]["id"])

    logger.info(
        f"research request: {query[:50]}... (thread={thread_id}, "
        f"new_thread={is_new_thread}, existing_msgs={len(existing_messages)})"
    )

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

    if existing_messages:
        initial_state["messages"] = _load_messages_for_state(existing_messages)

    if existing_report:
        initial_state["report"] = {
            "summary": existing_report.get("summary", ""),
            "claim_a": existing_report.get("claim_a", {}),
            "claim_b": existing_report.get("claim_b", {}),
            "agreements": existing_report.get("agreements", []),
            "disagreements": existing_report.get("disagreements", []),
            "uncertainties": existing_report.get("uncertainties", []),
        }
        initial_state["citations"] = existing_report.get("citations", [])

    if request.clarification_response:
        initial_state["clarification_response"] = request.clarification_response
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

    async def event_generator() -> Any:
        research_completed = False

        thread_event = {
            "type": "thread",
            "data": {"query_id": str(query_id), "thread_id": thread_id},
        }
        yield f"data: {json.dumps(thread_event)}\n\n"

        try:
            async with get_fresh_checkpointer() as checkpointer:
                graph = build_research_graph(checkpointer)
                config: Any = {"configurable": {"thread_id": thread_id}}

                async for chunk in graph.astream(
                    initial_state, config, stream_mode="custom"
                ):
                    chunk_type = chunk.get("type", "")

                    if chunk_type == "progress":
                        supabase.table("messages").insert(
                            {
                                "query_id": str(query_id),
                                "role": "agent",
                                "content": chunk,
                            }
                        ).execute()

                    elif chunk_type == "sub_queries":
                        supabase.table("messages").insert(
                            {
                                "query_id": str(query_id),
                                "role": "sub_queries",
                                "content": chunk.get("data", {}),
                            }
                        ).execute()

                    elif chunk_type == "draft":
                        supabase.table("messages").insert(
                            {
                                "query_id": str(query_id),
                                "role": "draft",
                                "content": chunk.get("data", {}),
                            }
                        ).execute()

                    elif chunk_type == "supervisor_decision":
                        supabase.table("messages").insert(
                            {
                                "query_id": str(query_id),
                                "role": "supervisor_decision",
                                "content": chunk.get("data", {}),
                            }
                        ).execute()

                    yield f"data: {json.dumps(chunk)}\n\n"

                state_snapshot = await graph.aget_state(config)
                final_state = state_snapshot.values if state_snapshot else {}

                if final_state.get("followup_answer"):
                    answer = final_state["followup_answer"]
                    citations = final_state.get("followup_citations", [])

                    followup_data = {
                        "answer": answer,
                        "citations": citations,
                        "thread_id": thread_id,
                    }
                    followup_event = {
                        "type": "followup_answer",
                        "data": followup_data,
                    }

                    supabase.table("messages").insert(
                        {
                            "query_id": str(query_id),
                            "role": "followup",
                            "content": followup_data,
                        }
                    ).execute()

                    yield f"data: {json.dumps(followup_event)}\n\n"
                    research_completed = True

                elif (
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
    registry = get_default_registry()
    sources = registry.list_sources()
    return [SourceInfo(**s) for s in sources]
