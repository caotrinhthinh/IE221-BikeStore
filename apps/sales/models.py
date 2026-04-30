"""
apps/sales/models.py — Sales domain models.

Models:
    Store       — Physical retail location
    Customer    — Buyer linked to a User account (optional)
    Staff       — Employee linked to User, self-referential manager hierarchy
    OrderStatus — FSM enum with allowed transition matrix
    Order       — Sales order header
    OrderItem   — Line item within an order
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Store(BaseModel):
    """
    A physical retail store location.

    All orders and stock entries are scoped to a store.
    """

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Store"
        verbose_name_plural = "Stores"

    def __str__(self) -> str:
        return self.name


class Customer(BaseModel):
    """
    A buyer. Optionally linked to a User account.

    A walk-in customer may not have an account (user=None).
    When a User registers, they can be linked to an existing Customer record.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profile",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True, db_index=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"


class Staff(BaseModel):
    """
    A store employee.

    Self-referential manager_id supports org hierarchy queries.
    Each staff member belongs to exactly one store.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_profile",
    )
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="staff")
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True, db_index=True)
    active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Staff"
        verbose_name_plural = "Staff"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"{self.full_name} @ {self.store}"


class OrderStatus(models.TextChoices):
    """
    FSM states for an Order.

    Allowed transitions:
        PENDING     → PROCESSING | REJECTED
        PROCESSING  → COMPLETED  | REJECTED
        REJECTED    → (terminal)
        COMPLETED   → (terminal)
    """

    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    REJECTED = "rejected", "Rejected"
    COMPLETED = "completed", "Completed"


# Transition matrix: {current_status: [allowed_next_statuses]}
ORDER_STATUS_TRANSITIONS: dict[str, list[str]] = {
    OrderStatus.PENDING: [OrderStatus.PROCESSING, OrderStatus.REJECTED],
    OrderStatus.PROCESSING: [OrderStatus.COMPLETED, OrderStatus.REJECTED],
    OrderStatus.REJECTED: [],
    OrderStatus.COMPLETED: [],
}


class Order(BaseModel):
    """
    Sales order header.

    DB indexes:
        - (customer_id, order_date) — query orders by customer chronologically
        - (store_id, order_status)  — filter orders by store + status (common dashboard query)
    """

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="orders")
    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )
    order_date = models.DateField(auto_now_add=True)
    required_date = models.DateField(null=True, blank=True)
    shipped_date = models.DateField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(fields=["customer_id", "order_date"]),
            models.Index(fields=["store_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk} [{self.status}] — {self.customer}"

    def can_transition_to(self, target: str) -> bool:
        """Check whether FSM allows transition from current status → target."""
        return target in ORDER_STATUS_TRANSITIONS.get(self.status, [])


class OrderItem(BaseModel):
    """
    A single line item in an Order.

    list_price is captured at order time so historical orders are
    not affected by future price changes.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "production.Product", on_delete=models.PROTECT, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    list_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    discount = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        unique_together = [("order", "product")]

    @property
    def line_total(self) -> Decimal:
        """Net price after discount, for this line."""
        unit_price = self.list_price * (1 - self.discount / 100)
        return (unit_price * self.quantity).quantize(Decimal("0.01"))

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product} (Order {self.order_id})"
