"""Django admin registrations for key management models."""

from django.contrib import admin

from keys.models import ApiKey, Provider, RateLimitPolicy


class RateLimitPolicyInline(admin.StackedInline):
    """Inline editor for rate limit policies on the API key admin page."""

    model = RateLimitPolicy
    extra = 0


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    """Admin configuration for API keys."""

    list_display = ["name", "prefix", "is_active", "created_at", "last_used_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "prefix"]
    readonly_fields = ["hashed_key", "prefix", "created_at"]
    inlines = [RateLimitPolicyInline]


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    """Admin configuration for LLM providers."""

    list_display = ["name", "slug", "is_active", "model_prefix", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
