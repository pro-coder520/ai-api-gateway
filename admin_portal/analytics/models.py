"""Django models for request logging and analytics.

The request_log table is written to by the FastAPI gateway (via SQLAlchemy)
and read from by this Django app for analytics and reporting.
"""

from django.db import models


class RequestLog(models.Model):
    """Stores every request flowing through the gateway for analytics."""

    key_id = models.IntegerField(null=True, blank=True, db_index=True)
    model = models.CharField(max_length=200, db_index=True)
    provider = models.CharField(max_length=100)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    latency_ms = models.FloatField(default=0.0)
    status_code = models.IntegerField(default=200)
    cost_usd = models.FloatField(default=0.0)
    cached = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "analytics_requestlog"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"RequestLog({self.model}, {self.status_code}, {self.timestamp})"
