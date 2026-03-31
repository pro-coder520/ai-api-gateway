"""OpenAI provider implementation.

Proxies requests to the OpenAI API using httpx with async connection pooling.
Full implementation is completed in Step 4.
"""

from typing import AsyncIterator

import httpx
import structlog

from config import settings
from providers.base import BaseProvider
from schemas.requests import ChatRequest
from schemas.responses import (
    ChatResponse,
    Choice,
    ChoiceMessage,
    Usage,
)

logger = structlog.get_logger(__name__)


class OpenAIProvider(BaseProvider):
    """Provider implementation for the OpenAI API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.openai_api_base,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Forward a chat completion request to OpenAI and return the response."""
        payload = {
            "model": request.model,
            "messages": [m.model_dump(exclude_none=True) for m in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "n": request.n,
            "stream": False,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
        }
        if request.stop is not None:
            payload["stop"] = request.stop

        await logger.ainfo("openai_request", model=request.model)
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("model", request.model),
            choices=[
                Choice(
                    index=c["index"],
                    message=ChoiceMessage(
                        role=c["message"]["role"],
                        content=c["message"]["content"],
                    ),
                    finish_reason=c.get("finish_reason"),
                )
                for c in data.get("choices", [])
            ],
            usage=Usage(
                prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
                total_tokens=data.get("usage", {}).get("total_tokens", 0),
            ),
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream SSE chunks from the OpenAI API."""
        payload = {
            "model": request.model,
            "messages": [m.model_dump(exclude_none=True) for m in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.stop is not None:
            payload["stop"] = request.stop

        async with self._client.stream(
            "POST", "/chat/completions", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line + "\n\n"
                    if line.strip() == "data: [DONE]":
                        break

    async def health_check(self) -> bool:
        """Ping the OpenAI models endpoint to verify connectivity."""
        try:
            response = await self._client.get("/models")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def supported_models(self) -> list[str]:
        """Return models known to be available from OpenAI."""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-3.5-turbo",
        ]

    async def close(self) -> None:
        """Close the httpx client."""
        await self._client.aclose()
