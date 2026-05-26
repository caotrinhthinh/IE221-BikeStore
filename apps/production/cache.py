"""apps/production/cache.py — Caching layer for production data."""

from __future__ import annotations

from contextlib import suppress

from django.core.cache import cache
from django.db.models import Max

from .models import Category

PRODUCT_CATALOG_TTL_SECONDS = 300
CATEGORY_TREE_TTL_SECONDS = 3600


def get_product_catalog_cache_key(*, store_id: str) -> str:
    """Return the cache key required by the sprint plan."""
    return f"product_catalog:store:{store_id}"


def serialize_product_for_catalog(product) -> dict:
    """Serialize a product plus its prefetched store stock for cache storage."""
    stock_quantity = 0
    store_stocks = getattr(product, "store_stocks", [])
    if store_stocks:
        stock_quantity = store_stocks[0].quantity

    return {
        "id": str(product.id),
        "name": product.name,
        "brand": {"id": str(product.brand_id), "name": product.brand.name},
        "category": {"id": str(product.category_id), "name": product.category.name},
        "model_year": product.model_year,
        "list_price": str(product.list_price),
        "description": product.description,
        "stock_quantity": stock_quantity,
    }


def get_product_catalog_for_store(*, store_id: str) -> list[dict]:
    """Get product catalog for a store, cached for five minutes."""
    from .selectors import get_products_with_stock

    key = get_product_catalog_cache_key(store_id=store_id)
    try:
        cached = cache.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return cached

    catalog = [
        serialize_product_for_catalog(product)
        for product in get_products_with_stock(store_id=store_id)
    ]
    with suppress(Exception):
        cache.set(key, catalog, timeout=PRODUCT_CATALOG_TTL_SECONDS)
    return catalog


def invalidate_product_catalog_for_store(*, store_id: str) -> None:
    """Invalidate catalog cache after stock changes."""
    with suppress(Exception):
        cache.delete(get_product_catalog_cache_key(store_id=store_id))


def get_category_tree_cache_key() -> str:
    """Generate a category tree key that changes when any category is updated."""
    latest_update = Category.objects.aggregate(latest=Max("updated_at"))["latest"]
    version = latest_update.timestamp() if latest_update else 1
    return f"category_tree:v{version}"


def get_cached_category_tree() -> list[Category]:
    """Return category tree rows cached for one hour."""
    from .selectors import get_category_tree

    key = get_category_tree_cache_key()
    try:
        tree = cache.get(key)
    except Exception:
        tree = None

    if tree is None:
        tree = list(get_category_tree())
        with suppress(Exception):
            cache.set(key, tree, timeout=CATEGORY_TREE_TTL_SECONDS)

    return tree
