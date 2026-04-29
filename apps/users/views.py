"""
apps/users/views.py — Auth views.

Notes:
- LoginView / LogoutView come from dj-rest-auth (configured in urls.py).
- GoogleLoginView redirects to Google consent; GoogleCallbackView exchanges the
  authorization code and returns a JWT pair.
- All business logic lives in apps/users/services.py, NOT here.
"""
from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .serializers import UserSerializer
from . import services as user_services


class CurrentUserView(APIView):
    """GET /auth/me/ — return authenticated user profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
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
    authentication_classes = []

    @extend_schema(
        description="Google OAuth2 callback — returns JWT access + refresh tokens.",
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
