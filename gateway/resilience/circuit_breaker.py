"""Per-provider circuit breaker backed by Redis.

Three states: CLOSED (normal), OPEN (failing → reject immediately),
HALF_OPEN (testing recovery). Failures are tracked via a Redis sorted
set with timestamps for a sliding window.
"""

import time
from enum import StrEnum

import redis.asyncio as aioredis
import structlog

from config import settings

logger = structlog.get_logger(__name__)


class CircuitState(StrEnum):
    """Possible states of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Redis-backed circuit breaker for a single provider.

    Attributes:
        provider_slug: Identifier for the provider.
        failure_threshold: Number of failures to trip the circuit.
        recovery_timeout: Seconds to wait before moving to HALF_OPEN.
        half_open_max_requests: Number of test requests allowed in HALF_OPEN.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        provider_slug: str,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
        half_open_max_requests: int | None = None,
    ) -> None:
        self.redis = redis_client
        self.provider_slug = provider_slug
        self.failure_threshold = failure_threshold or settings.cb_failure_threshold
        self.recovery_timeout = recovery_timeout or settings.cb_recovery_timeout
        self.half_open_max_requests = (
            half_open_max_requests or settings.cb_half_open_max_requests
        )

    @property
    def _state_key(self) -> str:
        return f"cb:{self.provider_slug}:state"

    @property
    def _failures_key(self) -> str:
        return f"cb:{self.provider_slug}:failures"

    @property
    def _opened_at_key(self) -> str:
        return f"cb:{self.provider_slug}:opened_at"

    @property
    def _half_open_count_key(self) -> str:
        return f"cb:{self.provider_slug}:half_open_count"

    async def get_state(self) -> CircuitState:
        """Return the current circuit state, transitioning from OPEN to HALF_OPEN if recovery timeout has elapsed."""
        state_raw = await self.redis.get(self._state_key)
        state = CircuitState(state_raw) if state_raw else CircuitState.CLOSED

        if state == CircuitState.OPEN:
            opened_at = await self.redis.get(self._opened_at_key)
            if opened_at and (time.time() - float(opened_at)) >= self.recovery_timeout:
                await self._set_state(CircuitState.HALF_OPEN)
                await self.redis.set(self._half_open_count_key, 0)
                return CircuitState.HALF_OPEN

        return state

    async def _set_state(self, state: CircuitState) -> None:
        """Persist the circuit state in Redis."""
        await self.redis.set(self._state_key, state.value)
        await logger.ainfo(
            "circuit_state_change", provider=self.provider_slug, new_state=state.value
        )

    async def record_success(self) -> None:
        """Record a successful request. May close the circuit from HALF_OPEN."""
        state = await self.get_state()
        if state == CircuitState.HALF_OPEN:
            count = await self.redis.incr(self._half_open_count_key)
            if count >= self.half_open_max_requests:
                await self._set_state(CircuitState.CLOSED)
                await self.redis.delete(
                    self._failures_key, self._opened_at_key, self._half_open_count_key
                )
        elif state == CircuitState.CLOSED:
            # Clean old failures outside sliding window
            cutoff = time.time() - self.recovery_timeout
            await self.redis.zremrangebyscore(self._failures_key, "-inf", cutoff)

    async def record_failure(self) -> None:
        """Record a failed request. May trip the circuit from CLOSED or reopen from HALF_OPEN."""
        now = time.time()
        state = await self.get_state()

        if state == CircuitState.HALF_OPEN:
            await self._open_circuit(now)
            return

        # Add failure to sliding window
        await self.redis.zadd(self._failures_key, {str(now): now})
        # Remove old entries outside window
        cutoff = now - self.recovery_timeout
        await self.redis.zremrangebyscore(self._failures_key, "-inf", cutoff)
        # Check threshold
        failure_count = await self.redis.zcard(self._failures_key)
        if failure_count >= self.failure_threshold:
            await self._open_circuit(now)

    async def _open_circuit(self, now: float) -> None:
        """Transition the circuit to OPEN state."""
        await self._set_state(CircuitState.OPEN)
        await self.redis.set(self._opened_at_key, str(now))
        await logger.awarn("circuit_opened", provider=self.provider_slug)

    async def is_request_allowed(self) -> bool:
        """Check whether a request should be allowed through.

        Returns:
            True if the circuit is CLOSED or HALF_OPEN (within limits).
            False if OPEN.
        """
        state = await self.get_state()
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            count_raw = await self.redis.get(self._half_open_count_key)
            count = int(count_raw) if count_raw else 0
            return count < self.half_open_max_requests
        return False  # OPEN
