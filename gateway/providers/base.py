"""Abstract base class for all LLM providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from schemas.requests import ChatRequest
from schemas.responses import ChatResponse


class BaseProvider(ABC):
    """Interface every LLM provider must implement.

    Providers are stateless request proxies. Connection pools and
    configuration are injected at construction time.
    """

    @abstractmethod
    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Send a non-streaming chat completion request and return the full response."""
        ...

    @abstractmethod
    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Send a streaming chat completion request and yield SSE-formatted chunks."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and responsive."""
        ...

    @abstractmethod
    def supported_models(self) -> list[str]:
        """Return a list of model identifiers this provider supports."""
        ...

    async def close(self) -> None:
        """Close any underlying HTTP clients. Override in subclasses."""
