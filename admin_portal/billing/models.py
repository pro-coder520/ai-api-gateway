"""Django models for billing records.

BillingRecord stores daily aggregated usage and cost data,
populated by the analytics aggregation Celery task.
"""

from django.db import models


class BillingRecord(models.Model):
    """Daily aggregated billing record per key and model."""

    date = models.DateField(db_index=True)
    key_id = models.IntegerField(null=True, blank=True, db_index=True)
    model = models.CharField(max_length=200)
    provider = models.CharField(max_length=100)
    request_count = models.IntegerField(default=0)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    cost_usd = models.FloatField(default=0.0)
    avg_latency_ms = models.FloatField(default=0.0)

    class Meta:
        db_table = "billing_billingrecord"
        ordering = ["-date"]
        unique_together = ["date", "key_id", "model"]

    def __str__(self) -> str:
        return f"Billing({self.date}, key={self.key_id}, model={self.model}, ${self.cost_usd:.4f})"
