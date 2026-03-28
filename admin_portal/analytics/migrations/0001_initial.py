"""Initial migration: creates the RequestLog table."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the analytics_requestlog table written to by the FastAPI gateway."""

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RequestLog",
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
                ("key_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("model", models.CharField(db_index=True, max_length=200)),
                ("provider", models.CharField(max_length=100)),
                ("input_tokens", models.IntegerField(default=0)),
                ("output_tokens", models.IntegerField(default=0)),
                ("total_tokens", models.IntegerField(default=0)),
                ("latency_ms", models.FloatField(default=0.0)),
                ("status_code", models.IntegerField(default=200)),
                ("cost_usd", models.FloatField(default=0.0)),
                ("cached", models.BooleanField(default=False)),
                (
                    "timestamp",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
            ],
            options={
                "db_table": "analytics_requestlog",
                "ordering": ["-timestamp"],
            },
        ),
    ]
