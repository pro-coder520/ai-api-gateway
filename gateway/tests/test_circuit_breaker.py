"""Tests for the circuit breaker."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from resilience.circuit_breaker import CircuitBreaker, CircuitState


@pytest_asyncio.fixture
async def circuit_breaker(mock_redis: AsyncMock) -> CircuitBreaker:
    """Provide a circuit breaker backed by a mock Redis."""
    return CircuitBreaker(
        redis_client=mock_redis,
        provider_slug="test-provider",
        failure_threshold=3,
        recovery_timeout=30,
        half_open_max_requests=2,
    )


class TestCircuitBreaker:
    """Test suite for the Redis-backed circuit breaker."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(
        self, circuit_breaker: CircuitBreaker, mock_redis: AsyncMock
    ) -> None:
        """A new circuit breaker starts in CLOSED state."""
        mock_redis.get = AsyncMock(return_value=None)
        state = await circuit_breaker.get_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_request_allowed_when_closed(
        self, circuit_breaker: CircuitBreaker, mock_redis: AsyncMock
    ) -> None:
        """Requests are allowed when the circuit is CLOSED."""
        mock_redis.get = AsyncMock(return_value=None)
        assert await circuit_breaker.is_request_allowed() is True

    @pytest.mark.asyncio
    async def test_request_denied_when_open(
        self, circuit_breaker: CircuitBreaker, mock_redis: AsyncMock
    ) -> None:
        """Requests are denied when the circuit is OPEN."""
        # Mock get to return "open" for state, then a recent timestamp for opened_at
        import time

        mock_redis.get = AsyncMock(side_effect=["open", str(time.time())])
        assert await circuit_breaker.is_request_allowed() is False
