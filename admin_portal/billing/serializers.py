"""Serializers for billing endpoints."""

from rest_framework import serializers

from billing.models import BillingRecord


class BillingRecordSerializer(serializers.ModelSerializer):
    """Serializer for billing records."""

    class Meta:
        model = BillingRecord
        fields = "__all__"
