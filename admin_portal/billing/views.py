"""Views for billing and cost tracking."""

from datetime import timedelta

from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import BillingRecord
from billing.serializers import BillingRecordSerializer


class BillingRecordListView(generics.ListAPIView):
    """List billing records with optional date-range filtering."""

    serializer_class = BillingRecordSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        """Filter by date range and key_id if provided."""
        qs = BillingRecord.objects.all()
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        key_id = self.request.query_params.get("key_id")

        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        if key_id:
            qs = qs.filter(key_id=key_id)
        return qs


class BillingSummaryView(APIView):
    """Return a high-level billing summary for a given period."""

    def get(self, request) -> Response:  # type: ignore[no-untyped-def]
        """Return total cost and token usage for the period."""
        days = int(request.query_params.get("days", 30))
        since = timezone.now().date() - timedelta(days=days)
        qs = BillingRecord.objects.filter(date__gte=since)

        from django.db.models import Sum

        totals = qs.aggregate(
            total_cost=Sum("cost_usd"),
            total_tokens=Sum("total_tokens"),
            total_requests=Sum("request_count"),
        )

        return Response(
            {
                "period_days": days,
                "total_cost_usd": round(totals["total_cost"] or 0.0, 6),
                "total_tokens": totals["total_tokens"] or 0,
                "total_requests": totals["total_requests"] or 0,
            }
        )
