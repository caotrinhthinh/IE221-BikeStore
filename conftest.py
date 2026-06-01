# conftest.py — project-wide pytest fixtures
import pytest
from allauth.account.models import EmailAddress
from rest_framework.test import APIClient

from apps.sales.models import Staff, Store
from apps.users.models import Role, User


def _verify_email(user: User) -> None:
    EmailAddress.objects.create(
        user=user,
        email=user.email,
        primary=True,
        verified=True,
    )


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def test_store(db) -> Store:
    return Store.objects.create(
        name="Test Store",
        email="test_store@bikestore.com",
    )


@pytest.fixture
def customer_user(db) -> User:
    user = User.objects.create_user(
        email="customer@example.com",
        password="Str0ng!Pass",
        role=Role.CUSTOMER,
    )
    _verify_email(user)
    return user


@pytest.fixture
def staff_user(db, test_store) -> User:
    user = User.objects.create_user(
        email="staff@example.com",
        password="Str0ng!Pass",
        role=Role.STAFF,
    )
    Staff.objects.create(
        user=user,
        store=test_store,
        first_name="Staff",
        last_name="User",
        email=user.email,
        active=True,
    )
    _verify_email(user)
    return user


@pytest.fixture
def manager_user(db, test_store) -> User:
    user = User.objects.create_user(
        email="manager@example.com",
        password="Str0ng!Pass",
        role=Role.STORE_MANAGER,
    )
    Staff.objects.create(
        user=user,
        store=test_store,
        first_name="Manager",
        last_name="User",
        email=user.email,
        active=True,
    )
    _verify_email(user)
    return user


@pytest.fixture
def admin_user(db) -> User:
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="Str0ng!Pass",
    )
    _verify_email(user)
    return user


@pytest.fixture
def auth_client(api_client: APIClient, customer_user: User) -> APIClient:
    """APIClient authenticated as customer."""
    api_client.force_authenticate(user=customer_user)
    return api_client


@pytest.fixture
def manager_client(api_client: APIClient, manager_user: User) -> APIClient:
    """APIClient authenticated as store manager."""
    api_client.force_authenticate(user=manager_user)
    return api_client


@pytest.fixture
def staff_client(api_client: APIClient, staff_user: User) -> APIClient:
    """APIClient authenticated as staff."""
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def admin_client(api_client: APIClient, admin_user: User) -> APIClient:
    """APIClient authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client
