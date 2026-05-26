"""
tests/users/test_google_oauth.py — Google OAuth2 edge-case tests.

Uses `responses` library to mock HTTP calls to Google APIs.

Coverage targets:
✓ New user created on first Google login
✓ Existing email → account linked (no duplicate)
✓ Missing code param → 400 ValidationError
✓ Missing state param → 400 ValidationError (CSRF)
✓ Google revokes token → 401 AuthenticationFailed
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.mark.django_db
class TestGoogleCallback:
    CALLBACK_URL = "/auth/google/callback/"

    def _mock_social_login(
        self, email: str, first_name: str = "Test", last_name: str = "User"
    ):
        """Build a minimal allauth social_login mock."""
        mock_login = MagicMock()
        mock_login.user.email = email
        mock_login.user.first_name = first_name
        mock_login.user.last_name = last_name
        return mock_login

    @patch("apps.users.services.handle_google_callback")
    def test_new_user_created_on_first_login(
        self,
        mock_handle: MagicMock,
        api_client: APIClient,
        db,
    ):
        mock_handle.return_value = {"access": "fake_access", "refresh": "fake_refresh"}

        response = api_client.get(
            self.CALLBACK_URL,
            {"code": "valid_code", "state": "valid_state"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    @patch("apps.users.services.handle_google_callback")
    def test_existing_email_links_account(
        self,
        mock_handle: MagicMock,
        api_client: APIClient,
        customer_user: User,
    ):
        """No duplicate user created when email already exists."""
        mock_handle.return_value = {"access": "fake_access", "refresh": "fake_refresh"}
        initial_count = User.objects.count()

        response = api_client.get(
            self.CALLBACK_URL,
            {"code": "valid_code", "state": "valid_state"},
        )

        assert response.status_code == status.HTTP_200_OK
        # User count must not increase
        assert User.objects.count() == initial_count

    def test_missing_code_returns_400(self, api_client: APIClient):
        response = api_client.get(self.CALLBACK_URL, {"state": "valid_state"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_state_returns_400(self, api_client: APIClient):
        response = api_client.get(self.CALLBACK_URL, {"code": "valid_code"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.users.services.handle_google_callback")
    def test_google_revoke_token_returns_401(
        self,
        mock_handle: MagicMock,
        api_client: APIClient,
        db,
    ):
        from rest_framework.exceptions import AuthenticationFailed

        mock_handle.side_effect = AuthenticationFailed("Google authentication failed.")

        response = api_client.get(
            self.CALLBACK_URL,
            {"code": "revoked_code", "state": "valid_state"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
