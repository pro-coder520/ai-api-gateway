"""Tests for API key authentication."""

import pytest

from auth.service import hash_api_key, get_key_prefix


class TestAuthService:
    """Test suite for auth service utilities."""

    def test_hash_api_key_deterministic(self) -> None:
        """Hashing the same key always produces the same result."""
        key = "sk-test-key-12345"
        assert hash_api_key(key) == hash_api_key(key)

    def test_hash_api_key_different_keys(self) -> None:
        """Different keys produce different hashes."""
        assert hash_api_key("key-a") != hash_api_key("key-b")

    def test_hash_api_key_length(self) -> None:
        """SHA-256 hex digest is always 64 characters."""
        assert len(hash_api_key("any-key")) == 64

    def test_get_key_prefix(self) -> None:
        """Prefix extraction returns the first 8 characters."""
        assert get_key_prefix("sk-test-key-12345") == "sk-test-"
