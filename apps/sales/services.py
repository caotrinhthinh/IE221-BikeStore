"""
apps/sales/services.py — Business logic for the sales domain.

Rules:
- All mutations go through service functions (no logic in views or models).
- create_order is atomic: either all items + stock decrements succeed, or nothing.
- FSM transitions are validated via ORDER_STATUS_TRANSITIONS matrix.
"""

from __future__ import annotations

import dataclasses
import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import (
    InvalidStatusTransitionError,
    ServiceError,
)
from apps.production.services import decrement_stock

from .models import (
    ORDER_STATUS_TRANSITIONS,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    Staff,
    Store,
)

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class OrderLineInput:
    """Input DTO for a single order line (product + quantity + discount)."""

    product_id: uuid.UUID
    quantity: int
    discount: Decimal = Decimal("0")


@transaction.atomic
def create_order(
    *,
    customer_id: uuid.UUID,
    store_id: uuid.UUID,
    staff_id: Optional[uuid.UUID] = None,
    required_date: Optional[date] = None,
    lines: list[OrderLineInput],
) -> Order:
    """
    Create a new order with the given line items.

    Steps (all inside a single atomic transaction):
    1. Validate customer, store, staff exist.
    2. For each line: fetch product price, decrement stock (raises InsufficientStockError if not enough).
    3. Create Order.
    4. Create OrderItems.
    5. Trigger async confirmation email (non-blocking).

    Args:
        customer_id: UUID of the Customer.
        store_id: UUID of the Store.
        staff_id: Optional UUID of the Staff member handling the order.
        required_date: Optional date the customer needs the order by.
        lines: List of OrderLineInput with product_id, quantity, discount.

    Returns:
        The newly created Order instance (with items prefetched).

    Raises:
        Customer.DoesNotExist: if customer not found.
        Store.DoesNotExist: if store not found.
        InsufficientStockError: if any product doesn't have enough stock.
    """
    from apps.production.models import Product

    if not lines:
        raise ServiceError("An order must have at least one line item.")

    # Validate FK references upfront to get clear error messages
    customer = Customer.objects.get(pk=customer_id)
    store = Store.objects.get(pk=store_id)
    staff: Optional[Staff] = Staff.objects.get(pk=staff_id) if staff_id else None

    # Build a map of product_id -> Product to avoid per-line queries
    product_ids = [line.product_id for line in lines]
    products = Product.objects.in_bulk(product_ids)
    missing_product_ids = [
        str(product_id) for product_id in product_ids if product_id not in products
    ]
    if missing_product_ids:
        raise ServiceError(f"Unknown product IDs: {', '.join(missing_product_ids)}")

    # Decrement stock for each line item (raises InsufficientStockError on failure)
    for line in lines:
        decrement_stock(
            product_id=str(line.product_id),
            store_id=str(store_id),
            quantity=line.quantity,
        )

    # Create the Order
    order = Order.objects.create(
        customer=customer,
        store=store,
        staff=staff,
        status=OrderStatus.PENDING,
        order_date=timezone.now().date(),
        required_date=required_date,
    )

    # Create OrderItems — list price is snapshotted from the product at order time
    order_items = [
        OrderItem(
            order=order,
            product_id=line.product_id,
            quantity=line.quantity,
            list_price=products[line.product_id].list_price,
            discount=line.discount,
        )
        for line in lines
    ]
    OrderItem.objects.bulk_create(order_items)

    # Trigger async order confirmation email only after the DB transaction commits.
    transaction.on_commit(lambda: _enqueue_order_confirmation(order_id=str(order.pk)))

    # Reload with all related data for the response
    return (
        Order.objects.select_related("customer", "store", "staff")
        .prefetch_related("items__product")
        .get(pk=order.pk)
    )


def _enqueue_order_confirmation(*, order_id: str) -> None:
    """Best-effort Celery enqueue that never rolls back a successful order."""
    from apps.sales.tasks import send_order_confirmation

    try:
        send_order_confirmation.delay(order_id)
    except Exception as exc:
        logger.warning("Could not enqueue order confirmation for %s: %s", order_id, exc)


def _transition_order_status(order_id: uuid.UUID, target_status: str) -> Order:
    """
    Internal helper: validates and applies an FSM status transition.

    Raises:
        Order.DoesNotExist: if order not found.
        InvalidStatusTransitionError: if the transition is not allowed.
    """
    order = Order.objects.select_for_update().get(pk=order_id)
    allowed = ORDER_STATUS_TRANSITIONS.get(order.status, [])

    if target_status not in allowed:
        raise InvalidStatusTransitionError(current=order.status, target=target_status)

    order.status = target_status

    if target_status == OrderStatus.COMPLETED:
        order.shipped_date = timezone.now().date()

    order.save(update_fields=["status", "shipped_date", "updated_at"])
    return order


@transaction.atomic
def ship_order(*, order_id: uuid.UUID) -> Order:
    """
    Mark an order as COMPLETED (shipped).

    If the order is still PENDING, the service advances it through PROCESSING
    first so every persisted transition remains valid under the FSM matrix.

    Returns:
        Updated Order instance.
    """
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PROCESSING
        order.save(update_fields=["status", "updated_at"])

    return _transition_order_status(order_id, OrderStatus.COMPLETED)


@transaction.atomic
def cancel_order(*, order_id: uuid.UUID) -> Order:
    """
    Reject/cancel an order.

    Valid from PENDING or PROCESSING.

    Returns:
        Updated Order instance.
    """
    return _transition_order_status(order_id, OrderStatus.REJECTED)


@transaction.atomic
def update_order_status(*, order_id: uuid.UUID, new_status: str) -> Order:
    """
    Apply a generic FSM transition to the given target status.

    Raises:
        InvalidStatusTransitionError: if the transition is not in the FSM matrix.
    """
    return _transition_order_status(order_id, new_status)


def update_stock(*, product_id: str, store_id: str, quantity: int) -> None:
    """
    Proxy to production.services.update_stock — used by views that import from sales.services.
    """
    from apps.production.services import update_stock as _update_stock

    _update_stock(product_id=product_id, store_id=store_id, quantity=quantity)
