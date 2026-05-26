"""
apps/production/selectors.py — Read-only query functions for production domain.

Rule: All queryset logic lives here. Views MUST NOT call .objects. directly.
All queries use select_related / prefetch_related to prevent N+1.
"""

from django.db.models import Avg, Count, Max, Min, Prefetch, Q, QuerySet

from .models import Brand, Category, Product, Stock


def get_category_tree() -> QuerySet[Category]:
    """
    Return ALL categories as a flat queryset ordered by MPTT tree structure.
    Use with MPTT's `cache_tree_children` for nested rendering.
    """
    return Category.objects.all().order_by("tree_id", "lft")


def get_brand_list() -> QuerySet[Brand]:
    """Return all brands ordered alphabetically."""
    return Brand.objects.all().order_by("name")


def get_product_list() -> QuerySet[Product]:
    """
    Return all products with related brand and category pre-fetched.
    Use as base queryset — callers may filter further.
    """
    return Product.objects.select_related("brand", "category").order_by("-created_at")


def get_products_with_stock(store_id: str) -> QuerySet[Product]:
    """
    Return products with their stock quantities for a specific store.
    Prefetch only the Stock row for the given store to avoid N+1.
    """
    store_stock_qs = Stock.objects.filter(store_id=store_id)
    return (
        Product.objects.select_related("brand", "category")
        .prefetch_related(
            Prefetch("stocks", queryset=store_stock_qs, to_attr="store_stocks")
        )
        .order_by("-created_at")
    )


def get_stock_for_store(store_id: str) -> QuerySet[Stock]:
    """Return all stock entries for a given store with product details."""
    return Stock.objects.select_related(
        "store", "product", "product__brand", "product__category"
    ).filter(store_id=store_id)


def get_all_stock() -> QuerySet[Stock]:
    """Return all stock entries with store/product details for admins."""
    return Stock.objects.select_related(
        "store", "product", "product__brand", "product__category"
    ).order_by("store__name", "product__name")


def get_no_stock() -> QuerySet[Stock]:
    """Return an empty stock queryset."""
    return Stock.objects.none()


def get_low_stock_products(threshold: int = 5) -> QuerySet[Stock]:
    """Return stock entries where quantity is at or below the threshold."""
    return (
        Stock.objects.select_related("store", "product", "product__brand")
        .filter(quantity__lte=threshold)
        .order_by("quantity")
    )


def search_products(
    *,
    query: str,
    brand_id: str | None = None,
    min_price: str | None = None,
    max_price: str | None = None,
) -> QuerySet[Product]:
    """Database-backed product search for local development/demo."""
    queryset = get_product_list().filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(brand__name__icontains=query)
        | Q(category__name__icontains=query)
    )
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)
    if min_price:
        queryset = queryset.filter(list_price__gte=min_price)
    if max_price:
        queryset = queryset.filter(list_price__lte=max_price)
    return queryset


def get_product_facets(queryset: QuerySet[Product]) -> dict:
    """Return lightweight facets for product search results."""
    return {
        "brands": list(
            queryset.values("brand_id", "brand__name")
            .annotate(count=Count("id"))
            .order_by("brand__name")
        ),
        "price": queryset.aggregate(
            min=Min("list_price"),
            max=Max("list_price"),
            avg=Avg("list_price"),
        ),
    }
