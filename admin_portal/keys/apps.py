"""API Key management app configuration."""

from django.apps import AppConfig


class KeysConfig(AppConfig):
    """Django app configuration for the keys management module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "keys"
    verbose_name = "API Key Management"
