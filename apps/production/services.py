"""
apps/production/services.py — Write operations for production domain.

Rule: All DB mutations go through services. Services are called by views,
NOT the other way around.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.exceptions import InsufficientStockError

from .cache import invalidate_product_catalog_for_store
from .models import Brand, Category, Product, Stock

# ── Category ──────────────────────────────────────────────────────────────────


def create_category(*, name: str, parent=None) -> Category:
    """Create a new category, optionally nested under a parent."""
    return Category.objects.create(name=name, parent=parent)


def update_category(
    *, category: Category, name: str | None = None, parent=None
) -> Category:
    """Update mutable fields on an existing category."""
    if name is not None:
        category.name = name
    if parent is not None:
        category.parent = parent
    category.save()
    return category


def delete_category(*, category: Category) -> None:
    """Delete a category. Raises ValueError if it has children."""
    if category.get_children().exists():
        raise ValueError("Cannot delete a category that has subcategories.")
    category.delete()


# ── Brand ─────────────────────────────────────────────────────────────────────


def create_brand(*, name: str) -> Brand:
    """Create a new brand."""
    return Brand.objects.create(name=name)


def update_brand(*, brand: Brand, name: str) -> Brand:
    """Update an existing brand."""
    brand.name = name
    brand.save(update_fields=["name", "updated_at"])
    return brand


def delete_brand(*, brand: Brand) -> None:
    """Delete a brand. Raises ValueError if products are linked."""
    if brand.products.exists():
        raise ValueError("Cannot delete a brand that has associated products.")
    brand.delete()


# ── Product ───────────────────────────────────────────────────────────────────


def create_product(
    *,
    name: str,
    brand: Brand,
    category: Category,
    model_year: int,
    list_price,
    description: str = "",
) -> Product:
    """Create a new product."""
    return Product.objects.create(
        name=name,
        brand=brand,
        category=category,
        model_year=model_year,
        list_price=list_price,
        description=description,
    )


def update_product(*, product: Product, **kwargs) -> Product:
    """Update mutable fields on an existing product."""
    for field, value in kwargs.items():
        setattr(product, field, value)
    product.save()
    return product


def delete_product(*, product: Product) -> None:
    """Delete a product. Raises ValueError if it has active order items."""
    if product.order_items.exists():
        raise ValueError("Cannot delete a product that is referenced in orders.")
    product.delete()


# ── Stock ─────────────────────────────────────────────────────────────────────


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


def create_stock(*, product_id: str, store_id: str, quantity: int) -> Stock:
    """
    Create a new Stock entry for a (product, store) pair.

    Raises:
        ValidationError: if quantity < 0 or if a stock entry already exists.
    """
    if quantity < 0:
        raise ValidationError("Stock quantity must be greater than or equal to 0.")
    if Stock.objects.filter(product_id=product_id, store_id=store_id).exists():
        raise ValidationError(
            "A stock entry for this product and store already exists. Use update instead."
        )
    stock = Stock.objects.create(
        product_id=product_id, store_id=store_id, quantity=quantity
    )
    invalidate_product_catalog_for_store(store_id=store_id)
    return stock


def delete_stock(*, stock: Stock) -> None:
    """Delete a stock entry and invalidate the store's product catalog cache."""
    store_id = str(stock.store_id)
    stock.delete()
    invalidate_product_catalog_for_store(store_id=store_id)


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
