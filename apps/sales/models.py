"""
apps/sales/models.py — Sales domain models.

Tables: stores, customers, staffs, orders, order_items
Follows ERD from IE221 requirements.

Rules:
- All business logic → services.py
- All DB queries → selectors.py
- No .objects. calls in views.py
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Store(BaseModel):
    """
    Physical bike store location.

    DB table: stores
    """

    name = models.CharField(max_length=255, db_index=True)
    phone = models.CharField(max_length=25, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    street = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    zip_code = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Customer(BaseModel):
    """
    Customer profile linked to a User account.

    DB table: customers
    OneToOne with User for authentication.
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="customer_profile",
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    phone = models.CharField(max_length=25, blank=True, default="")
    email = models.EmailField(blank=True, default="", db_index=True)
    street = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    zip_code = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["last_name", "first_name"]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return self.full_name or self.email


class Staff(BaseModel):
    """
    Staff member at a store.

    DB table: staffs
    - Self-referential FK for manager hierarchy (manager_id).
    - OneToOne with User for authentication.
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="staff_profile",
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    email = models.EmailField(blank=True, default="", db_index=True)
    phone = models.CharField(max_length=25, blank=True, default="")
    active = models.BooleanField(default=True, db_index=True)
    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staffs",
        db_column="store_id",
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
        db_column="manager_id",
    )

    class Meta:
        verbose_name = "Staff"
        verbose_name_plural = "Staffs"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["store", "active"], name="idx_staff_store_active"),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return self.full_name or self.email


class OrderStatus(models.TextChoices):
    """
    FSM states for an Order.

    Valid transitions:
      PENDING     → PROCESSING, REJECTED
      PROCESSING  → COMPLETED, REJECTED
      REJECTED    → (terminal)
      COMPLETED   → (terminal)
    """

    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    REJECTED = "rejected", "Rejected"
    COMPLETED = "completed", "Completed"


# FSM transition matrix — maps current status to allowed next statuses.
ORDER_STATUS_TRANSITIONS: dict[str, list[str]] = {
    OrderStatus.PENDING: [OrderStatus.PROCESSING, OrderStatus.REJECTED],
    OrderStatus.PROCESSING: [OrderStatus.COMPLETED, OrderStatus.REJECTED],
    OrderStatus.REJECTED: [],
    OrderStatus.COMPLETED: [],
}


class Order(BaseModel):
    """
    Customer order.

    DB table: orders
    Composite index on (customer, order_date) and (store, status).
    """

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
        db_column="customer_id",
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )
    order_date = models.DateField(default=timezone.now)
    required_date = models.DateField(null=True, blank=True)
    shipped_date = models.DateField(null=True, blank=True)
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="orders",
        db_column="store_id",
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        db_column="staff_id",
    )

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-order_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["customer", "order_date"], name="idx_order_customer_date"
            ),
            models.Index(fields=["store", "status"], name="idx_order_store_status"),
        ]

    def __str__(self) -> str:
        return f"Order#{str(self.id)[:8]} [{self.status}]"


class OrderItem(BaseModel):
    """
    A single line item in an Order.

    DB table: order_items
    - list_price is captured at order time (snapshot).
    - discount is a percentage (0–1).
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="order_id",
    )
    product = models.ForeignKey(
        "production.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
        db_column="product_id",
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    list_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price at the time of ordering (snapshot).",
    )
    discount = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Discount rate between 0 (no discount) and 1 (100% off).",
    )

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ["created_at"]

    @property
    def line_total(self):
        """Effective total = quantity * list_price * (1 - discount)."""
        return self.quantity * self.list_price * (1 - self.discount)

    def __str__(self) -> str:
        return f"OrderItem(order={str(self.order_id)[:8]}, product={self.product_id}, qty={self.quantity})"
