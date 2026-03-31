"""API key validation, hashing, and Redis-cached lookups.

Uses bcrypt for secure key hashing. Since bcrypt salts each hash uniquely,
lookups use the key prefix to find candidates, then verify with bcrypt.checkpw().

Pipeline:
1. Extract Bearer token from Authorization header.
2. Check Redis cache by key prefix (TTL 5 min).
3. On cache miss, find candidates by prefix in PostgreSQL, verify with bcrypt.
4. Cache the result in Redis for subsequent requests.
5. Return 401 for invalid, inactive, or expired keys.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone

import bcrypt
import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.models import ApiKey, RateLimitPolicy

logger = structlog.get_logger(__name__)

CACHE_TTL_SECONDS: int = 300  # 5 minutes
CACHE_KEY_PREFIX: str = "auth:key:"


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using bcrypt.

    Returns:
        A bcrypt hash string (60 characters).
    """
    return bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Verify a raw API key against its bcrypt hash.

    Args:
        raw_key: The plaintext API key.
        hashed_key: The stored bcrypt hash.

    Returns:
        True if the key matches, False otherwise.
    """
    return bcrypt.checkpw(raw_key.encode("utf-8"), hashed_key.encode("utf-8"))


def get_key_prefix(raw_key: str) -> str:
    """Return the first 8 characters of a key for safe display and lookups."""
    return raw_key[:8]


async def validate_api_key(
    raw_key: str,
    session: AsyncSession,
    redis_client: aioredis.Redis,
) -> dict:
    """Validate an API key and return its metadata.

    Since bcrypt uses unique salts, we cannot do a direct hash lookup.
    Instead, we use the key prefix to narrow candidates, then verify
    with bcrypt.checkpw().

    Args:
        raw_key: The plaintext API key from the Authorization header.
        session: An async SQLAlchemy session.
        redis_client: The async Redis client.

    Returns:
        A dict with key metadata: id, name, is_active, scopes, rate_limit.

    Raises:
        ValueError: If the key is invalid, inactive, or expired.
    """
    prefix = get_key_prefix(raw_key)
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
    cache_key = f"{CACHE_KEY_PREFIX}{prefix}:{key_hash}"

    # ── Redis cache lookup ────────────────────────────────────────────
    cached = await redis_client.get(cache_key)
    if cached is not None:
        key_data = json.loads(cached)
        if not key_data.get("is_active", False):
            raise ValueError("API key has been revoked")
        await logger.adebug("auth_cache_hit", key_prefix=prefix)
        return key_data

    # ── Database lookup by prefix, then verify with bcrypt ────────────
    stmt = (
        select(ApiKey)
        .options(selectinload(ApiKey.rate_limit_policy))
        .where(ApiKey.prefix == prefix)
        .where(ApiKey.is_active == True)  # noqa: E712
    )
    result = await session.execute(stmt)
    candidates = result.scalars().all()

    api_key: ApiKey | None = None
    for candidate in candidates:
        matched = await asyncio.to_thread(
            verify_api_key, raw_key, candidate.hashed_key
        )
        if matched:
            api_key = candidate
            break

    if api_key is None:
        await logger.awarn("auth_invalid_key", key_prefix=prefix)
        raise ValueError("Invalid API key")

    if not api_key.is_active:
        await logger.awarn("auth_revoked_key", key_id=api_key.id)
        raise ValueError("API key has been revoked")

    if api_key.expires_at is not None and api_key.expires_at < datetime.now(
        timezone.utc
    ):
        await logger.awarn("auth_expired_key", key_id=api_key.id)
        raise ValueError("API key has expired")

    # Build key data dict
    rate_limit = None
    if api_key.rate_limit_policy is not None:
        rate_limit = {
            "capacity": api_key.rate_limit_policy.capacity,
            "refill_rate": api_key.rate_limit_policy.refill_rate,
            "daily_token_limit": api_key.rate_limit_policy.daily_token_limit,
        }

    key_data = {
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.prefix,
        "is_active": api_key.is_active,
        "scopes": api_key.scopes,
        "rate_limit": rate_limit,
    }

    # ── Cache the result ──────────────────────────────────────────────
    await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(key_data))
    await logger.adebug("auth_cache_set", key_id=api_key.id)

    # Update last_used_at (committed by the session dependency on exit)
    api_key.last_used_at = datetime.now(timezone.utc)

    return key_data
