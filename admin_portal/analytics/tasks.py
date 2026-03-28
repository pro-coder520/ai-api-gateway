"""Celery tasks for analytics aggregation.

Runs as periodic tasks to aggregate request_logs into billing_records.
"""

import structlog
from datetime import timedelta

from celery import shared_task
from django.db.models import Avg, Count, Sum
from django.utils import timezone

logger = structlog.get_logger(__name__)


@shared_task(name="analytics.tasks.aggregate_daily_billing")
def aggregate_daily_billing() -> None:
    """Aggregate yesterday's request logs into daily billing records.

    Called by Celery beat once per day. Full Celery integration is
    completed in Step 11.
    """
    from analytics.models import RequestLog
    from billing.models import BillingRecord

    yesterday = timezone.now().date() - timedelta(days=1)
    logs = RequestLog.objects.filter(
        timestamp__date=yesterday,
    )

    if not logs.exists():
        logger.info("no_logs_to_aggregate", date=str(yesterday))
        return

    # Aggregate by key_id + model
    aggregates = logs.values("key_id", "model", "provider").annotate(
        request_count=Count("id"),
        total_input_tokens=Sum("input_tokens"),
        total_output_tokens=Sum("output_tokens"),
        total_tokens_sum=Sum("total_tokens"),
        total_cost=Sum("cost_usd"),
        avg_latency=Avg("latency_ms"),
    )

    for agg in aggregates:
        BillingRecord.objects.update_or_create(
            date=yesterday,
            key_id=agg["key_id"],
            model=agg["model"],
            defaults={
                "provider": agg["provider"],
                "request_count": agg["request_count"],
                "input_tokens": agg["total_input_tokens"] or 0,
                "output_tokens": agg["total_output_tokens"] or 0,
                "total_tokens": agg["total_tokens_sum"] or 0,
                "cost_usd": agg["total_cost"] or 0.0,
                "avg_latency_ms": agg["avg_latency"] or 0.0,
            },
        )

    logger.info(
        "daily_billing_aggregated", date=str(yesterday), records=len(aggregates)
    )
