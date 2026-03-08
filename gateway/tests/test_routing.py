"""Tests for provider routing logic."""

import pytest

from routing.router import resolve_provider_slug


class TestProviderRouting:
    """Test suite for model-to-provider routing."""

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
