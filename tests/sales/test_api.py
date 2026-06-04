"""Sales API integration tests."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.production.models import Stock
from apps.sales.models import Order, OrderStatus
from tests.factories import (
    CustomerFactory,
    OrderFactory,
    ProductFactory,
    StaffFactory,
    StockFactory,
    StoreFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticate(api_client):
    def _authenticate(user):
        api_client.force_authenticate(user=user)
        return api_client

    return _authenticate


@pytest.mark.django_db
class TestOrderCreateAPI:
    def test_create_order_success_and_triggers_celery_task(
        self, authenticate, api_client
    ):
        """
        Scenario 1: API creates order successfully.
        - Deducts stock.
        - Triggers Celery task to send email.
        """
        customer = CustomerFactory()
        store = StoreFactory()
        product = ProductFactory(list_price=Decimal("1500.00"))
        StockFactory(store=store, product=product, quantity=10)

        # Authenticate as customer
        client = authenticate(customer.user)

        payload = {
            "customer_id": str(customer.pk),
            "store_id": str(store.pk),
            "lines": [
                {
                    "product_id": str(product.pk),
                    "quantity": 2,
                }
            ],
        }

        url = reverse("order-list")

        # Mock the Celery task so we don't actually send emails in tests
        with (
            patch("django.db.transaction.on_commit", lambda func: func()),
            patch("apps.sales.tasks.send_order_confirmation.delay") as mock_task,
        ):
            response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data

        # Verify Database
        order_id = data["id"]
        order = Order.objects.get(id=order_id)
        assert order.status == OrderStatus.PENDING

        stock = Stock.objects.get(store=store, product=product)
        assert stock.quantity == 8  # 10 - 2 = 8

        # Verify Celery Task was triggered
        mock_task.assert_called_once_with(str(order.pk))

    def test_create_order_fails_insufficient_stock_and_no_celery_task(
        self, authenticate, api_client
    ):
        """
        Scenario 2: API fails due to insufficient stock.
        - Database rolls back (no order, no stock deducted).
        - Celery task is NOT triggered.
        """
        customer = CustomerFactory()
        store = StoreFactory()
        product = ProductFactory(list_price=Decimal("1500.00"))
        StockFactory(store=store, product=product, quantity=5)

        client = authenticate(customer.user)

        payload = {
            "customer_id": str(customer.pk),
            "store_id": str(store.pk),
            "lines": [
                {
                    "product_id": str(product.pk),
                    "quantity": 100,  # Request more than available
                }
            ],
        }

        url = reverse("order-list")

        with patch("apps.sales.tasks.send_order_confirmation.delay") as mock_task:
            response = client.post(url, payload, format="json")

        # Verify API Error
        assert response.status_code == status.HTTP_409_CONFLICT

        # Verify Database is untouched
        assert Order.objects.count() == 0
        stock = Stock.objects.get(store=store, product=product)
        assert stock.quantity == 5  # Unchanged

        # Verify Celery Task was NOT triggered
        mock_task.assert_not_called()


@pytest.mark.django_db
class TestOrderStatusAPI:
    def test_staff_can_ship_order_and_transition_to_completed(
        self, authenticate, api_client
    ):
        """
        Scenario 3: Staff ships an order.
        - Staff must belong to the same store as the order.
        - Order transitions from PENDING to COMPLETED.
        - shipped_date is set.
        """
        store = StoreFactory()
        staff = StaffFactory(store=store)
        order = OrderFactory(store=store, status=OrderStatus.PENDING)

        client = authenticate(staff.user)
        url = reverse("order-ship", kwargs={"pk": order.pk})

        response = client.post(url)

        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()
        assert order.status == OrderStatus.COMPLETED
        assert order.shipped_date is not None

    def test_staff_cannot_cancel_completed_order(self, authenticate, api_client):
        """
        Scenario 4: Invalid FSM transition.
        - Staff tries to cancel a COMPLETED order.
        - API returns 409 Conflict.
        """
        store = StoreFactory()
        staff = StaffFactory(store=store)
        order = OrderFactory(store=store, status=OrderStatus.COMPLETED)

        client = authenticate(staff.user)
        url = reverse("order-cancel", kwargs={"pk": order.pk})

        response = client.post(url)

        assert response.status_code == status.HTTP_409_CONFLICT
        order.refresh_from_db()
        assert order.status == OrderStatus.COMPLETED
