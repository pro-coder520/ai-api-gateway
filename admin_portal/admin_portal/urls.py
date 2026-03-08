"""Admin portal URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/keys/", include("keys.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/billing/", include("billing.urls")),
]
