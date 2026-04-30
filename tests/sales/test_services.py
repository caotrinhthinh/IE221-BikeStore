"""
tests/sales/test_services.py — Unit tests for the Sales service layer.

Coverage:
    create_order()
        - happy path: creates Order + OrderItems, decrements Stock
        - insufficient stock: raises InsufficientStockError
        - stock = 0: raises InsufficientStockError
        - empty lines: raises ValueError
        - invalid product: raises Product.DoesNotExist
        - atomic rollback: no partial writes on error

    update_order_status() / ship_order() / cancel_order()
        - happy path FSM transitions
        - invalid FSM transition: raises InvalidStatusTransitionError

    update_stock()
        - creates new Stock entry if absent
        - updates existing Stock entry
        - negative quantity: raises ValueError

    check_availability()
        - True when stock >= requested
        - False when stock < requested
        - False when no Stock entry exists

    get_low_stock_products()
        - returns only entries below threshold
        - ordered by quantity ascending
"""
from __future__ import annotations

import pytest
from decimal import Decimal

from apps.core.exceptions import InsufficientStockError, InvalidStatusTransitionError
from apps.production.models import Product, Stock
from apps.sales.models import Order, OrderStatus
from apps.sales import services
from tests.factories import (
    CustomerFactory,
    OrderFactory,
    ProductFactory,
    StaffFactory,
    StockFactory,
    StoreFactory,
)


# ── Helpers ──────────────────────────────────────────────────────────

def make_line(product: Product, quantity: int, discount: Decimal = Decimal("0.00")):
    return services.OrderLineInput(
        product_id=product.pk,
        quantity=quantity,
        discount=discount,
    )


# ── create_order ─────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
class TestCreateOrder:
    def test_happy_path_creates_order_and_items(self):
        store = StoreFactory()
        customer = CustomerFactory()
        product = ProductFactory(list_price=Decimal("500.00"))
        StockFactory(product=product, store=store, quantity=5)

        order = services.create_order(
            customer_id=customer.pk,
            store_id=store.pk,
            lines=[make_line(product, quantity=2)],
        )

        assert order.pk is not None
        assert order.status == OrderStatus.PENDING
        assert order.items.count() == 1

        item = order.items.first()
        assert item.quantity == 2
        assert item.list_price == Decimal("500.00")

    def test_happy_path_decrements_stock(self):
        store = StoreFactory()
        customer = CustomerFactory()
        product = ProductFactory()
        stock = StockFactory(product=product, store=store, quantity=10)

        services.create_order(
            customer_id=customer.pk,
            store_id=store.pk,
            lines=[make_line(product, quantity=3)],
        )

        stock.refresh_from_db()
        assert stock.quantity == 7

    def test_multiple_lines_decrements_all_stock(self):
        store = StoreFactory()
        customer = CustomerFactory()
        product_a = ProductFactory()
        product_b = ProductFactory()
        stock_a = StockFactory(product=product_a, store=store, quantity=5)
        stock_b = StockFactory(product=product_b, store=store, quantity=8)

        services.create_order(
            customer_id=customer.pk,
            store_id=store.pk,
            lines=[
                make_line(product_a, quantity=2),
                make_line(product_b, quantity=4),
            ],
        )

        stock_a.refresh_from_db()
        stock_b.refresh_from_db()
        assert stock_a.quantity == 3
        assert stock_b.quantity == 4

    def test_insufficient_stock_raises_error(self):
        store = StoreFactory()
        customer = CustomerFactory()
        product = ProductFactory()
        StockFactory(product=product, store=store, quantity=2)

        with pytest.raises(InsufficientStockError) as exc_info:
            services.create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[make_line(product, quantity=5)],
            )

        err = exc_info.value
        assert err.product_id == product.pk
        assert err.requested == 5
        assert err.available == 2

    def test_stock_zero_raises_insufficient_stock_error(self):
        store = StoreFactory()
        customer = CustomerFactory()
        product = ProductFactory()
        StockFactory(product=product, store=store, quantity=0)

        with pytest.raises(InsufficientStockError):
            services.create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[make_line(product, quantity=1)],
            )

    def test_no_stock_entry_raises_insufficient_stock_error(self):
        """No Stock row at all — should be treated as quantity=0."""
        store = StoreFactory()
        customer = CustomerFactory()
        product = ProductFactory()
        # No StockFactory call → no Stock entry

        with pytest.raises(InsufficientStockError):
            services.create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[make_line(product, quantity=1)],
            )

    def test_empty_lines_raises_value_error(self):
        store = StoreFactory()
        customer = CustomerFactory()

        with pytest.raises(ValueError, match="at least one line"):
            services.create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[],
            )

    def test_invalid_product_raises_does_not_exist(self):
        import uuid
        store = StoreFactory()
        customer = CustomerFactory()

        with pytest.raises(Product.DoesNotExist):
            services.create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[make_line.__func__(None, uuid.uuid4(), 1)],  # type: ignore
            )

    def test_invalid_product_id_raises_does_not_exist(self):
        import uuid
        store = StoreFactory()
        customer = CustomerFactory()

        with pytest.raises(Product.DoesNotExist):
            services.create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[
                    services.OrderLineInput(
                        product_id=uuid.uuid4(),  # non-existent
                        quantity=1,
                    )
                ],
            )

    def test_atomic_rollback_on_insufficient_stock(self):
        """
        When the second line has insufficient stock, the whole transaction
        must roll back — no Order or OrderItem should be persisted.
        """
        store = StoreFactory()
        customer = CustomerFactory()
        product_ok = ProductFactory()
        product_empty = ProductFactory()
        StockFactory(product=product_ok, store=store, quantity=10)
        StockFactory(product=product_empty, store=store, quantity=0)

        with pytest.raises(InsufficientStockError):
            services.create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[
                    make_line(product_ok, quantity=1),
                    make_line(product_empty, quantity=1),
                ],
            )

        assert Order.objects.count() == 0

    def test_with_staff(self):
        store = StoreFactory()
        customer = CustomerFactory()
        product = ProductFactory()
        StockFactory(product=product, store=store, quantity=5)
        staff = StaffFactory(store=store)

        order = services.create_order(
            customer_id=customer.pk,
            store_id=store.pk,
            staff_id=staff.pk,
            lines=[make_line(product, quantity=1)],
        )

        assert order.staff_id == staff.pk

    def test_discount_stored_on_item(self):
        store = StoreFactory()
        customer = CustomerFactory()
        product = ProductFactory(list_price=Decimal("1000.00"))
        StockFactory(product=product, store=store, quantity=5)

        order = services.create_order(
            customer_id=customer.pk,
            store_id=store.pk,
            lines=[make_line(product, quantity=1, discount=Decimal("10.00"))],
        )

        item = order.items.first()
        assert item.discount == Decimal("10.00")
        assert item.line_total == Decimal("900.00")


# ── FSM transitions ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestOrderStatusFSM:
    def test_pending_to_processing(self):
        order = OrderFactory(status=OrderStatus.PENDING)
        updated = services.update_order_status(
            order=order, target_status=OrderStatus.PROCESSING
        )
        assert updated.status == OrderStatus.PROCESSING

    def test_pending_to_rejected(self):
        order = OrderFactory(status=OrderStatus.PENDING)
        updated = services.update_order_status(
            order=order, target_status=OrderStatus.REJECTED
        )
        assert updated.status == OrderStatus.REJECTED

    def test_processing_to_completed(self):
        order = OrderFactory(status=OrderStatus.PROCESSING)
        updated = services.update_order_status(
            order=order, target_status=OrderStatus.COMPLETED
        )
        assert updated.status == OrderStatus.COMPLETED

    def test_processing_to_rejected(self):
        order = OrderFactory(status=OrderStatus.PROCESSING)
        updated = services.update_order_status(
            order=order, target_status=OrderStatus.REJECTED
        )
        assert updated.status == OrderStatus.REJECTED

    def test_completed_is_terminal(self):
        order = OrderFactory(status=OrderStatus.COMPLETED)
        with pytest.raises(InvalidStatusTransitionError):
            services.update_order_status(
                order=order, target_status=OrderStatus.PROCESSING
            )

    def test_rejected_is_terminal(self):
        order = OrderFactory(status=OrderStatus.REJECTED)
        with pytest.raises(InvalidStatusTransitionError):
            services.update_order_status(
                order=order, target_status=OrderStatus.PENDING
            )

    def test_pending_to_completed_invalid(self):
        """PENDING → COMPLETED is not an allowed transition."""
        order = OrderFactory(status=OrderStatus.PENDING)
        with pytest.raises(InvalidStatusTransitionError):
            services.update_order_status(
                order=order, target_status=OrderStatus.COMPLETED
            )

    def test_ship_order_sets_shipped_date(self):
        order = OrderFactory(status=OrderStatus.PROCESSING)
        updated = services.ship_order(order_id=order.pk)
        assert updated.status == OrderStatus.COMPLETED
        assert updated.shipped_date is not None

    def test_cancel_order_rejects(self):
        order = OrderFactory(status=OrderStatus.PENDING)
        updated = services.cancel_order(order_id=order.pk)
        assert updated.status == OrderStatus.REJECTED


# ── update_stock ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUpdateStock:
    def test_creates_new_stock_entry(self):
        product = ProductFactory()
        store = StoreFactory()

        stock = services.update_stock(
            product_id=product.pk, store_id=store.pk, quantity=20
        )

        assert stock.quantity == 20
        assert Stock.objects.filter(product=product, store=store).count() == 1

    def test_updates_existing_stock_entry(self):
        existing = StockFactory(quantity=5)
        services.update_stock(
            product_id=existing.product_id,
            store_id=existing.store_id,
            quantity=50,
        )

        existing.refresh_from_db()
        assert existing.quantity == 50

    def test_negative_quantity_raises_value_error(self):
        product = ProductFactory()
        store = StoreFactory()

        with pytest.raises(ValueError, match="negative"):
            services.update_stock(
                product_id=product.pk, store_id=store.pk, quantity=-1
            )


# ── check_availability ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestCheckAvailability:
    def test_available_when_stock_sufficient(self):
        stock = StockFactory(quantity=10)
        assert services.check_availability(
            product_id=stock.product_id,
            store_id=stock.store_id,
            quantity=10,
        )

    def test_not_available_when_stock_insufficient(self):
        stock = StockFactory(quantity=2)
        assert not services.check_availability(
            product_id=stock.product_id,
            store_id=stock.store_id,
            quantity=3,
        )

    def test_not_available_when_no_stock_entry(self):
        import uuid
        product = ProductFactory()
        store = StoreFactory()
        assert not services.check_availability(
            product_id=product.pk,
            store_id=store.pk,
            quantity=1,
        )


# ── get_low_stock_products ─────────────────────────────────────────────

@pytest.mark.django_db
class TestGetLowStockProducts:
    def test_returns_only_below_threshold(self):
        store = StoreFactory()
        low = StockFactory(store=store, quantity=2)
        StockFactory(store=store, quantity=10)  # above threshold

        results = list(services.get_low_stock_products(threshold=5, store_id=store.pk))

        assert len(results) == 1
        assert results[0].pk == low.pk

    def test_ordered_by_quantity_ascending(self):
        store = StoreFactory()
        s3 = StockFactory(store=store, quantity=3)
        s1 = StockFactory(store=store, quantity=1)
        s5 = StockFactory(store=store, quantity=5)

        results = list(
            services.get_low_stock_products(threshold=5, store_id=store.pk)
        )
        quantities = [r.quantity for r in results]
        assert quantities == sorted(quantities)
        assert quantities[0] == 1
