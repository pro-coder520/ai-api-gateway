"""Serializers for analytics endpoints."""

from rest_framework import serializers

from analytics.models import RequestLog


class RequestLogSerializer(serializers.ModelSerializer):
    """Serializer for individual request log entries."""

    class Meta:
        model = RequestLog
        fields = "__all__"


class UsageSummarySerializer(serializers.Serializer):
    """Serializer for aggregated usage statistics."""

    total_requests = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    total_cost_usd = serializers.FloatField()
    avg_latency_ms = serializers.FloatField()
    cache_hit_ratio = serializers.FloatField()
    error_rate = serializers.FloatField()
