"""Analytics app configuration."""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Django app configuration for usage analytics."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"
    verbose_name = "Usage Analytics"
