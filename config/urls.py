"""config/urls.py — root URL configuration."""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth endpoints (JWT + logout)
    path("auth/", include("apps.users.urls")),

    # OAuth2 — Google (allauth headless)
    path("auth/", include("allauth.socialaccount.urls")),

    # dj-rest-auth registration
    path("auth/registration/", include("dj_rest_auth.registration.urls")),

    # App routers (added in later sprints)
    # path("api/", include("apps.sales.urls")),
    # path("api/", include("apps.production.urls")),

    # Health check
    path("health/", include("apps.core.urls")),
]

# OpenAPI docs — dev only
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

    # Silk profiler
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
