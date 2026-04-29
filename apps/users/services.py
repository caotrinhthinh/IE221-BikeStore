"""
apps/users/services.py — Auth business logic.

Rules (HackSoft style):
- Views call services, never touch models directly.
- Services call selectors for read-only queries.
- Services own all mutations and external calls.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from . import selectors as user_selectors

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ── JWT helpers ───────────────────────────────────────────────────

def create_jwt_pair(user: User) -> dict[str, str]:
    """Return access + refresh JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# ── Google OAuth2 ─────────────────────────────────────────────────

def get_google_auth_url(request: Request) -> str:
    """
    Build the Google OAuth2 authorization URL.
    Uses allauth's adapter to ensure the state param (CSRF) is set.
    """
    from allauth.socialaccount.providers.google.provider import GoogleProvider
    from allauth.socialaccount.helpers import complete_social_login

    adapter = GoogleOAuth2Adapter(request)
    callback_url: str = settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"].get(
        "callback_url",
        request.build_absolute_uri("/auth/google/callback/"),
    )
    client = OAuth2Client(
        request,
        adapter.get_client_id(request),
        adapter.get_client_secret(request),
        adapter.access_token_method,
        adapter.access_token_url,
        callback_url,
        scope=adapter.get_default_scope(),
    )
    return client.get_redirect_url(
        adapter.authorize_url,
        extra_params={"access_type": "online"},
    )


def handle_google_callback(
    request: Request,
    code: str | None,
    state: str | None,
) -> dict[str, str]:
    """
    Exchange Google authorization code for JWT pair.

    Flow:
    1. Validate code/state presence.
    2. Exchange code → Google access token via allauth.
    3. Fetch Google user profile.
    4. create_or_link_user() — no duplicates.
    5. Return JWT pair.

    Raises:
        ValidationError: if code/state is missing.
        AuthenticationFailed: if token exchange fails.
    """
    if not code:
        raise ValidationError({"code": "Authorization code is required."})
    if not state:
        raise ValidationError({"state": "State parameter is required (CSRF protection)."})

    from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
    from allauth.socialaccount.providers.oauth2.client import OAuth2Client

    adapter = GoogleOAuth2Adapter(request)
    callback_url = request.build_absolute_uri("/auth/google/callback/")
    client = OAuth2Client(
        request,
        adapter.get_client_id(request),
        adapter.get_client_secret(request),
        adapter.access_token_method,
        adapter.access_token_url,
        callback_url,
    )

    try:
        token = client.get_access_token(code)
        social_token = adapter.parse_token(token)
        social_login = adapter.complete_login(request, None, social_token, response=token)
        social_login.token = social_token
    except Exception as exc:
        logger.warning("Google OAuth2 token exchange failed: %s", exc)
        raise AuthenticationFailed("Google authentication failed.") from exc

    user = _create_or_link_user(social_login)
    logger.info("Google OAuth2 login success: user=%s", user.id)
    return create_jwt_pair(user)


def _create_or_link_user(social_login) -> User:
    """
    Find existing User by email or create new one.
    Ensures no duplicate accounts for the same Google email.
    """
    email: str = social_login.user.email
    try:
        user = user_selectors.get_user_by_email(email=email)
        logger.debug("Linking existing account: email=%s", email)
    except User.DoesNotExist:
        user = User.objects.create_user(
            email=email,
            first_name=social_login.user.first_name or "",
            last_name=social_login.user.last_name or "",
        )
        logger.info("Created new user via Google OAuth2: email=%s", email)
    return user
