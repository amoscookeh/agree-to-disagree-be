from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from langgraph.types import StateSnapshot

from src.api.deps import get_current_user
from src.db.checkpointer import get_checkpointer
from src.db.client import get_supabase
from src.utils.logger import logger

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.post("")
async def create_thread(user: dict = Depends(get_current_user)):
    """create a new conversation thread"""
    thread_id = str(uuid4())

    supabase = get_supabase()
    result = (
        supabase.table("queries")
        .insert(
            {
                "user_id": user["id"],
                "thread_id": thread_id,
                "query_text": "",
                "title": "New Research",
                "is_completed": False,
            }
        )
        .execute()
    )

    data = cast(list[dict[str, Any]], result.data)
    return {
        "thread_id": thread_id,
        "query_id": data[0]["id"],
        "created_at": data[0]["created_at"],
    }


@router.get("")
async def list_threads(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
):
    """list user's conversation threads"""
    supabase = get_supabase()

    response = (
        supabase.table("queries")
        .select("id, thread_id, query_text, title, is_completed, created_at")
        .eq("user_id", user["id"])
        .not_.is_("thread_id", "null")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    return {"threads": response.data, "offset": offset, "limit": limit}


@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    """get thread details with report if completed"""
    supabase = get_supabase()

    try:
        query_response = (
            supabase.table("queries")
            .select("*")
            .eq("thread_id", thread_id)
            .eq("user_id", user["id"])
            .execute()
        )

        query_data = cast(list[dict[str, Any]], query_response.data)
        if not query_data or len(query_data) == 0:
            raise HTTPException(status_code=404, detail="Thread not found")

        query = query_data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"failed to fetch query for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch thread")

    report = None
    if query["is_completed"]:
        try:
            report_response = (
                supabase.table("reports")
                .select("*")
                .eq("query_id", query["id"])
                .execute()
            )
            report_data = cast(list[dict[str, Any]], report_response.data)
            if report_data and len(report_data) > 0:
                report = report_data[0]
        except Exception as e:
            logger.warning(f"failed to fetch report for query {query['id']}: {e}")

    # get all messages for this conversation
    messages_response = (
        supabase.table("messages")
        .select("*")
        .eq("query_id", query["id"])
        .order("created_at")
        .execute()
    )
    messages = (
        cast(list[dict[str, Any]], messages_response.data)
        if messages_response.data
        else []
    )

    state = None
    history = []
    try:
        checkpointer = get_checkpointer()
        if checkpointer:
            from src.agents.graph import build_research_graph

            graph = build_research_graph(checkpointer)
            config: Any = {"configurable": {"thread_id": thread_id}}

            # get current state
            state_snapshot: StateSnapshot = await graph.aget_state(config)
            if state_snapshot and state_snapshot.values:
                state = state_snapshot.values

            # get full history of checkpoints (includes all progress updates, tool calls, etc)
            snapshot: StateSnapshot
            async for snapshot in graph.aget_state_history(config):
                history.append(
                    {
                        "values": snapshot.values,
                        "next": snapshot.next,
                        "metadata": snapshot.metadata,
                        "created_at": snapshot.created_at
                        if hasattr(snapshot, "created_at")
                        else None,
                    }
                )
    except Exception as e:
        logger.warning(f"failed to get checkpointer state for thread {thread_id}: {e}")

    return {
        "thread_id": thread_id,
        "query": query,
        "report": report,
        "messages": messages,
        "state": state,
        "history": history,
    }


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    """delete a thread and its associated data"""
    supabase = get_supabase()

    query = (
        supabase.table("queries")
        .select("id")
        .eq("thread_id", thread_id)
        .eq("user_id", user["id"])
        .maybe_single()
        .execute()
    )

    if not query or not query.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    supabase.table("queries").delete().eq("thread_id", thread_id).execute()

    return {"deleted": True}
