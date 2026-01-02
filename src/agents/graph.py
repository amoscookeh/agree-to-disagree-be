from langgraph.graph import END, StateGraph

from src.agents.nodes import clarification_node, research_node
from src.agents.nodes.synthesis import synthesis_node
from src.agents.state import AgentState
from src.utils.logger import logger


def _should_continue_after_clarification(state: AgentState) -> str:
    needs_clarification = state.get("needs_clarification", False)
    clarification_response = state.get("clarification_response")

    if needs_clarification and not clarification_response:
        logger.info("query needs clarification, waiting for user response")
        return "wait_for_clarification"

    logger.info("query is clear, proceeding to research")
    return "research"


def build_research_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("clarification", clarification_node)
    builder.add_node("research", research_node)
    builder.add_node("synthesis", synthesis_node)

    builder.set_entry_point("clarification")

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

    return builder.compile()


research_graph = build_research_graph()

