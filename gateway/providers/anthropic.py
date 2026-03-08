"""Anthropic provider implementation.

Translates OpenAI-compatible requests to and from the Anthropic Messages API.
"""

import json
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


class AnthropicProvider(BaseProvider):
    """Provider implementation for the Anthropic Messages API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.anthropic_api_base,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    def _build_anthropic_payload(self, request: ChatRequest) -> dict:
        """Convert an OpenAI-format request into an Anthropic Messages API payload."""
        system_message: str | None = None
        messages: list[dict[str, str]] = []
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        payload: dict = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }
        if system_message:
            payload["system"] = system_message
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop is not None:
            payload["stop_sequences"] = (
                request.stop if isinstance(request.stop, list) else [request.stop]
            )
        return payload

    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Forward a chat completion request to Anthropic and return in OpenAI format."""
        payload = self._build_anthropic_payload(request)
        payload["stream"] = False

        await logger.ainfo("anthropic_request", model=request.model)
        response = await self._client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        content_parts = data.get("content", [])
        text = "".join(
            p.get("text", "") for p in content_parts if p.get("type") == "text"
        )
        usage_data = data.get("usage", {})

        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("model", request.model),
            choices=[
                Choice(
                    index=0,
                    message=ChoiceMessage(role="assistant", content=text),
                    finish_reason=data.get("stop_reason", "stop"),
                )
            ],
            usage=Usage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=(
                    usage_data.get("input_tokens", 0)
                    + usage_data.get("output_tokens", 0)
                ),
            ),
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream Anthropic SSE events, re-formatting as OpenAI-compatible chunks."""
        payload = self._build_anthropic_payload(request)
        payload["stream"] = True

        async with self._client.stream(
            "POST", "/v1/messages", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                if raw.strip() == "[DONE]":
                    yield "data: [DONE]\n\n"
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type", "")
                if event_type == "content_block_delta":
                    delta_text = event.get("delta", {}).get("text", "")
                    chunk = {
                        "id": event.get("message", {}).get("id", ""),
                        "object": "chat.completion.chunk",
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta_text},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif event_type == "message_stop":
                    yield "data: [DONE]\n\n"
                    break

    async def health_check(self) -> bool:
        """Verify connectivity to the Anthropic API."""
        try:
            response = await self._client.post(
                "/v1/messages",
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
            )
            return response.status_code in (200, 400)
        except httpx.HTTPError:
            return False

    def supported_models(self) -> list[str]:
        """Return models known to be available from Anthropic."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
        ]
