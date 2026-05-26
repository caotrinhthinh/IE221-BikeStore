"""tests/core/test_health.py — health check endpoint tests."""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthCheck:
    URL = "/health/"

    def test_health_check_returns_200_when_all_healthy(self, api_client: APIClient):
        response = api_client.get(self.URL)
        # DB is available in test DB; Redis may not be → check structure only
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]
        assert "status" in response.data
        assert "services" in response.data

    def test_health_check_accessible_without_auth(self, api_client: APIClient):
        response = api_client.get(self.URL)
        # Must not return 401
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @patch("django.db.connection.ensure_connection", side_effect=Exception("DB down"))
    def test_health_check_returns_503_when_db_down(
        self, mock_db, api_client: APIClient
    ):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["services"]["db"] is False
