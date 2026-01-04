"""model configuration per node"""

MODELS = {
    "clarification": "google/gemini-2.5-flash",
    "classification": "google/gemini-2.5-flash",
    "supervisor": "google/gemini-2.5-pro",
    "sub_research": "anthropic/claude-sonnet-4.5",
    "sub_research_tools": "openai/gpt-5-mini",
    "synthesis": "google/gemini-2.5-pro",
    "followup": "google/gemini-2.5-pro",
    "evaluators": "openai/gpt-4o",
}


def get_model(node_name: str) -> str:
    return MODELS.get(node_name, "openai/gpt-5-mini")


__all__ = ["MODELS", "get_model"]
