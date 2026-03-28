"""Initial migration: creates ApiKey, RateLimitPolicy, and Provider tables."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the core keys app tables shared with the FastAPI gateway."""

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ApiKey",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Friendly name for the key.", max_length=255
                    ),
                ),
                (
                    "prefix",
                    models.CharField(
                        db_index=True,
                        help_text="First 8 chars for display.",
                        max_length=8,
                    ),
                ),
                (
                    "hashed_key",
                    models.CharField(
                        db_index=True,
                        help_text="Bcrypt hash of the key.",
                        max_length=128,
                        unique=True,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "scopes",
                    models.TextField(
                        blank=True,
                        help_text="Comma-separated list of allowed model prefixes.",
                        null=True,
                    ),
                ),
            ],
            options={
                "db_table": "keys_apikey",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RateLimitPolicy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "capacity",
                    models.IntegerField(
                        default=60, help_text="Max burst (bucket size)."
                    ),
                ),
                (
                    "refill_rate",
                    models.FloatField(
                        default=1.0, help_text="Tokens per second."
                    ),
                ),
                (
                    "daily_token_limit",
                    models.IntegerField(
                        default=1000000, help_text="Max tokens per day."
                    ),
                ),
                (
                    "api_key",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rate_limit_policy",
                        to="keys.apikey",
                    ),
                ),
            ],
            options={
                "db_table": "keys_ratelimitpolicy",
            },
        ),
        migrations.CreateModel(
            name="Provider",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=50, unique=True)),
                ("api_base", models.URLField(max_length=500)),
                (
                    "api_key_env_var",
                    models.CharField(
                        help_text="Name of the env var holding the API key.",
                        max_length=100,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "model_prefix",
                    models.CharField(
                        help_text="Model name prefix routed to this provider (e.g. 'gpt-').",
                        max_length=50,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "keys_provider",
                "ordering": ["name"],
            },
        ),
    ]
