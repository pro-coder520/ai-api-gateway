"""Initial migration: creates the BillingRecord table."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the billing_billingrecord table for daily aggregated usage."""

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BillingRecord",
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
                ("date", models.DateField(db_index=True)),
                ("key_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("model", models.CharField(max_length=200)),
                ("provider", models.CharField(max_length=100)),
                ("request_count", models.IntegerField(default=0)),
                ("input_tokens", models.IntegerField(default=0)),
                ("output_tokens", models.IntegerField(default=0)),
                ("total_tokens", models.IntegerField(default=0)),
                ("cost_usd", models.FloatField(default=0.0)),
                ("avg_latency_ms", models.FloatField(default=0.0)),
            ],
            options={
                "db_table": "billing_billingrecord",
                "ordering": ["-date"],
                "unique_together": {("date", "key_id", "model")},
            },
        ),
    ]
