"""
apps/core/models.py — shared abstract base model and reusable field mixins.

Rules:
- Every model in this project MUST extend BaseModel.
- UUID primary key prevents integer enumeration attacks.
- created_at / updated_at are indexed for efficient time-range queries.

Mixins (all abstract — add no extra DB table):
- PersonMixin   : first_name, last_name, full_name property
- ContactMixin  : email, phone
- AddressMixin  : street, city, state, zip_code
"""

import uuid

from django.db import models


class BaseModel(models.Model):
    """Abstract base with UUID pk + audit timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class PersonMixin(models.Model):
    """
    Abstract mixin for any entity that represents a person.

    Provides: first_name, last_name, full_name (property).
    Used by: User, Customer, Staff.
    """

    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")

    class Meta:
        abstract = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class ContactMixin(models.Model):
    """
    Abstract mixin for entities with contact information.

    Provides: email, phone.
    Used by: User, Customer, Staff, Store.
    """

    email = models.EmailField(blank=True, default="", db_index=True)
    phone = models.CharField(max_length=25, blank=True, default="")

    class Meta:
        abstract = True


class AddressMixin(models.Model):
    """
    Abstract mixin for entities with a physical address.

    Provides: street, city, state, zip_code.
    Used by: Customer, Store.
    """

    street = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    zip_code = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        abstract = True
