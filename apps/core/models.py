"""
apps/core/models.py — shared abstract base model.

Rules:
- Every model in this project MUST extend BaseModel.
- UUID primary key prevents integer enumeration attacks.
- created_at / updated_at are indexed for efficient time-range queries.
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
