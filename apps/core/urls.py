"""apps/core/urls.py — health-check endpoint."""
from django.urls import path
from .views import HealthCheckView

urlpatterns = [
    path("", HealthCheckView.as_view(), name="health-check"),
]
