"""Shared test fixtures for gateway unit and integration tests."""

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_redis() -> AsyncMock:
    """Provide a mock async Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.incrby = AsyncMock(return_value=1)
    redis_mock.evalsha = AsyncMock(return_value=1)
    redis_mock.script_load = AsyncMock(return_value="mock_sha")
    redis_mock.hmget = AsyncMock(return_value=[None, None])
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zremrangebyscore = AsyncMock(return_value=0)
    redis_mock.aclose = AsyncMock()
    return redis_mock


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """Provide an HTTP test client for the FastAPI app.

    Patches dependencies to use mocks instead of real DB/Redis.
    """
    from main import app
    from dependencies import get_redis, get_db_session

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)

    mock_session = AsyncMock()

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
