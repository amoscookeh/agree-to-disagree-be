from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from prompts.models import ModelConfig, Models
from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_llm(
    model: str | ModelConfig | None = None,
    temperature: float | None = None,
    **kwargs,
) -> ChatOpenAI:
    """
    get configured llm instance for use in agent nodes

    args:
        model: model id string, ModelConfig, or None for default
        temperature: override temperature (uses ModelConfig.temperature if not provided)
        **kwargs: additional kwargs passed to ChatOpenAI
    """
    if model is None:
        model_config = Models.DEFAULT
    elif isinstance(model, ModelConfig):
        model_config = model
    else:
        model_config = ModelConfig(model_id=model, temperature=temperature or 0.7)

    actual_temp = temperature if temperature is not None else model_config.temperature

    return ChatOpenAI(
        model=model_config.model_id,
        api_key=SecretStr(settings.openrouter_api_key),  # type: ignore[arg-type]
        base_url="https://openrouter.ai/api/v1",
        temperature=actual_temp,
        default_headers={
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_site_name,
        },
        **kwargs,
    )


# default instance for quick use
llm = get_llm()
