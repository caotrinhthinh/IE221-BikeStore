"""
apps/production/models.py — Production domain models.

Models:
    Category  — MPTT hierarchical product category tree
    Brand     — Bike manufacturer / brand
    Product   — Sellable item (belongs to Category + Brand)
    Stock     — Inventory level per (product, store) pair
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from apps.core.models import BaseModel


class Category(MPTTModel):
    """
    Hierarchical product category using django-mptt.

    Uses MPTT for efficient subtree queries without recursive SQL.
    version field supports cache key invalidation (category_tree:v{version}).
    """

    name = models.CharField(max_length=150, db_index=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name

    def bump_version(self) -> None:
        """Increment cache version — call this after any tree mutation."""
        Category.objects.filter(pk=self.pk).update(version=models.F("version") + 1)


class Brand(BaseModel):
    """Bike manufacturer or brand label."""

    name = models.CharField(max_length=150, unique=True, db_index=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self) -> str:
        return self.name


class Product(BaseModel):
    """
    A sellable item.

    DB indexes:
        - (category_id, list_price) — filter by category + price range
        - model_year indexed — filter current-year products
    """

    name = models.CharField(max_length=255, db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    model_year = models.PositiveSmallIntegerField(db_index=True)
    list_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=["category_id", "list_price"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.model_year})"


class Stock(BaseModel):
    """
    Inventory level for a specific Product at a specific Store.

    Constraint: unique_together (product, store) acts as composite PK semantics
    while keeping a UUID pk for BaseModel compatibility.

    quantity must be >= 0; enforced at DB level via CheckConstraint.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_entries"
    )
    # Circular import avoided by string reference; Store is in apps.sales
    store = models.ForeignKey(
        "sales.Store", on_delete=models.CASCADE, related_name="stock_entries"
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        unique_together = [("product", "store")]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name="stock_quantity_non_negative",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} @ {self.store}: {self.quantity}"
