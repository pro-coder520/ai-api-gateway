"""Seed initial provider configurations into the database.

Usage:
    docker compose exec admin python ../scripts/seed_providers.py

Or from within the admin container:
    cd /app && DJANGO_SETTINGS_MODULE=admin_portal.settings python ../scripts/seed_providers.py
"""

import os
import sys

# Add admin_portal to path so Django can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "admin_portal"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_portal.settings")

import django

django.setup()

from keys.models import Provider


PROVIDERS = [
    {
        "name": "OpenAI",
        "slug": "openai",
        "api_base": "https://api.openai.com/v1",
        "api_key_env_var": "OPENAI_API_KEY",
        "model_prefix": "gpt-",
        "is_active": True,
    },
    {
        "name": "Anthropic",
        "slug": "anthropic",
        "api_base": "https://api.anthropic.com",
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "model_prefix": "claude-",
        "is_active": True,
    },
    {
        "name": "Ollama",
        "slug": "ollama",
        "api_base": os.environ.get("OLLAMA_API_BASE", "http://localhost:11434"),
        "api_key_env_var": "OLLAMA_API_KEY",
        "model_prefix": "",
        "is_active": True,
    },
]


def main() -> None:
    """Seed provider configurations into the database."""
    for provider_data in PROVIDERS:
        provider, created = Provider.objects.update_or_create(
            slug=provider_data["slug"],
            defaults=provider_data,
        )
        action = "Created" if created else "Updated"
        print(f"{action} provider: {provider.name} ({provider.slug})")

    print(f"\nTotal providers: {Provider.objects.count()}")


if __name__ == "__main__":
    main()
