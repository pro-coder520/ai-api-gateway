"""Views for usage analytics.

Provides endpoints for querying request logs and viewing aggregated
usage statistics with date-range filtering.
"""

from datetime import timedelta

from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.models import RequestLog
from analytics.serializers import RequestLogSerializer, UsageSummarySerializer


class RequestLogListView(generics.ListAPIView):
    """List request logs with optional date-range filtering."""

    serializer_class = RequestLogSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        """Filter by date range, model, provider, or key_id if provided."""
        qs = RequestLog.objects.all()
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        model = self.request.query_params.get("model")
        provider = self.request.query_params.get("provider")
        key_id = self.request.query_params.get("key_id")

        if start:
            qs = qs.filter(timestamp__gte=start)
        if end:
            qs = qs.filter(timestamp__lte=end)
        if model:
            qs = qs.filter(model=model)
        if provider:
            qs = qs.filter(provider=provider)
        if key_id:
            qs = qs.filter(key_id=key_id)
        return qs


def _parse_days(raw: str | None, default: int) -> int:
    """Parse and clamp the 'days' query parameter."""
    try:
        days = int(raw) if raw else default
    except (ValueError, TypeError):
        days = default
    return max(1, min(days, 365))


class UsageSummaryView(APIView):
    """Aggregated usage statistics with date-range filtering."""

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        """Return aggregated usage stats for the given period."""
        days = _parse_days(request.query_params.get("days"), 7)
        since = timezone.now() - timedelta(days=days)
        qs = RequestLog.objects.filter(timestamp__gte=since)

        total = qs.count()
        aggregates = qs.aggregate(
            total_tokens=Sum("total_tokens"),
            total_cost_usd=Sum("cost_usd"),
            avg_latency_ms=Avg("latency_ms"),
        )
        cached_count = qs.filter(cached=True).count()
        error_count = qs.filter(status_code__gte=400).count()

        data = {
            "total_requests": total,
            "total_tokens": aggregates["total_tokens"] or 0,
            "total_cost_usd": round(aggregates["total_cost_usd"] or 0.0, 6),
            "avg_latency_ms": round(aggregates["avg_latency_ms"] or 0.0, 2),
            "cache_hit_ratio": round(cached_count / total, 4) if total > 0 else 0.0,
            "error_rate": round(error_count / total, 4) if total > 0 else 0.0,
        }
        serializer = UsageSummarySerializer(data)
        return Response(serializer.data)


class CostByModelView(APIView):
    """Cost breakdown by model."""

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        """Return cost aggregated by model name."""
        days = _parse_days(request.query_params.get("days"), 7)
        since = timezone.now() - timedelta(days=days)
        breakdown = (
            RequestLog.objects.filter(timestamp__gte=since)
            .values("model")
            .annotate(
                total_cost=Sum("cost_usd"),
                total_tokens=Sum("total_tokens"),
                request_count=Count("id"),
            )
            .order_by("-total_cost")
        )
        return Response(list(breakdown))


class CostByKeyView(APIView):
    """Cost breakdown by API key."""

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        """Return cost aggregated by API key ID."""
        days = _parse_days(request.query_params.get("days"), 7)
        since = timezone.now() - timedelta(days=days)
        breakdown = (
            RequestLog.objects.filter(timestamp__gte=since)
            .values("key_id")
            .annotate(
                total_cost=Sum("cost_usd"),
                total_tokens=Sum("total_tokens"),
                request_count=Count("id"),
            )
            .order_by("-total_cost")
        )
        return Response(list(breakdown))
