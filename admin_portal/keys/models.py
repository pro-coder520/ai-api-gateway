"""Django models for API keys, rate limit policies, and provider configuration.

These tables are shared with the FastAPI gateway via the same PostgreSQL database.
The gateway reads from them using SQLAlchemy; Django owns the schema and migrations.
"""

import hashlib
import secrets

from django.db import models


class ApiKey(models.Model):
    """An API key used by clients to authenticate with the gateway."""

    name = models.CharField(max_length=255, help_text="Friendly name for the key.")
    prefix = models.CharField(
        max_length=8, db_index=True, help_text="First 8 chars for display."
    )
    hashed_key = models.CharField(
        max_length=64, unique=True, db_index=True, help_text="SHA-256 hash of the key."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    scopes = models.TextField(
        null=True,
        blank=True,
        help_text="Comma-separated list of allowed model prefixes.",
    )

    class Meta:
        db_table = "keys_apikey"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def generate(cls, name: str, scopes: str | None = None) -> tuple["ApiKey", str]:
        """Create a new API key, returning (instance, plaintext_key).

        The plaintext key is only available at creation time. It is
        hashed with SHA-256 before storage.
        """
        raw_key = f"sk-{secrets.token_urlsafe(48)}"
        hashed = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        instance = cls(
            name=name,
            prefix=raw_key[:8],
            hashed_key=hashed,
            scopes=scopes,
        )
        return instance, raw_key


class RateLimitPolicy(models.Model):
    """Rate limit policy attached to a specific API key."""

    api_key = models.OneToOneField(
        ApiKey, on_delete=models.CASCADE, related_name="rate_limit_policy"
    )
    capacity = models.IntegerField(default=60, help_text="Max burst (bucket size).")
    refill_rate = models.FloatField(default=1.0, help_text="Tokens per second.")
    daily_token_limit = models.IntegerField(
        default=1_000_000, help_text="Max tokens per day."
    )

    class Meta:
        db_table = "keys_ratelimitpolicy"

    def __str__(self) -> str:
        return f"Rate limit for {self.api_key.name}"


class Provider(models.Model):
    """An LLM provider configuration."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    api_base = models.URLField(max_length=500)
    api_key_env_var = models.CharField(
        max_length=100, help_text="Name of the env var holding the API key."
    )
    is_active = models.BooleanField(default=True)
    model_prefix = models.CharField(
        max_length=50,
        help_text="Model name prefix routed to this provider (e.g. 'gpt-').",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "keys_provider"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
