"""
apps/sales/selectors.py — Read-only query functions for sales domain.

Rule: All queryset logic lives here. Views MUST NOT call .objects. directly.
All queries use select_related / prefetch_related to prevent N+1.
"""

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    QuerySet,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from .models import Customer, Order, OrderItem, OrderStatus, Staff, Store


def _orders_base_queryset() -> QuerySet[Order]:
    """Base optimized queryset for order list/retrieve APIs."""
    line_total = ExpressionWrapper(
        F("items__quantity")
        * F("items__list_price")
        * (Value(1) - F("items__discount")),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    return (
        Order.objects.select_related("customer", "store", "staff")
        .prefetch_related("items__product", "items__product__brand")
        .annotate(
            total_amount=Coalesce(
                Sum(line_total),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            items_count=Count("items", distinct=True),
        )
    )


def get_all_stores() -> QuerySet[Store]:
    """Return all stores ordered by name."""
    return Store.objects.all().order_by("name")


def get_customer_by_user(user_id: str) -> Customer:
    """Return the Customer profile for a given User ID."""
    return Customer.objects.select_related("user").get(user_id=user_id)


def get_all_customers() -> QuerySet[Customer]:
    """Return all customers for admins."""
    return Customer.objects.select_related("user").order_by("last_name", "first_name")


def get_customers_for_user(user_id: str) -> QuerySet[Customer]:
    """Return the customer profile queryset for a user."""
    return Customer.objects.filter(user_id=user_id).select_related("user")


def get_staff_by_user(user_id: str) -> Staff:
    """Return the Staff profile for a given User ID."""
    return Staff.objects.select_related("user", "store", "manager").get(user_id=user_id)


def get_all_staff() -> QuerySet[Staff]:
    """Return all staff for admins."""
    return Staff.objects.select_related("user", "store", "manager").order_by(
        "last_name", "first_name"
    )


def get_staff_for_store(store_id: str) -> QuerySet[Staff]:
    """Return all staff for a store."""
    return (
        Staff.objects.filter(store_id=store_id)
        .select_related("user", "store", "manager")
        .order_by("last_name", "first_name")
    )


def get_no_staff() -> QuerySet[Staff]:
    """Return an empty staff queryset."""
    return Staff.objects.none()


def get_orders_for_customer(customer_id: str) -> QuerySet[Order]:
    """
    Return all orders for a specific customer.
    Pre-fetches order items and related products to avoid N+1.
    """
    return (
        _orders_base_queryset()
        .filter(customer_id=customer_id)
        .order_by("-order_date", "-created_at")
    )


def get_orders_for_store(store_id: str) -> QuerySet[Order]:
    """
    Return all orders placed at a specific store.
    Pre-fetches order items and related products to avoid N+1.
    """
    return (
        _orders_base_queryset()
        .filter(store_id=store_id)
        .order_by("-order_date", "-created_at")
    )


def get_all_orders() -> QuerySet[Order]:
    """Return all orders. Only for ADMIN role."""
    return _orders_base_queryset().order_by("-order_date", "-created_at")


def get_no_orders() -> QuerySet[Order]:
    """Return an empty order queryset."""
    return Order.objects.none()


def get_order_items(order_id: str) -> QuerySet[OrderItem]:
    """Return items for one order with product details."""
    return (
        OrderItem.objects.select_related(
            "product", "product__brand", "product__category"
        )
        .filter(order_id=order_id)
        .order_by("created_at")
    )


def get_pending_orders_older_than(days: int) -> QuerySet[Order]:
    """Return PENDING orders older than the given number of days (for cleanup task)."""
    from datetime import timedelta

    from django.utils import timezone

    cutoff = timezone.now().date() - timedelta(days=days)
    return Order.objects.filter(
        status=OrderStatus.PENDING,
        order_date__lt=cutoff,
    )
