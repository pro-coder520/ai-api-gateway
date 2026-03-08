"""Views for API key management."""

import structlog
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from keys.models import ApiKey, Provider, RateLimitPolicy
from keys.serializers import (
    ApiKeyCreateSerializer,
    ApiKeyCreatedSerializer,
    ApiKeyResponseSerializer,
    ProviderSerializer,
    RateLimitPolicySerializer,
)

logger = structlog.get_logger(__name__)


class ApiKeyListCreateView(APIView):
    """List all API keys or create a new one.

    POST creates a key, returns the plaintext once, and stores the SHA-256 hash.
    """

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        """List all API keys (without plaintext)."""
        keys = ApiKey.objects.select_related("rate_limit_policy").all()
        serializer = ApiKeyResponseSerializer(keys, many=True)
        return Response(serializer.data)

    def post(self, request) -> Response:  # type: ignore[no-untyped-def]
        """Create a new API key."""
        serializer = ApiKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        api_key, raw_key = ApiKey.generate(
            name=serializer.validated_data["name"],
            scopes=serializer.validated_data.get("scopes"),
        )
        api_key.save()

        # Create rate limit policy if provided
        rate_limit_data = serializer.validated_data.get("rate_limit")
        if rate_limit_data:
            RateLimitPolicy.objects.create(api_key=api_key, **rate_limit_data)
        else:
            RateLimitPolicy.objects.create(api_key=api_key)

        logger.info("api_key_created", key_id=api_key.id, name=api_key.name)

        return Response(
            ApiKeyCreatedSerializer(
                {
                    "id": api_key.id,
                    "name": api_key.name,
                    "prefix": api_key.prefix,
                    "key": raw_key,
                    "created_at": api_key.created_at,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ApiKeyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or revoke an API key."""

    queryset = ApiKey.objects.select_related("rate_limit_policy").all()
    serializer_class = ApiKeyResponseSerializer

    def perform_destroy(self, instance: ApiKey) -> None:
        """Revoke a key by deactivating it (soft delete)."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        logger.info("api_key_revoked", key_id=instance.id, name=instance.name)


class ProviderListCreateView(generics.ListCreateAPIView):
    """List all providers or create a new one."""

    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer


class ProviderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a provider."""

    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
