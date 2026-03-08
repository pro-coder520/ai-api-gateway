"""Ollama (local model) provider implementation.

Ollama exposes an OpenAI-compatible API at /v1/chat/completions,
so minimal translation is required.
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


class OllamaProvider(BaseProvider):
    """Provider implementation for locally hosted Ollama models."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_api_base,
            headers={"Content-Type": "application/json"},
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Forward a chat completion request to Ollama."""
        payload = {
            "model": request.model,
            "messages": [m.model_dump(exclude_none=True) for m in request.messages],
            "stream": False,
        }
        if request.temperature is not None:
            payload["options"] = {"temperature": request.temperature}

        await logger.ainfo("ollama_request", model=request.model)
        response = await self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("model", request.model),
            choices=[
                Choice(
                    index=c.get("index", 0),
                    message=ChoiceMessage(
                        role=c["message"]["role"],
                        content=c["message"]["content"],
                    ),
                    finish_reason=c.get("finish_reason", "stop"),
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
        """Stream SSE chunks from Ollama's OpenAI-compatible endpoint."""
        payload = {
            "model": request.model,
            "messages": [m.model_dump(exclude_none=True) for m in request.messages],
            "stream": True,
        }
        if request.temperature is not None:
            payload["options"] = {"temperature": request.temperature}

        async with self._client.stream(
            "POST", "/v1/chat/completions", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line + "\n\n"
                    if line.strip() == "data: [DONE]":
                        break

    async def health_check(self) -> bool:
        """Check if Ollama is running and responsive."""
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def supported_models(self) -> list[str]:
        """Return a default list; dynamically fetched in Step 5."""
        return ["llama3", "mistral", "codellama"]
