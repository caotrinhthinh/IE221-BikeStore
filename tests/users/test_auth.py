"""
tests/users/test_auth.py — JWT Auth integration tests.

Coverage targets (Sprint 1):
✓ login → access token issued
✓ access token → authenticated request succeeds
✓ refresh token → new access token
✓ logout → refresh token blacklisted
✓ blacklisted token cannot refresh again
✓ wrong password → 401
✓ inactive user → 401
✓ all 4 role combinations can login
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, Role


@pytest.mark.django_db
class TestJWTLogin:
    def test_login_returns_tokens(self, api_client: APIClient, customer_user: User):
        url = reverse("auth-login")
        response = api_client.post(url, {"email": "customer@example.com", "password": "Str0ng!Pass"})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_wrong_password_returns_401(self, api_client: APIClient, customer_user: User):
        url = reverse("auth-login")
        response = api_client.post(url, {"email": "customer@example.com", "password": "WrongPass"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_cannot_login(self, api_client: APIClient, db):
        User.objects.create_user(
            email="inactive@example.com",
            password="Str0ng!Pass",
            is_active=False,
        )
        url = reverse("auth-login")
        response = api_client.post(url, {"email": "inactive@example.com", "password": "Str0ng!Pass"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("role", [Role.CUSTOMER, Role.STAFF, Role.STORE_MANAGER, Role.ADMIN])
    def test_all_roles_can_login(self, api_client: APIClient, db, role: str):
        email = f"{role}@example.com"
        User.objects.create_user(email=email, password="Str0ng!Pass", role=role)
        url = reverse("auth-login")
        response = api_client.post(url, {"email": email, "password": "Str0ng!Pass"})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


@pytest.mark.django_db
class TestJWTRefresh:
    def _login(self, api_client, email="customer@example.com", password="Str0ng!Pass"):
        url = reverse("auth-login")
        return api_client.post(url, {"email": email, "password": password})

    def test_refresh_returns_new_access_token(self, api_client: APIClient, customer_user: User):
        login_resp = self._login(api_client)
        refresh = login_resp.data["refresh"]

        url = reverse("auth-token-refresh")
        response = api_client.post(url, {"refresh": refresh})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        # New access token should differ from old
        assert response.data["access"] != login_resp.data["access"]

    def test_invalid_refresh_token_returns_401(self, api_client: APIClient):
        url = reverse("auth-token-refresh")
        response = api_client.post(url, {"refresh": "not.a.valid.token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestJWTLogout:
    def _login(self, api_client, email="customer@example.com", password="Str0ng!Pass"):
        url = reverse("auth-login")
        resp = api_client.post(url, {"email": email, "password": password})
        return resp.data

    def test_logout_blacklists_refresh_token(self, api_client: APIClient, customer_user: User):
        tokens = self._login(api_client)
        access = tokens["access"]
        refresh = tokens["refresh"]

        # Authenticate and logout
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_url = reverse("auth-logout")
        logout_resp = api_client.post(logout_url, {"refresh": refresh})
        assert logout_resp.status_code == status.HTTP_200_OK

        # Try to refresh with blacklisted token → must fail
        refresh_url = reverse("auth-token-refresh")
        refresh_resp = api_client.post(refresh_url, {"refresh": refresh})
        assert refresh_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCurrentUserEndpoint:
    def test_me_returns_user_data(self, auth_client: APIClient, customer_user: User):
        url = reverse("auth-me")
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == customer_user.email
        assert response.data["role"] == Role.CUSTOMER

    def test_me_requires_authentication(self, api_client: APIClient):
        url = reverse("auth-me")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
