"""URL routing for the keys API."""

from django.urls import path

from keys.views import (
    ApiKeyDetailView,
    ApiKeyListCreateView,
    ProviderDetailView,
    ProviderListCreateView,
)

urlpatterns = [
    path("", ApiKeyListCreateView.as_view(), name="apikey-list-create"),
    path("<int:pk>/", ApiKeyDetailView.as_view(), name="apikey-detail"),
    path("providers/", ProviderListCreateView.as_view(), name="provider-list-create"),
    path("providers/<int:pk>/", ProviderDetailView.as_view(), name="provider-detail"),
]
