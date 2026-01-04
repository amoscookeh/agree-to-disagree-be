"""
model configuration per node - easy to swap for experiments

change models here to test different llm capabilities per node

currently using x-ai/grok-4.1-fast as default (fast, cost-effective)
can upgrade specific nodes to grok-beta for better reasoning if needed
"""

MODELS = {
    "clarification": "x-ai/grok-4.1-fast",
    "classification": "x-ai/grok-4.1-fast",
    "supervisor": "x-ai/grok-4.1-fast",
    "sub_research": "x-ai/grok-4.1-fast",
    "sub_research_tools": "x-ai/grok-4.1-fast",
    "synthesis": "x-ai/grok-4.1-fast",
    "followup": "x-ai/grok-4.1-fast",
    "evaluators": "x-ai/grok-4.1-fast",
}


def get_model(node_name: str) -> str:
    """
    get the model for a specific node

    args:
        node_name: name of the node (e.g., "synthesis", "clarification")

    returns:
        model identifier for openrouter (e.g., "x-ai/grok-4.1-fast")
    """
    return MODELS.get(node_name, "x-ai/grok-4.1-fast")


__all__ = ["MODELS", "get_model"]
