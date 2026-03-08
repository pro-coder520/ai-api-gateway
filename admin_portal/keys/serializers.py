"""Serializers for API key management endpoints."""

from rest_framework import serializers

from keys.models import ApiKey, Provider, RateLimitPolicy


class RateLimitPolicySerializer(serializers.ModelSerializer):
    """Serializer for rate limit policies."""

    class Meta:
        model = RateLimitPolicy
        fields = ["id", "capacity", "refill_rate", "daily_token_limit"]
        read_only_fields = ["id"]


class ApiKeyCreateSerializer(serializers.Serializer):
    """Serializer for creating a new API key."""

    name = serializers.CharField(max_length=255)
    scopes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rate_limit = RateLimitPolicySerializer(required=False)


class ApiKeyResponseSerializer(serializers.ModelSerializer):
    """Serializer for API key responses (read-only)."""

    rate_limit_policy = RateLimitPolicySerializer(read_only=True)

    class Meta:
        model = ApiKey
        fields = [
            "id",
            "name",
            "prefix",
            "is_active",
            "created_at",
            "expires_at",
            "last_used_at",
            "scopes",
            "rate_limit_policy",
        ]
        read_only_fields = fields


class ApiKeyCreatedSerializer(serializers.Serializer):
    """Serializer for the one-time plaintext key response."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    prefix = serializers.CharField()
    key = serializers.CharField(help_text="Plaintext API key. Shown only once.")
    created_at = serializers.DateTimeField()


class ProviderSerializer(serializers.ModelSerializer):
    """Serializer for provider configuration."""

    class Meta:
        model = Provider
        fields = [
            "id",
            "name",
            "slug",
            "api_base",
            "api_key_env_var",
            "is_active",
            "model_prefix",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
