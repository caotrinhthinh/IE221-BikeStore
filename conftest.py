# conftest.py — project-wide pytest fixtures
import pytest
from rest_framework.test import APIClient

from apps.users.models import Role, User


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def customer_user(db) -> User:
    return User.objects.create_user(
        email="customer@example.com",
        password="Str0ng!Pass",
        role=Role.CUSTOMER,
    )


@pytest.fixture
def staff_user(db) -> User:
    return User.objects.create_user(
        email="staff@example.com",
        password="Str0ng!Pass",
        role=Role.STAFF,
    )


@pytest.fixture
def manager_user(db) -> User:
    return User.objects.create_user(
        email="manager@example.com",
        password="Str0ng!Pass",
        role=Role.STORE_MANAGER,
    )


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_superuser(
        email="admin@example.com",
        password="Str0ng!Pass",
    )


@pytest.fixture
def auth_client(api_client: APIClient, customer_user: User) -> APIClient:
    """APIClient authenticated as customer."""
    api_client.force_authenticate(user=customer_user)
    return api_client


@pytest.fixture
def admin_client(api_client: APIClient, admin_user: User) -> APIClient:
    """APIClient authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client
