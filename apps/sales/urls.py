"""apps/sales/urls.py — Sales URLs."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"stores", views.StoreViewSet, basename="store")
router.register(r"customers", views.CustomerViewSet, basename="customer")
router.register(r"staff", views.StaffViewSet, basename="staff")
router.register(r"orders", views.OrderViewSet, basename="order")

urlpatterns = [
    path("", include(router.urls)),
]
