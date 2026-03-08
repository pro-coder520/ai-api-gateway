"""Provider selection logic.

Maps model identifiers to the appropriate LLM provider using database
configuration. Falls back to prefix-based routing when DB config is
unavailable.
"""

import structlog

logger = structlog.get_logger(__name__)

# Prefix-based fallback mapping (overridden by DB config in Step 5)
_DEFAULT_PREFIX_MAP: dict[str, str] = {
    "gpt-": "openai",
    "claude-": "anthropic",
}


def resolve_provider_slug(model: str) -> str:
    """Determine the provider slug for a given model identifier.

    Args:
        model: The model name from the client request.

    Returns:
        Provider slug string (e.g. 'openai', 'anthropic', 'ollama').
    """
    for prefix, slug in _DEFAULT_PREFIX_MAP.items():
        if model.startswith(prefix):
            return slug
    # Default to Ollama for unknown models (local inference)
    return "ollama"
