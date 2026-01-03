from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.nodes import clarification_node, research_node
from src.agents.nodes.classification import classification_node
from src.agents.nodes.followup import followup_node
from src.agents.nodes.synthesis import synthesis_node
from src.agents.state import AgentState
from src.utils.logger import logger


def _route_after_classification(state: AgentState) -> str:
    """route based on classification result"""
    message_type = state.get("message_type", "research_prompt")

    if message_type == "follow_up_question":
        logger.info("routing to followup agent")
        return "followup"

    logger.info("routing to research (clarification first)")
    return "clarification"


def _should_continue_after_clarification(state: AgentState) -> str:
    """check if we need user clarification before research"""
    needs_clarification = state.get("needs_clarification", False)
    clarification_response = state.get("clarification_response")

    if needs_clarification and not clarification_response:
        logger.info("query needs clarification, waiting for user response")
        return "wait_for_clarification"

    logger.info("query is clear, proceeding to research")
    return "research"


def build_research_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("classification", classification_node)
    builder.add_node("clarification", clarification_node)
    builder.add_node("research", research_node)
    builder.add_node("synthesis", synthesis_node)
    builder.add_node("followup", followup_node)

    builder.set_entry_point("classification")

    builder.add_conditional_edges(
        "classification",
        _route_after_classification,
        {
            "clarification": "clarification",
            "followup": "followup",
        },
    )

    builder.add_conditional_edges(
        "clarification",
        _should_continue_after_clarification,
        {
            "wait_for_clarification": END,
            "research": "research",
        },
    )

    builder.add_edge("research", "synthesis")
    builder.add_edge("synthesis", END)

    builder.add_edge("followup", END)

    return builder.compile(checkpointer=checkpointer)


research_graph = build_research_graph()
