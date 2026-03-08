"""Exponential backoff with jitter for retrying failed upstream requests."""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: object,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: object,
) -> T:
    """Execute an async function with exponential backoff on failure.

    Args:
        func: The async callable to execute.
        *args: Positional arguments for *func*.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum delay between retries.
        jitter: Whether to add random jitter to the delay.
        retryable_exceptions: Tuple of exception types that should trigger a retry.
        **kwargs: Keyword arguments for *func*.

    Returns:
        The result of *func* on success.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exception = exc
            if attempt == max_retries:
                await logger.aerror(
                    "retry_exhausted",
                    func=func.__name__,
                    attempts=max_retries + 1,
                    error=str(exc),
                )
                raise

            delay = min(base_delay * (2**attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())

            await logger.awarn(
                "retry_attempt",
                func=func.__name__,
                attempt=attempt + 1,
                delay=round(delay, 2),
                error=str(exc),
            )
            await asyncio.sleep(delay)

    # Should never reach here, but satisfy type checker
    raise last_exception  # type: ignore[misc]
