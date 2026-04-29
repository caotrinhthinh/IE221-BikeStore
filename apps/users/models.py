"""
apps/users/models.py — Custom User model.

⚠️  CRITICAL RULE: This model MUST be defined before the first migration.
Changing AUTH_USER_MODEL after migrations exist is extremely painful.

Design decisions:
- Extends AbstractBaseUser (not AbstractUser) for full control.
- Email is the login identifier, no username field.
- Role enum stored as CharField for readability in DB queries.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid


class Role(models.TextChoices):
    """
    Role hierarchy (least → most privileged):
    CUSTOMER < STAFF < STORE_MANAGER < ADMIN
    """
    CUSTOMER = "customer", "Customer"
    STAFF = "staff", "Staff"
    STORE_MANAGER = "store_manager", "Store Manager"
    ADMIN = "admin", "Admin"


class UserManager(BaseUserManager["User"]):
    """Custom manager — email-based, no username."""

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields,
    ) -> "User":
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user: User = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields) -> "User":
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Project-wide User.

    Fields:
        email       — login identifier (unique)
        role        — RBAC role (see Role enum)
        is_active   — soft-delete flag
        is_staff    — access to Django admin
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email
