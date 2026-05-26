"""Sales service-layer tests."""

from decimal import Decimal

import pytest

from apps.core.exceptions import InsufficientStockError, InvalidStatusTransitionError
from apps.production.models import Stock
from apps.sales.models import Order, OrderItem, OrderStatus
from apps.sales.services import OrderLineInput, cancel_order, create_order, ship_order
from tests.factories import (
    CustomerFactory,
    OrderFactory,
    ProductFactory,
    StockFactory,
    StoreFactory,
)


@pytest.mark.django_db
class TestCreateOrderService:
    def test_create_order_decrements_stock_and_creates_items(self):
        customer = CustomerFactory()
        store = StoreFactory()
        product = ProductFactory(list_price=Decimal("1200.00"))
        StockFactory(store=store, product=product, quantity=5)

        order = create_order(
            customer_id=customer.pk,
            store_id=store.pk,
            lines=[
                OrderLineInput(
                    product_id=product.pk, quantity=2, discount=Decimal("0.10")
                )
            ],
        )

        stock = Stock.objects.get(store=store, product=product)
        item = OrderItem.objects.get(order=order)

        assert order.status == OrderStatus.PENDING
        assert stock.quantity == 3
        assert item.quantity == 2
        assert item.list_price == Decimal("1200.00")

    def test_create_order_is_atomic_when_stock_is_insufficient(self):
        customer = CustomerFactory()
        store = StoreFactory()
        product = ProductFactory()
        StockFactory(store=store, product=product, quantity=1)

        with pytest.raises(InsufficientStockError):
            create_order(
                customer_id=customer.pk,
                store_id=store.pk,
                lines=[OrderLineInput(product_id=product.pk, quantity=2)],
            )

        assert Order.objects.count() == 0
        assert OrderItem.objects.count() == 0
        assert Stock.objects.get(store=store, product=product).quantity == 1


@pytest.mark.django_db
class TestOrderStatusService:
    def test_ship_order_advances_pending_order_to_completed(self):
        order = OrderFactory(status=OrderStatus.PENDING)

        updated_order = ship_order(order_id=order.pk)

        assert updated_order.status == OrderStatus.COMPLETED
        assert updated_order.shipped_date is not None

    def test_cancel_completed_order_raises_invalid_transition(self):
        order = OrderFactory(status=OrderStatus.COMPLETED)

        with pytest.raises(InvalidStatusTransitionError):
            cancel_order(order_id=order.pk)
