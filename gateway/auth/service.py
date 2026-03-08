"""API key validation, hashing, and Redis-cached lookups.

Full implementation is added in Step 3. This module provides the service
interface and hashing utilities.
"""

import hashlib

import structlog

logger = structlog.get_logger(__name__)


def hash_api_key(raw_key: str) -> str:
    """Return the SHA-256 hex digest of a raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_key_prefix(raw_key: str) -> str:
    """Return the first 8 characters of a key for safe display."""
    return raw_key[:8]
