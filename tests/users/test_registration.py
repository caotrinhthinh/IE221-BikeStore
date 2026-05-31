"""tests/users/test_registration.py — Integration tests for email-only registration."""

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Role, User


@pytest.mark.django_db
class TestUserRegistration:
    URL_REGISTER = reverse("rest_register")
    URL_RESEND_EMAIL = reverse("rest_resend_email")

    def test_registration_succeeds_with_valid_data(self, api_client: APIClient):
        # Clear outbox before sending
        mail.outbox.clear()

        payload = {
            "email": "new_registration@example.com",
            "password1": "Str0ng!Pass123",
            "password2": "Str0ng!Pass123",
            "first_name": "Nguyen",
            "last_name": "An",
        }

        response = api_client.post(self.URL_REGISTER, payload)

        # Under mandatory email verification, should return 201 with detail message and no JWT tokens
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {"detail": "Verification e-mail sent."}

        # Verify email is sent
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["new_registration@example.com"]

        # Verify user model creation in DB (unverified by default)
        user = User.objects.get(email="new_registration@example.com")
        assert user.first_name == "Nguyen"
        assert user.last_name == "An"
        assert user.role == Role.CUSTOMER

        # Verify EmailAddress record exists but verified is False
        email_addr = EmailAddress.objects.get(user=user, email=user.email)
        assert email_addr.verified is False

    def test_registration_fails_when_passwords_do_not_match(
        self, api_client: APIClient
    ):
        payload = {
            "email": "mismatch@example.com",
            "password1": "Str0ng!Pass123",
            "password2": "DifferentPass123",
        }

        response = api_client.post(self.URL_REGISTER, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data

    def test_resend_verification_email_succeeds(self, api_client: APIClient):
        # 1. Create a registered but unverified user
        user = User.objects.create_user(
            email="unverified_resend@example.com", password="Str0ng!Pass123"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=False
        )

        mail.outbox.clear()

        # 2. Trigger resend-email
        payload = {"email": "unverified_resend@example.com"}
        response = api_client.post(self.URL_RESEND_EMAIL, payload)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"detail": "ok"}

        # 3. Verify email is sent
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["unverified_resend@example.com"]
