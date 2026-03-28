"""Rate limit middleware / FastAPI dependency.

Enforces per-key rate limits by consulting the token bucket and
adding X-RateLimit-* headers to every response. Also enforces
daily token limits.
"""

import math
import time

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException

from config import settings
from ratelimit.token_bucket import TokenBucket
from schemas.responses import ErrorDetail, ErrorResponse

logger = structlog.get_logger(__name__)


async def check_rate_limit(
    key_data: dict,
    redis_client: aioredis.Redis,
) -> dict[str, str]:
    """Check whether a request is allowed under the rate limit policy.

    Args:
        key_data: The authenticated API key metadata dict.
        redis_client: The async Redis client.

    Returns:
        A dict of X-RateLimit-* headers to attach to the response.

    Raises:
        HTTPException: 429 if the request exceeds the rate limit.
    """
    rate_limit = key_data.get("rate_limit")
    if rate_limit is None:
        capacity = settings.default_rate_limit_capacity
        refill_rate = settings.default_rate_limit_refill_rate
    else:
        capacity = rate_limit["capacity"]
        refill_rate = rate_limit["refill_rate"]

    key_id = str(key_data["id"])
    bucket = TokenBucket(redis_client)

    # Check token bucket
    allowed = await bucket.consume(key_id, capacity=capacity, refill_rate=refill_rate)
    remaining = await bucket.get_remaining(key_id, capacity=capacity, refill_rate=refill_rate)

    # Calculate reset time (seconds until a token refills)
    reset_seconds = math.ceil(1.0 / refill_rate) if remaining < 1 else 0

    headers = {
        "X-RateLimit-Limit": str(capacity),
        "X-RateLimit-Remaining": str(max(0, int(remaining))),
        "X-RateLimit-Reset": str(reset_seconds),
    }

    if not allowed:
        await logger.awarn("rate_limit_exceeded", key_id=key_id, capacity=capacity)
        raise HTTPException(
            status_code=429,
            detail=ErrorResponse(
                error=ErrorDetail(
                    type="rate_limit_error",
                    message="Rate limit exceeded. Please wait before retrying.",
                    code="rate_limited",
                )
            ).model_dump(),
            headers={"Retry-After": str(reset_seconds), **headers},
        )

    return headers


async def check_daily_limit(
    key_data: dict,
    redis_client: aioredis.Redis,
    tokens_used: int,
) -> None:
    """Check and update daily token usage.

    Args:
        key_data: The authenticated API key metadata dict.
        redis_client: The async Redis client.
        tokens_used: Number of tokens consumed by this request.

    Raises:
        HTTPException: 429 if the daily token limit is exceeded.
    """
    rate_limit = key_data.get("rate_limit")
    daily_limit = (
        rate_limit["daily_token_limit"]
        if rate_limit
        else settings.default_daily_token_limit
    )

    key_id = str(key_data["id"])
    bucket = TokenBucket(redis_client)
    new_total = await bucket.increment_daily_usage(key_id, tokens_used)

    if new_total > daily_limit:
        await logger.awarn(
            "daily_limit_exceeded",
            key_id=key_id,
            usage=new_total,
            limit=daily_limit,
        )
        raise HTTPException(
            status_code=429,
            detail=ErrorResponse(
                error=ErrorDetail(
                    type="rate_limit_error",
                    message=f"Daily token limit exceeded ({new_total}/{daily_limit}).",
                    code="daily_limit_exceeded",
                )
            ).model_dump(),
        )
