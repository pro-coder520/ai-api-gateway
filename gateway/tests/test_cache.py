"""Tests for response caching."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from cache.service import CacheService, generate_cache_key


class TestCacheKeyGeneration:
    """Test suite for cache key determinism."""

    def test_same_input_same_key(self) -> None:
        """Identical inputs produce identical cache keys."""
        messages = [{"role": "user", "content": "Hello"}]
        key1 = generate_cache_key("gpt-4", messages, temperature=0, max_tokens=100)
        key2 = generate_cache_key("gpt-4", messages, temperature=0, max_tokens=100)
        assert key1 == key2

    def test_different_model_different_key(self) -> None:
        """Different models produce different cache keys."""
        messages = [{"role": "user", "content": "Hello"}]
        key1 = generate_cache_key("gpt-4", messages)
        key2 = generate_cache_key("gpt-3.5-turbo", messages)
        assert key1 != key2

    def test_key_has_prefix(self) -> None:
        """Cache keys are prefixed with 'cache:'."""
        key = generate_cache_key("gpt-4", [])
        assert key.startswith("cache:")

    def test_key_length(self) -> None:
        """Cache key is 'cache:' + 64-char SHA-256 hex digest."""
        key = generate_cache_key("gpt-4", [])
        assert len(key) == 6 + 64  # "cache:" + hex digest


class TestCacheService:
    """Test suite for the Redis cache service."""

    @pytest.mark.asyncio
    async def test_should_cache_deterministic(self) -> None:
        """Caching is enabled when temperature is 0 and not streaming."""
        assert CacheService.should_cache(temperature=0, stream=False) is True

    @pytest.mark.asyncio
    async def test_should_not_cache_streaming(self) -> None:
        """Caching is disabled for streaming requests."""
        assert CacheService.should_cache(temperature=0, stream=True) is False

    @pytest.mark.asyncio
    async def test_should_not_cache_non_deterministic(self) -> None:
        """Caching is disabled when temperature > 0."""
        assert CacheService.should_cache(temperature=0.7, stream=False) is False

    @pytest.mark.asyncio
    async def test_cache_miss(self, mock_redis: AsyncMock) -> None:
        """Cache miss returns None."""
        service = CacheService(mock_redis)
        result = await service.get("nonexistent-key")
        assert result is None
