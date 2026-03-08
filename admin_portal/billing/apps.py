"""Billing app configuration."""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    """Django app configuration for cost tracking and billing."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "billing"
    verbose_name = "Billing & Cost Tracking"
