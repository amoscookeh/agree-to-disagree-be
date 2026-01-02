import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OpenRouterClient:
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = settings.openrouter_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_site_name,
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = "openai/gpt-4o",
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if stream:
            return self._stream_response(payload)
        else:
            async with httpx.AsyncClient(timeout=60.0) as client:
                return await self._single_response(client, payload)

    async def _single_response(
        self, client: httpx.AsyncClient, payload: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            response = await client.post(
                self.base_url, headers=self.headers, json=payload
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPError as e:
            logger.error(f"openrouter api error: {e}")
            raise

    async def _stream_response(
        self, payload: dict[str, Any]
    ) -> AsyncGenerator[dict[str, Any], None]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST", self.base_url, headers=self.headers, json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                yield json.loads(data)
                            except json.JSONDecodeError:
                                continue
        except httpx.HTTPError as e:
            logger.error(f"openrouter streaming error: {e}")
            raise


client = OpenRouterClient()
