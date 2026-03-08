"""URL routing for analytics endpoints."""

from django.urls import path

from analytics.views import (
    CostByKeyView,
    CostByModelView,
    RequestLogListView,
    UsageSummaryView,
)

urlpatterns = [
    path("logs/", RequestLogListView.as_view(), name="request-log-list"),
    path("summary/", UsageSummaryView.as_view(), name="usage-summary"),
    path("cost-by-model/", CostByModelView.as_view(), name="cost-by-model"),
    path("cost-by-key/", CostByKeyView.as_view(), name="cost-by-key"),
]
