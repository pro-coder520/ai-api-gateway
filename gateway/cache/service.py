"""Request hashing and Redis-backed response caching.

Only caches when temperature == 0 (deterministic). Never caches streaming
requests. Cache entries are stored as JSON with a configurable TTL.
"""

import hashlib
import json

import redis.asyncio as aioredis
import structlog

from config import settings

logger = structlog.get_logger(__name__)


def generate_cache_key(model: str, messages: list, **params: object) -> str:
    """Generate a deterministic cache key from request parameters.

    Args:
        model: The model identifier.
        messages: The list of chat messages.
        **params: Additional parameters (temperature, max_tokens, top_p).

    Returns:
        A prefixed SHA-256 hex digest cache key.
    """
    payload = json.dumps(
        {"model": model, "messages": messages, **params},
        sort_keys=True,
        default=str,
    )
    return f"cache:{hashlib.sha256(payload.encode()).hexdigest()}"


class CacheService:
    """Redis-backed response cache for deterministic LLM responses."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self.redis = redis_client
        self.ttl = settings.cache_default_ttl
        self.enabled = settings.cache_enabled

    async def get(self, cache_key: str) -> dict | None:
        """Retrieve a cached response by key.

        Returns:
            The cached response dict, or None if not found.
        """
        if not self.enabled:
            return None
        raw = await self.redis.get(cache_key)
        if raw is None:
            return None
        await logger.ainfo("cache_hit", key=cache_key[:20])
        return json.loads(raw)

    async def set(
        self, cache_key: str, response_data: dict, ttl: int | None = None
    ) -> None:
        """Store a response in the cache.

        Args:
            cache_key: The cache key.
            response_data: The response to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds. Defaults to configured TTL.
        """
        if not self.enabled:
            return
        ttl = ttl or self.ttl
        await self.redis.setex(cache_key, ttl, json.dumps(response_data, default=str))
        await logger.ainfo("cache_set", key=cache_key[:20], ttl=ttl)

    async def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern.

        Args:
            pattern: Redis glob pattern (e.g. 'cache:*').

        Returns:
            Number of keys deleted.
        """
        keys: list[str] = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            deleted: int = await self.redis.delete(*keys)  # type: ignore[assignment]
            await logger.ainfo("cache_invalidated", pattern=pattern, count=deleted)
            return deleted
        return 0

    @staticmethod
    def should_cache(temperature: float | None, stream: bool) -> bool:
        """Determine whether a request's response should be cached.

        Only caches when temperature == 0 and the request is not streaming.
        """
        return temperature == 0 and not stream
