"""Tests for token bucket rate limiting."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from ratelimit.token_bucket import TokenBucket


@pytest_asyncio.fixture
async def token_bucket(mock_redis: AsyncMock) -> TokenBucket:
    """Provide a TokenBucket backed by a mock Redis."""
    return TokenBucket(mock_redis)


class TestTokenBucket:
    """Test suite for the Redis-backed token bucket."""

    @pytest.mark.asyncio
    async def test_consume_allowed(self, token_bucket: TokenBucket) -> None:
        """A consume call returns True when tokens are available."""
        result = await token_bucket.consume("test-key", capacity=10, refill_rate=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_consume_denied(
        self, token_bucket: TokenBucket, mock_redis: AsyncMock
    ) -> None:
        """A consume call returns False when the bucket is empty."""
        mock_redis.evalsha = AsyncMock(return_value=0)
        result = await token_bucket.consume("test-key", capacity=10, refill_rate=1.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_daily_usage_increment(self, token_bucket: TokenBucket) -> None:
        """Daily usage counter is incremented correctly."""
        result = await token_bucket.increment_daily_usage("test-key", 100)
        assert result == 1  # mock returns 1

    @pytest.mark.asyncio
    async def test_get_daily_usage_empty(
        self, token_bucket: TokenBucket, mock_redis: AsyncMock
    ) -> None:
        """Daily usage returns 0 when no data exists."""
        mock_redis.get = AsyncMock(return_value=None)
        result = await token_bucket.get_daily_usage("test-key")
        assert result == 0
