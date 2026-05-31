"""tests/users/test_registration.py — Integration tests for email-only registration."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Role, User


@pytest.mark.django_db
class TestUserRegistration:
    URL = reverse("rest_register")

    def test_registration_succeeds_with_valid_data(self, api_client: APIClient):
        payload = {
            "email": "new_registration@example.com",
            "password1": "Str0ng!Pass123",
            "password2": "Str0ng!Pass123",
            "first_name": "Nguyen",
            "last_name": "An",
        }

        response = api_client.post(self.URL, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data

        # Verify user model creation
        user = User.objects.get(email="new_registration@example.com")
        assert user.first_name == "Nguyen"
        assert user.last_name == "An"
        assert user.role == Role.CUSTOMER

    def test_registration_fails_when_passwords_do_not_match(
        self, api_client: APIClient
    ):
        payload = {
            "email": "mismatch@example.com",
            "password1": "Str0ng!Pass123",
            "password2": "DifferentPass123",
        }

        response = api_client.post(self.URL, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data
