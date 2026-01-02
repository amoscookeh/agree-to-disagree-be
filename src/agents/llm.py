from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_llm(
    model: str = "x-ai/grok-4.1-fast", temperature: float = 0.7, **kwargs
) -> ChatOpenAI:
    """
    get configured llm instance for use in agent nodes

    defaults to grok-4.1-fast via openrouter
    """
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(settings.openrouter_api_key),  # type: ignore[arg-type]
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
        default_headers={
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_site_name,
        },
        **kwargs,
    )


# default instance for quick use
llm = get_llm()
