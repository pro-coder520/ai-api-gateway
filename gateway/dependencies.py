"""Dependency injection for database sessions, Redis connections, and auth."""

from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

logger = structlog.get_logger(__name__)

# ── Module-level singletons (initialised in lifespan) ────────────────────────

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis: aioredis.Redis | None = None


# ── Database ──────────────────────────────────────────────────────────────────


async def init_db_engine() -> None:
    """Create the async SQLAlchemy engine and session factory."""
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.gateway_debug,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    await logger.ainfo(
        "Database engine initialised", url=settings.database_url.split("@")[-1]
    )


async def shutdown_db_engine() -> None:
    """Dispose the async engine and release all connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        await logger.ainfo("Database engine disposed")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory for fire-and-forget tasks."""
    if _session_factory is None:
        raise RuntimeError(
            "Database engine not initialised. Call init_db_engine() first."
        )
    return _session_factory


async def get_db_session():
    """FastAPI dependency that yields an async database session."""
    if _session_factory is None:
        raise RuntimeError(
            "Database engine not initialised. Call init_db_engine() first."
        )
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Redis ─────────────────────────────────────────────────────────────────────


async def init_redis() -> None:
    """Create the async Redis connection pool."""
    global _redis
    _redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )
    await _redis.ping()
    await logger.ainfo("Redis connection pool initialised")


async def shutdown_redis() -> None:
    """Close the Redis connection pool."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        await logger.ainfo("Redis connection pool closed")


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency that returns the shared Redis client."""
    if _redis is None:
        raise RuntimeError("Redis not initialised. Call init_redis() first.")
    return _redis


# ── Auth ──────────────────────────────────────────────────────────────────────


async def get_current_api_key(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session: AsyncSession = Depends(get_db_session),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> dict:
    """Extract and validate the API key from the Authorization header.

    Pipeline:
    1. Extract Bearer token.
    2. Hash with SHA-256.
    3. Check Redis cache (5 min TTL).
    4. Fallback to PostgreSQL on cache miss.
    5. Return key metadata dict on success, 401 on failure.

    Returns:
        dict with key metadata: id, name, prefix, is_active, scopes, rate_limit.
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "type": "auth_error",
                    "message": "Missing Authorization header",
                    "code": "missing_auth",
                }
            },
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "type": "auth_error",
                    "message": "Invalid authorization scheme. Use 'Bearer <key>'",
                    "code": "invalid_auth",
                }
            },
        )

    from auth.service import validate_api_key

    try:
        key_data = await validate_api_key(token, session, redis_client)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "type": "auth_error",
                    "message": str(exc),
                    "code": "invalid_key",
                }
            },
        )

    return key_data


# ── Typed dependency aliases ──────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Redis = Annotated[aioredis.Redis, Depends(get_redis)]
CurrentApiKey = Annotated[dict, Depends(get_current_api_key)]
