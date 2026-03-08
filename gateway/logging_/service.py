"""Async request logger that writes to PostgreSQL without blocking responses.

Uses asyncio.create_task to fire-and-forget log entries so the response
is never delayed by database writes.
"""

import asyncio
import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from logging_.models import RequestLog

logger = structlog.get_logger(__name__)

# Cost per 1K tokens by model (USD). Used for cost_usd calculation.
COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
}

# Default cost for unknown models
_DEFAULT_COST = {"input": 0.001, "output": 0.002}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate the USD cost of a request based on token usage.

    Args:
        model: The model identifier.
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.

    Returns:
        Estimated cost in USD.
    """
    costs = COST_PER_1K_TOKENS.get(model, _DEFAULT_COST)
    return (input_tokens / 1000 * costs["input"]) + (
        output_tokens / 1000 * costs["output"]
    )


async def _write_log(session_factory, log_entry: RequestLog) -> None:  # type: ignore[no-untyped-def]
    """Write a single log entry to the database."""
    try:
        async with session_factory() as session:
            session.add(log_entry)
            await session.commit()
    except Exception as exc:
        await logger.aerror("log_write_failed", error=str(exc))


def log_request(
    session_factory,  # type: ignore[no-untyped-def]
    *,
    key_id: int | None,
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    status_code: int,
    cached: bool = False,
) -> None:
    """Fire-and-forget a request log entry.

    Creates an asyncio task to write the log asynchronously so the
    response is never blocked.

    Args:
        session_factory: Async session factory for database writes.
        key_id: The API key ID (nullable for unauthenticated requests).
        model: The model used.
        provider: The provider slug.
        input_tokens: Prompt token count.
        output_tokens: Completion token count.
        latency_ms: Request latency in milliseconds.
        status_code: HTTP status code returned.
        cached: Whether the response was served from cache.
    """
    total_tokens = input_tokens + output_tokens
    cost_usd = calculate_cost(model, input_tokens, output_tokens)

    entry = RequestLog(
        key_id=key_id,
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        status_code=status_code,
        cost_usd=cost_usd,
        cached=cached,
    )

    asyncio.create_task(_write_log(session_factory, entry))
