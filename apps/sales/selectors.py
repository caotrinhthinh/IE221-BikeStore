"""
apps/sales/selectors.py — Read-only query functions for Sales domain.

Rules:
    - NO business logic here — only DB reads.
    - Always use select_related / prefetch_related to prevent N+1.
    - Services and views import these; NEVER call .objects.* in views.
"""
from __future__ import annotations

from django.db.models import QuerySet

from .models import Customer, Order, OrderStatus, Staff, Store


# ── Store ────────────────────────────────────────────────────────────

def get_store_by_id(*, store_id: object) -> Store:
    """Raises Store.DoesNotExist if not found."""
    return Store.objects.get(pk=store_id)


def get_all_stores() -> QuerySet[Store]:
    return Store.objects.all().order_by("name")


# ── Customer ─────────────────────────────────────────────────────────

def get_customer_by_id(*, customer_id: object) -> Customer:
    """Raises Customer.DoesNotExist if not found."""
    return Customer.objects.select_related("user").get(pk=customer_id)


def get_customer_by_email(*, email: str) -> Customer:
    """Raises Customer.DoesNotExist if not found."""
    return Customer.objects.select_related("user").get(email=email)


# ── Staff ────────────────────────────────────────────────────────────

def get_staff_by_id(*, staff_id: object) -> Staff:
    """Raises Staff.DoesNotExist if not found."""
    return Staff.objects.select_related("user", "store", "manager").get(pk=staff_id)


def get_staff_for_store(*, store_id: object) -> QuerySet[Staff]:
    return (
        Staff.objects.select_related("user", "manager")
        .filter(store_id=store_id, active=True)
        .order_by("last_name")
    )


# ── Order ────────────────────────────────────────────────────────────

def get_order_by_id(*, order_id: object) -> Order:
    """Raises Order.DoesNotExist if not found."""
    return (
        Order.objects.select_related("customer", "store", "staff")
        .prefetch_related("items__product")
        .get(pk=order_id)
    )


def get_orders_for_store(
    *,
    store_id: object,
    status: str | None = None,
) -> QuerySet[Order]:
    """
    All orders for a store, optionally filtered by status.
    Indexed path: uses (store_id, status) composite index.
    """
    qs = (
        Order.objects.select_related("customer", "staff")
        .filter(store_id=store_id)
        .order_by("-order_date", "-created_at")
    )
    if status is not None:
        qs = qs.filter(status=status)
    return qs


def get_orders_for_customer(*, customer_id: object) -> QuerySet[Order]:
    """
    All orders for a customer.
    Uses (customer_id, order_date) composite index.
    """
    return (
        Order.objects.select_related("store", "staff")
        .filter(customer_id=customer_id)
        .order_by("-order_date")
    )


def get_pending_orders_older_than(*, days: int) -> QuerySet[Order]:
    """Return PENDING orders older than `days` days — used by cleanup task."""
    from django.utils import timezone
    import datetime

    cutoff = timezone.now().date() - datetime.timedelta(days=days)
    return Order.objects.filter(
        status=OrderStatus.PENDING,
        order_date__lt=cutoff,
    )
