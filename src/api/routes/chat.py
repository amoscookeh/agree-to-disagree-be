from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import require_auth
from src.db.checkpointer import get_checkpointer
from src.db.client import get_supabase
from src.utils.logger import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/{query_id}")
async def get_chat(query_id: str, user: dict = Depends(require_auth)):
    """get full conversation thread by query_id"""
    supabase = get_supabase()

    query_result = (
        supabase.table("queries")
        .select("*")
        .eq("id", query_id)
        .eq("user_id", user["id"])
        .maybe_single()
        .execute()
    )

    if not query_result.data:
        raise HTTPException(status_code=404, detail="Chat not found")

    query = query_result.data
    thread_id = query.get("thread_id")

    report = None
    if query.get("is_completed"):
        report_result = (
            supabase.table("reports")
            .select("*")
            .eq("query_id", query_id)
            .maybe_single()
            .execute()
        )
        if report_result.data:
            report = report_result.data

    # get all messages for this conversation
    messages_result = (
        supabase.table("messages")
        .select("*")
        .eq("query_id", query_id)
        .order("created_at")
        .execute()
    )
    messages = messages_result.data if messages_result.data else []

    state = None
    history = []

    if thread_id:
        try:
            checkpointer = get_checkpointer()
            if checkpointer:
                from src.agents.graph import build_research_graph

                graph = build_research_graph(checkpointer)
                config = {"configurable": {"thread_id": thread_id}}

                state_snapshot = await graph.aget_state(config)
                if state_snapshot and state_snapshot.values:
                    state = state_snapshot.values

                async for checkpoint in graph.aget_state_history(config):
                    history.append(
                        {
                            "values": checkpoint.values,
                            "next": checkpoint.next,
                            "metadata": checkpoint.metadata,
                            "created_at": getattr(checkpoint, "created_at", None),
                        }
                    )
        except Exception as e:
            logger.warning(f"failed to get checkpointer state for query {query_id}: {e}")

    return {
        "query_id": query_id,
        "thread_id": thread_id,
        "query": query,
        "report": report,
        "messages": messages,
        "state": state,
        "history": history,
    }

