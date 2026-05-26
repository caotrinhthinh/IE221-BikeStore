"""apps/production/urls.py — Production URLs."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"categories", views.CategoryViewSet, basename="category")
router.register(r"brands", views.BrandViewSet, basename="brand")
router.register(r"products", views.ProductViewSet, basename="product")
router.register(r"stocks", views.StockViewSet, basename="stock")

urlpatterns = [
    path("", include(router.urls)),
]
