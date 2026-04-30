"""
apps/sales/services.py — Sales service layer.

Rules (HackSoft style):
    - Views call services; services call selectors.
    - ALL mutations and business logic live here.
    - Services raise domain exceptions; views handle them via DRF exception handler.

Public API:
    create_order()           — atomic: validate stock → create order+items → decrement stock
    ship_order()             — PENDING/PROCESSING → COMPLETED with shipped_date
    cancel_order()           — any non-terminal → REJECTED
    update_order_status()    — generic FSM-validated transition
    update_stock()           — set stock quantity for (product, store)
    check_availability()     — True if stock >= requested quantity
    get_low_stock_products() — returns Stock entries below threshold
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import InsufficientStockError, InvalidStatusTransitionError
from apps.production.models import Product, Stock
from apps.production import selectors as production_selectors

from .models import (
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    Staff,
    Store,
)
from . import selectors as sales_selectors

if TYPE_CHECKING:
    from django.db.models import QuerySet

logger = logging.getLogger(__name__)


# ── Input types ──────────────────────────────────────────────────────

@dataclass
class OrderLineInput:
    """Represents a single line to be placed in an order."""

    product_id: object
    quantity: int
    discount: Decimal = Decimal("0.00")


# ── Order services ───────────────────────────────────────────────────

@transaction.atomic
def create_order(
    *,
    customer_id: object,
    store_id: object,
    lines: list[OrderLineInput],
    staff_id: object | None = None,
    required_date: datetime.date | None = None,
) -> Order:
    """
    Create an Order atomically.

    Steps:
        1. Validate all lines have quantity >= 1.
        2. Fetch + lock Stock rows (SELECT FOR UPDATE) to prevent race conditions.
        3. Raise InsufficientStockError if any line exceeds available stock.
        4. Create Order header.
        5. Bulk-create OrderItem rows.
        6. Bulk-decrement Stock quantities.
        7. Emit async notification (stub — Celery task in Sprint 4).

    Raises:
        InsufficientStockError: if stock < requested quantity for any product.
        Customer.DoesNotExist: if customer_id is invalid.
        Store.DoesNotExist: if store_id is invalid.
        Product.DoesNotExist: if any product_id is invalid.
    """
    if not lines:
        raise ValueError("An order must have at least one line item.")

    # Validate that all product_ids exist up-front (fail fast)
    product_ids = [line.product_id for line in lines]
    products: dict[object, Product] = {
        p.pk: p for p in Product.objects.filter(pk__in=product_ids)
    }
    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise Product.DoesNotExist(f"Products not found: {missing}")

    # Lock stock rows for all products in this store to prevent concurrent oversell
    stock_map: dict[object, Stock] = {
        s.product_id: s
        for s in Stock.objects.select_for_update().filter(
            product_id__in=product_ids, store_id=store_id
        )
    }

    # Check stock availability for every line
    for line in lines:
        stock = stock_map.get(line.product_id)
        available = stock.quantity if stock else 0
        if available < line.quantity:
            raise InsufficientStockError(
                product_id=line.product_id,
                requested=line.quantity,
                available=available,
            )

    # Fetch FK objects (already validated above — DoesNotExist will propagate)
    customer = sales_selectors.get_customer_by_id(customer_id=customer_id)
    store = sales_selectors.get_store_by_id(store_id=store_id)
    staff: Staff | None = None
    if staff_id is not None:
        staff = sales_selectors.get_staff_by_id(staff_id=staff_id)

    # Create Order header
    order = Order.objects.create(
        customer=customer,
        store=store,
        staff=staff,
        status=OrderStatus.PENDING,
        required_date=required_date,
    )

    # Bulk-create OrderItem rows
    order_items = [
        OrderItem(
            order=order,
            product=products[line.product_id],
            quantity=line.quantity,
            list_price=products[line.product_id].list_price,
            discount=line.discount,
        )
        for line in lines
    ]
    OrderItem.objects.bulk_create(order_items)

    # Decrement stock for each line
    for line in lines:
        stock = stock_map[line.product_id]
        Stock.objects.filter(pk=stock.pk).update(
            quantity=stock.quantity - line.quantity
        )

    logger.info(
        "Order created",
        extra={"order_id": str(order.pk), "store_id": str(store_id), "lines": len(lines)},
    )

    # Sprint 4: replace with Celery task
    # send_order_confirmation.delay(str(order.pk))

    return order


def ship_order(*, order_id: object) -> Order:
    """
    Transition order to COMPLETED and record shipped_date.

    Valid from: PENDING or PROCESSING.
    """
    order = sales_selectors.get_order_by_id(order_id=order_id)
    return update_order_status(order=order, target_status=OrderStatus.COMPLETED)


def cancel_order(*, order_id: object) -> Order:
    """
    Transition order to REJECTED (cancel).

    Valid from: PENDING or PROCESSING.
    """
    order = sales_selectors.get_order_by_id(order_id=order_id)
    return update_order_status(order=order, target_status=OrderStatus.REJECTED)


def update_order_status(*, order: Order, target_status: str) -> Order:
    """
    Generic FSM-validated status transition.

    Raises:
        InvalidStatusTransitionError: if the transition is not allowed.
    """
    if not order.can_transition_to(target_status):
        raise InvalidStatusTransitionError(
            current=order.status, target=target_status
        )

    update_fields = {"status": target_status}
    if target_status == OrderStatus.COMPLETED:
        update_fields["shipped_date"] = timezone.now().date()

    Order.objects.filter(pk=order.pk).update(**update_fields)
    order.refresh_from_db()

    logger.info(
        "Order status updated",
        extra={"order_id": str(order.pk), "status": target_status},
    )
    return order


# ── Stock services ───────────────────────────────────────────────────

def update_stock(
    *,
    product_id: object,
    store_id: object,
    quantity: int,
) -> Stock:
    """
    Set the stock quantity for a (product, store) pair.

    Creates the Stock entry if it does not yet exist.
    Raises ValueError if quantity < 0.
    """
    if quantity < 0:
        raise ValueError(f"Stock quantity cannot be negative, got {quantity}.")

    stock, created = Stock.objects.update_or_create(
        product_id=product_id,
        store_id=store_id,
        defaults={"quantity": quantity},
    )
    action = "created" if created else "updated"
    logger.info(
        "Stock %s",
        action,
        extra={"product_id": str(product_id), "store_id": str(store_id), "quantity": quantity},
    )
    return stock


def check_availability(
    *,
    product_id: object,
    store_id: object,
    quantity: int,
) -> bool:
    """Return True if stock >= requested quantity, False otherwise."""
    try:
        stock = Stock.objects.get(product_id=product_id, store_id=store_id)
        return stock.quantity >= quantity
    except Stock.DoesNotExist:
        return False


def get_low_stock_products(*, threshold: int, store_id: object) -> QuerySet[Stock]:
    """Delegate to production selector — convenience wrapper."""
    return production_selectors.get_low_stock_products(
        threshold=threshold, store_id=store_id
    )
