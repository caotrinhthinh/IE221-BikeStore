"""
apps/production/services.py — Write operations for production domain.

Rule: All DB mutations go through services. Services are called by views,
NOT the other way around.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.exceptions import InsufficientStockError

from .cache import invalidate_product_catalog_for_store
from .models import Stock


def update_stock(*, product_id: str, store_id: str, quantity: int) -> Stock:
    """
    Directly set the stock quantity for a (product, store) pair.
    Creates the Stock entry if it doesn't exist yet.

    Args:
        product_id: UUID of the product.
        store_id: UUID of the store.
        quantity: New absolute stock quantity (must be >= 0).

    Returns:
        Updated Stock instance.
    """
    if quantity < 0:
        raise ValidationError("Stock quantity must be greater than or equal to 0.")

    stock, _ = Stock.objects.get_or_create(
        product_id=product_id,
        store_id=store_id,
        defaults={"quantity": 0},
    )
    stock.quantity = quantity
    stock.save(update_fields=["quantity", "updated_at"])
    invalidate_product_catalog_for_store(store_id=store_id)
    return stock


@transaction.atomic
def decrement_stock(*, product_id: str, store_id: str, quantity: int) -> Stock:
    """
    Atomically decrement stock quantity for a (product, store) pair.
    Uses select_for_update() to prevent race conditions.

    Raises:
        InsufficientStockError: if available stock < requested quantity.
    """
    try:
        stock = Stock.objects.select_for_update().get(
            product_id=product_id,
            store_id=store_id,
        )
    except Stock.DoesNotExist as exc:
        raise InsufficientStockError(
            product_id=product_id, requested=quantity, available=0
        ) from exc

    if stock.quantity < quantity:
        raise InsufficientStockError(
            product_id=product_id,
            requested=quantity,
            available=stock.quantity,
        )

    stock.quantity -= quantity
    stock.save(update_fields=["quantity", "updated_at"])
    invalidate_product_catalog_for_store(store_id=store_id)
    return stock


def check_availability(*, product_id: str, store_id: str, quantity: int) -> bool:
    """Return True when store stock can satisfy the requested quantity."""
    if quantity <= 0:
        return False
    return Stock.objects.filter(
        product_id=product_id,
        store_id=store_id,
        quantity__gte=quantity,
    ).exists()


def get_low_stock_products(*, threshold: int = 5):
    """Service wrapper for low-stock selector."""
    from .selectors import get_low_stock_products as _get_low_stock_products

    return _get_low_stock_products(threshold=threshold)
