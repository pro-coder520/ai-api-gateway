"""Redis-backed token bucket rate limiter using an atomic Lua script.

The Lua script runs entirely within Redis, eliminating race conditions
between concurrent requests. Each API key has its own bucket with
configurable capacity and refill rate.
"""

import time

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)

# Atomic Lua script for token bucket rate limiting
TOKEN_BUCKET_SCRIPT = """
local bucket = redis.call('HMGET', KEYS[1], 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or tonumber(ARGV[1])
local last = tonumber(bucket[2]) or tonumber(ARGV[3])
local elapsed = tonumber(ARGV[3]) - last
local refill = math.min(tonumber(ARGV[1]), tokens + elapsed * tonumber(ARGV[2]))
if refill >= 1 then
    redis.call('HMSET', KEYS[1], 'tokens', refill - 1, 'last_refill', ARGV[3])
    redis.call('EXPIRE', KEYS[1], 86400)
    return 1
else
    redis.call('HMSET', KEYS[1], 'tokens', refill, 'last_refill', ARGV[3])
    redis.call('EXPIRE', KEYS[1], 86400)
    return 0
end
"""

# Lua script to check remaining tokens without consuming
CHECK_TOKENS_SCRIPT = """
local bucket = redis.call('HMGET', KEYS[1], 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or tonumber(ARGV[1])
local last = tonumber(bucket[2]) or tonumber(ARGV[3])
local elapsed = tonumber(ARGV[3]) - last
local refill = math.min(tonumber(ARGV[1]), tokens + elapsed * tonumber(ARGV[2]))
return tostring(refill)
"""


class TokenBucket:
    """Redis-backed token bucket rate limiter.

    Attributes:
        redis: The async Redis client.
        _consume_sha: SHA hash of the registered Lua consume script.
        _check_sha: SHA hash of the registered Lua check script.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self.redis = redis_client
        self._consume_sha: str | None = None
        self._check_sha: str | None = None

    async def _ensure_scripts(self) -> None:
        """Register Lua scripts if not already loaded."""
        if self._consume_sha is None:
            self._consume_sha = await self.redis.script_load(TOKEN_BUCKET_SCRIPT)  # type: ignore[assignment]
        if self._check_sha is None:
            self._check_sha = await self.redis.script_load(CHECK_TOKENS_SCRIPT)  # type: ignore[assignment]

    async def consume(
        self,
        key_id: str,
        capacity: int,
        refill_rate: float,
    ) -> bool:
        """Attempt to consume one token from the bucket.

        Args:
            key_id: Unique identifier for the rate limit bucket (e.g. API key ID).
            capacity: Maximum number of tokens (burst size).
            refill_rate: Tokens added per second.

        Returns:
            True if the request is allowed, False if rate limited.
        """
        await self._ensure_scripts()
        bucket_key = f"ratelimit:{key_id}"
        now = time.time()
        result = await self.redis.evalsha(
            self._consume_sha,  # type: ignore[arg-type]
            1,
            bucket_key,
            str(capacity),
            str(refill_rate),
            str(now),
        )
        allowed = int(result) == 1
        if not allowed:
            await logger.awarn("rate_limited", key_id=key_id)
        return allowed

    async def get_remaining(
        self,
        key_id: str,
        capacity: int,
        refill_rate: float,
    ) -> float:
        """Return the current number of tokens without consuming any.

        Args:
            key_id: Unique identifier for the rate limit bucket.
            capacity: Maximum bucket capacity.
            refill_rate: Tokens added per second.

        Returns:
            Number of tokens currently available (may be fractional).
        """
        await self._ensure_scripts()
        bucket_key = f"ratelimit:{key_id}"
        now = time.time()
        result = await self.redis.evalsha(
            self._check_sha,  # type: ignore[arg-type]
            1,
            bucket_key,
            str(capacity),
            str(refill_rate),
            str(now),
        )
        return float(result)

    async def increment_daily_usage(self, key_id: str, tokens: int) -> int:
        """Increment the daily token counter and return the new total.

        Counters are stored with a key that includes the current UTC date
        and automatically expire after 48 hours.
        """
        import datetime

        date_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
        daily_key = f"daily_tokens:{key_id}:{date_str}"
        new_total: int = await self.redis.incrby(daily_key, tokens)  # type: ignore[assignment]
        await self.redis.expire(daily_key, 172_800)  # 48 hours
        return new_total

    async def get_daily_usage(self, key_id: str) -> int:
        """Return the current daily token usage for a key."""
        import datetime

        date_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
        daily_key = f"daily_tokens:{key_id}:{date_str}"
        result = await self.redis.get(daily_key)
        return int(result) if result else 0
