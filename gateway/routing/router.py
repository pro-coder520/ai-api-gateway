"""Provider selection logic.

Maps model identifiers to the appropriate LLM provider. Uses database
configuration as the primary source, with a prefix-based fallback.
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Prefix-based fallback mapping (used when DB is unavailable)
_DEFAULT_PREFIX_MAP: dict[str, str] = {
    "gpt-": "openai",
    "claude-": "anthropic",
}


def resolve_provider_slug(model: str) -> str:
    """Determine the provider slug for a given model identifier.

    Uses prefix-based matching as the default strategy.

    Args:
        model: The model name from the client request.

    Returns:
        Provider slug string (e.g. 'openai', 'anthropic', 'ollama').
    """
    for prefix, slug in _DEFAULT_PREFIX_MAP.items():
        if model.startswith(prefix):
            return slug
    return "ollama"


async def resolve_provider_slug_from_db(
    model: str,
    session: AsyncSession,
) -> str:
    """Determine the provider slug using the providers table in the database.

    Falls back to prefix-based matching if no DB match is found.

    Args:
        model: The model name from the client request.
        session: An async SQLAlchemy session.

    Returns:
        Provider slug string.
    """
    from auth.models import Provider

    try:
        stmt = select(Provider).where(Provider.is_active == True)  # noqa: E712
        result = await session.execute(stmt)
        providers = result.scalars().all()

        for provider in providers:
            if provider.model_prefix and model.startswith(provider.model_prefix):
                return provider.slug

    except Exception as exc:
        await logger.awarn("db_routing_fallback", error=str(exc))

    return resolve_provider_slug(model)
