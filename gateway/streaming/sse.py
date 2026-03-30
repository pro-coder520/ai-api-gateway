"""SSE pass-through and incremental token counting.

Handles streaming responses from upstream providers, forwarding chunks
to the client while counting tokens as they arrive.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from starlette.responses import StreamingResponse

logger = structlog.get_logger(__name__)


class SSEHandler:
    """Manages SSE streaming from an upstream provider to the client.

    Tracks token counts incrementally and handles client disconnects
    by cancelling the upstream request.
    """

    def __init__(self) -> None:
        self.total_tokens: int = 0
        self._cancelled: bool = False
        self._error: Exception | None = None
        self._completed: bool = False

    async def stream_response(
        self,
        upstream_stream: AsyncIterator[str],
        model: str,
        on_complete: Any = None,
        on_error: Any = None,
    ) -> StreamingResponse:
        """Wrap an upstream SSE stream for the client.

        Args:
            upstream_stream: The async iterator of SSE chunks from the provider.
            model: The model name for logging.
            on_complete: Optional async callback(total_tokens) called on successful completion.
            on_error: Optional async callback(exception) called on stream error.

        Returns:
            A Starlette StreamingResponse with media_type text/event-stream.
        """

        async def _generate() -> AsyncIterator[str]:
            try:
                async for chunk in upstream_stream:
                    if self._cancelled:
                        break
                    self._count_tokens(chunk)
                    yield chunk
                self._completed = True
            except asyncio.CancelledError:
                await logger.ainfo("stream_cancelled", model=model)
            except Exception as exc:
                self._error = exc
                await logger.aerror("stream_error_during_iteration", model=model, error=str(exc))
            finally:
                await logger.ainfo(
                    "stream_complete",
                    model=model,
                    total_tokens=self.total_tokens,
                )
                if self._error and on_error:
                    await on_error(self._error)
                elif self._completed and on_complete:
                    await on_complete(self.total_tokens)

        return StreamingResponse(
            _generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    def _count_tokens(self, chunk: str) -> None:
        """Estimate token count from a streaming SSE chunk.

        Approximation: count whitespace-separated words in delta content.
        A more accurate count is logged post-stream using tiktoken (Step 10).
        """
        if not chunk.startswith("data: ") or chunk.strip() == "data: [DONE]":
            return
        try:
            data = json.loads(chunk[6:])
            for choice in data.get("choices", []):
                content = choice.get("delta", {}).get("content", "")
                if content:
                    # Rough token estimate: ~0.75 tokens per word
                    self.total_tokens += max(1, len(content.split()))
        except (json.JSONDecodeError, KeyError):
            pass

    def cancel(self) -> None:
        """Signal that the client has disconnected."""
        self._cancelled = True
