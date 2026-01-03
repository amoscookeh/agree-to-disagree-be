"""centralized model configuration for all agent nodes"""

from dataclasses import dataclass


@dataclass
class ModelConfig:
    model_id: str
    temperature: float = 0.7
    description: str = ""


class Models:
    FAST = ModelConfig(
        model_id="x-ai/grok-4.1-fast",
        temperature=0.7,
        description="fast model for simple classifications",
    )

    DEFAULT = ModelConfig(
        model_id="x-ai/grok-4.1-fast",
        temperature=0.7,
        description="balanced model for general tasks",
    )

    QUALITY = ModelConfig(
        model_id="anthropic/claude-sonnet-4",
        temperature=0.7,
        description="high quality model for synthesis",
    )

    STRUCTURED = ModelConfig(
        model_id="x-ai/grok-4.1-fast",
        temperature=0.3,
        description="low temperature for structured output",
    )


CLARIFICATION_MODEL = Models.FAST
CLASSIFICATION_MODEL = Models.FAST
SUPERVISOR_MODEL = Models.DEFAULT
SUB_RESEARCH_MODEL = Models.DEFAULT
SUB_RESEARCH_TOOL_MODEL = ModelConfig(
    model_id="x-ai/grok-4.1-fast",
    temperature=0.5,
)
SYNTHESIS_MODEL = Models.QUALITY
FOLLOWUP_MODEL = Models.DEFAULT
EVALUATOR_MODEL = ModelConfig(
    model_id="x-ai/grok-4.1-fast",
    temperature=0.0,
)


__all__ = [
    "ModelConfig",
    "Models",
    "CLARIFICATION_MODEL",
    "CLASSIFICATION_MODEL",
    "SUPERVISOR_MODEL",
    "SUB_RESEARCH_MODEL",
    "SUB_RESEARCH_TOOL_MODEL",
    "SYNTHESIS_MODEL",
    "FOLLOWUP_MODEL",
    "EVALUATOR_MODEL",
]
