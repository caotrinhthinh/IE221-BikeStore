"""
apps/users/selectors.py — read-only query functions.

Rules:
- NO business logic here — only DB reads.
- Views and services use selectors; NEVER call User.objects.* directly in views.
"""
from .models import User


def get_user_by_email(*, email: str) -> User:
    """Raises User.DoesNotExist if not found."""
    return User.objects.get(email=email)


def get_active_users():
    return User.objects.filter(is_active=True)


def get_users_by_role(*, role: str):
    return User.objects.filter(role=role, is_active=True)
