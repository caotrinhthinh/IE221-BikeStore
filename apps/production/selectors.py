"""
apps/production/selectors.py — Read-only query functions for Production domain.

Rules:
    - NO business logic here — only DB reads.
    - Always use select_related / prefetch_related to prevent N+1.
    - Services and views import these; NEVER call .objects.* in views.
"""
from __future__ import annotations

from django.db.models import QuerySet

from .models import Brand, Category, Product, Stock


# ── Category ────────────────────────────────────────────────────────

def get_category_tree() -> QuerySet[Category]:
    """Return entire category tree ordered for MPTT rendering."""
    return Category.objects.all()


def get_category_by_slug(*, slug: str) -> Category:
    """Raises Category.DoesNotExist if not found."""
    return Category.objects.get(slug=slug)


# ── Brand ────────────────────────────────────────────────────────────

def get_brand_list() -> QuerySet[Brand]:
    return Brand.objects.all().order_by("name")


def get_brand_by_id(*, brand_id: object) -> Brand:
    """Raises Brand.DoesNotExist if not found."""
    return Brand.objects.get(pk=brand_id)


# ── Product ──────────────────────────────────────────────────────────

def get_product_by_id(*, product_id: object) -> Product:
    """Raises Product.DoesNotExist if not found."""
    return (
        Product.objects.select_related("brand", "category").get(pk=product_id)
    )


def get_products_with_stock(*, store_id: object | None = None) -> QuerySet[Product]:
    """
    Products annotated with stock for a given store.
    If store_id is None, returns all products with prefetched stock entries.
    """
    qs = Product.objects.select_related("brand", "category").prefetch_related(
        "stock_entries"
    )
    if store_id is not None:
        qs = qs.filter(stock_entries__store_id=store_id)
    return qs


def get_low_stock_products(*, threshold: int, store_id: object) -> QuerySet[Stock]:
    """
    Stock entries where quantity <= threshold for a given store.
    Ordered by quantity ascending so critical items come first.
    """
    return (
        Stock.objects.select_related("product", "store")
        .filter(store_id=store_id, quantity__lte=threshold)
        .order_by("quantity")
    )
