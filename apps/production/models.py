"""
apps/production/models.py — Production domain models.

Tables: categories, brands, products, stocks
Follows ERD from IE221 requirements.
"""

from django.core.validators import MinValueValidator
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from apps.core.models import BaseModel


class Category(MPTTModel, BaseModel):
    """
    Product category with tree structure (supports nested categories).
    Uses django-mptt for efficient tree traversal.

    DB table: categories
    """

    name = models.CharField(max_length=255, unique=True, db_index=True)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        db_column="parent_id",
    )
    # version is used as part of the cache key for the category tree.
    # Increment this whenever the tree changes to bust the cache.
    version = models.PositiveIntegerField(default=1)

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        # Override BaseModel ordering to use MPTT tree_id ordering
        ordering = ["tree_id", "lft"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Bump version on every save to invalidate the category-tree cache."""
        self.version += 1
        super().save(*args, **kwargs)


class Brand(BaseModel):
    """
    Bike brand / manufacturer.

    DB table: brands
    """

    name = models.CharField(max_length=255, unique=True, db_index=True)

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(BaseModel):
    """
    A bike product available in the catalogue.

    DB table: products
    Composite index on (category, list_price) for filtered listing.
    """

    name = models.CharField(max_length=255, db_index=True)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products",
        db_column="brand_id",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        db_column="category_id",
    )
    model_year = models.PositiveSmallIntegerField()
    list_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        db_index=True,
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["category", "list_price"], name="idx_product_cat_price"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.model_year})"


class Stock(BaseModel):
    """
    Inventory level of a product at a specific store.

    DB table: stocks
    Composite unique constraint: (store, product).
    The 'store' FK is forward-declared using a string to avoid circular imports.
    """

    store = models.ForeignKey(
        "sales.Store",
        on_delete=models.CASCADE,
        related_name="stocks",
        db_column="store_id",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stocks",
        db_column="product_id",
    )
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        # Composite unique constraint matching ERD composite PK (store_id, product_id)
        constraints = [
            models.UniqueConstraint(
                fields=["store", "product"],
                name="unique_stock_store_product",
            )
        ]
        indexes = [
            models.Index(fields=["store", "product"], name="idx_stock_store_product"),
        ]

    def __str__(self) -> str:
        return f"Stock({self.store_id}, {self.product_id}) = {self.quantity}"
