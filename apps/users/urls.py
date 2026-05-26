"""
apps/users/urls.py — Auth endpoints.

Endpoints:
    POST   /auth/login/         → access + refresh JWT
    POST   /auth/logout/        → blacklist refresh token
    POST   /auth/token/refresh/ → get new access token
    GET    /auth/me/            → current user profile
    GET    /auth/google/        → OAuth2 redirect
    GET    /auth/google/callback/ → exchange code → JWT
"""

from django.urls import path

from .views import (
    CurrentUserView,
    GoogleCallbackView,
    GoogleLoginView,
    LogoutView,
    RateLimitedLoginView,
    TokenRefreshView,
)

urlpatterns = [
    # JWT Auth
    path("login/", RateLimitedLoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
    # Google OAuth2
    path("google/", GoogleLoginView.as_view(), name="auth-google-login"),
    path("google/callback/", GoogleCallbackView.as_view(), name="auth-google-callback"),
]
