"""
apps/users/views.py — Auth views.

Notes:
- LoginView / LogoutView come from dj-rest-auth (configured in urls.py).
- GoogleLoginView redirects to Google consent; GoogleCallbackView exchanges the
  authorization code and returns a JWT pair.
- All business logic lives in apps/users/services.py, NOT here.
"""

from contextlib import suppress

from dj_rest_auth.views import LoginView as DjRestAuthLoginView
from dj_rest_auth.views import LogoutView as _DjLogoutView
from django.core.cache import cache
from django.views import View
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView as _TokenRefreshView

from . import services as user_services
from .serializers import UserSerializer


@extend_schema_view(post=extend_schema(tags=["Auth"]))
class RateLimitedLoginView(DjRestAuthLoginView):
    """POST /auth/login/ with IP-based brute-force protection."""

    permission_classes = [AllowAny]
    max_failed_attempts = 5
    window_seconds = 15 * 60

    def post(self, request, *args, **kwargs):
        cache_key = self._cache_key(request)
        cache_available = True
        try:
            failed_attempts = cache.get(cache_key, 0)
        except Exception:
            cache_available = False
            failed_attempts = 0

        if cache_available and failed_attempts >= self.max_failed_attempts:
            response = Response(
                {"detail": "Too many login attempts. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(self.window_seconds)
            return response

        response = super().post(request, *args, **kwargs)

        if cache_available:
            with suppress(Exception):
                if response.status_code >= status.HTTP_400_BAD_REQUEST:
                    cache.set(
                        cache_key, failed_attempts + 1, timeout=self.window_seconds
                    )
                else:
                    cache.delete(cache_key)

        return response

    def _cache_key(self, request: Request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else ""
        ip_address = ip_address or request.META.get("REMOTE_ADDR", "unknown")
        return f"ratelimit:auth_login:{ip_address}"


class CurrentUserView(APIView):
    """GET /auth/me/ — return authenticated user profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"], responses=UserSerializer)
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)


class GoogleLoginView(APIView):
    """
    GET /auth/google/
    Redirect the browser to Google OAuth2 consent screen.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Auth"],
        description="Redirects to Google OAuth2 consent screen.",
        responses={302: None},
    )
    def get(self, request: Request) -> Response:
        redirect_url = user_services.get_google_auth_url(request)
        from django.shortcuts import redirect

        return redirect(redirect_url)


class GoogleCallbackView(APIView):
    """
    GET /auth/google/callback/?code=...&state=...
    Exchange authorization code → create/link User → return JWT pair.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        description="Google OAuth2 callback — returns JWT access + refresh tokens.",
        responses=inline_serializer(
            name="JWTPairResponse",
            fields={
                "access": serializers.CharField(),
                "refresh": serializers.CharField(),
            },
        ),
    )
    def get(self, request: Request) -> Response:
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        tokens = user_services.handle_google_callback(
            request=request,
            code=code,
            state=state,
        )
        return Response(tokens)


# ── Tagged wrappers for third-party views ─────────────────────────────────────


@extend_schema_view(post=extend_schema(tags=["Auth"]))
class LogoutView(_DjLogoutView):
    """POST /auth/logout/ — blacklist refresh token."""


@extend_schema_view(post=extend_schema(tags=["Auth"]))
class TokenRefreshView(_TokenRefreshView):
    """POST /auth/token/refresh/ — exchange refresh for new access token."""


class UserConfirmEmailView(View):
    """
    GET /auth/registration/account-confirm-email/<key>/
    Renders confirmation status HTML page.
    """

    def get(self, request, key, *args, **kwargs):
        from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC
        from django.shortcuts import render

        co = EmailConfirmationHMAC.from_key(key)
        if not co:
            try:
                co = EmailConfirmation.objects.get(key=key.lower())
            except EmailConfirmation.DoesNotExist:
                co = None

        success = False
        if co:
            email_address = co.confirm(request)
            if email_address:
                success = True

        return render(request, "account/email_confirm.html", {"success": success})
