"""Tests for provider routing logic."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from routing.router import resolve_provider_slug, resolve_provider_slug_from_db


class TestPrefixRouting:
    """Test suite for prefix-based model-to-provider routing."""

    def test_openai_routing(self) -> None:
        """Models starting with 'gpt-' route to OpenAI."""
        assert resolve_provider_slug("gpt-4") == "openai"
        assert resolve_provider_slug("gpt-3.5-turbo") == "openai"
        assert resolve_provider_slug("gpt-4o") == "openai"

    def test_anthropic_routing(self) -> None:
        """Models starting with 'claude-' route to Anthropic."""
        assert resolve_provider_slug("claude-3-opus-20240229") == "anthropic"
        assert resolve_provider_slug("claude-3-haiku-20240307") == "anthropic"

    def test_ollama_fallback(self) -> None:
        """Unknown models default to Ollama."""
        assert resolve_provider_slug("llama3") == "ollama"
        assert resolve_provider_slug("mistral") == "ollama"
        assert resolve_provider_slug("custom-model") == "ollama"


class TestDbRouting:
    """Test suite for database-backed routing."""

    @pytest.mark.asyncio
    async def test_db_routing_with_provider_match(self) -> None:
        """DB routing returns the provider slug when a prefix match is found."""
        mock_provider = MagicMock()
        mock_provider.slug = "openai"
        mock_provider.model_prefix = "gpt-"
        mock_provider.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_provider]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await resolve_provider_slug_from_db("gpt-4", mock_session)
        assert result == "openai"

    @pytest.mark.asyncio
    async def test_db_routing_falls_back_to_prefix(self) -> None:
        """DB routing falls back to prefix matching when no DB match is found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await resolve_provider_slug_from_db("gpt-4", mock_session)
        assert result == "openai"

    @pytest.mark.asyncio
    async def test_db_routing_handles_db_error(self) -> None:
        """DB routing falls back gracefully on database errors."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))

        result = await resolve_provider_slug_from_db("gpt-4", mock_session)
        assert result == "openai"  # Falls back to prefix
