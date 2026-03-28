"""Tests for API key authentication."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from auth.service import hash_api_key, verify_api_key, get_key_prefix, validate_api_key


class TestAuthServiceUtilities:
    """Test suite for auth service utility functions."""

    def test_hash_and_verify_api_key(self) -> None:
        """Hashing a key and verifying it returns True."""
        key = "sk-test-key-12345"
        hashed = hash_api_key(key)
        assert verify_api_key(key, hashed) is True

    def test_verify_wrong_key(self) -> None:
        """Verifying a wrong key returns False."""
        hashed = hash_api_key("correct-key")
        assert verify_api_key("wrong-key", hashed) is False

    def test_hash_api_key_unique_salts(self) -> None:
        """Bcrypt generates different hashes for the same key (unique salts)."""
        key = "sk-test-key-12345"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 != hash2  # Different salts
        assert verify_api_key(key, hash1) is True
        assert verify_api_key(key, hash2) is True

    def test_hash_api_key_length(self) -> None:
        """Bcrypt hash is always 60 characters."""
        assert len(hash_api_key("any-key")) == 60

    def test_get_key_prefix(self) -> None:
        """Prefix extraction returns the first 8 characters."""
        assert get_key_prefix("sk-test-key-12345") == "sk-test-"


class TestValidateApiKey:
    """Test suite for the full key validation pipeline."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_key_data(self) -> None:
        """Cached key data is returned without hitting DB."""
        import json

        mock_redis = AsyncMock()
        mock_session = AsyncMock()
        key_data = {
            "id": 1,
            "name": "test",
            "is_active": True,
            "scopes": None,
            "rate_limit": None,
            "prefix": "sk-test-",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(key_data))

        result = await validate_api_key("sk-test-key", mock_session, mock_redis)
        assert result["id"] == 1
        assert result["is_active"] is True
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_key_raises_value_error(self) -> None:
        """An unknown key raises ValueError."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Invalid API key"):
            await validate_api_key("sk-unknown-key", mock_session, mock_redis)

    @pytest.mark.asyncio
    async def test_revoked_key_from_cache(self) -> None:
        """A revoked key in the cache raises ValueError."""
        import json

        mock_redis = AsyncMock()
        mock_session = AsyncMock()
        key_data = {"id": 1, "name": "revoked", "is_active": False}
        mock_redis.get = AsyncMock(return_value=json.dumps(key_data))

        with pytest.raises(ValueError, match="revoked"):
            await validate_api_key("sk-revoked-key", mock_session, mock_redis)
