"""URL routing for billing endpoints."""

from django.urls import path

from billing.views import BillingRecordListView, BillingSummaryView

urlpatterns = [
    path("", BillingRecordListView.as_view(), name="billing-list"),
    path("summary/", BillingSummaryView.as_view(), name="billing-summary"),
]
