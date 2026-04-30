"""
tests/factories.py — factory_boy factories for all domain models.

Usage in tests:
    from tests.factories import OrderFactory, ProductFactory, StockFactory

    order = OrderFactory()
    product = ProductFactory(list_price=Decimal("500.00"))
    stock = StockFactory(product=product, store=order.store, quantity=10)
"""
from __future__ import annotations

import factory
from decimal import Decimal
from factory.django import DjangoModelFactory

from apps.users.models import Role, User
from apps.production.models import Brand, Category, Product, Stock
from apps.sales.models import Customer, Order, OrderItem, OrderStatus, Staff, Store


# ── Users ────────────────────────────────────────────────────────────

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = Role.CUSTOMER
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):  # noqa: N805
        raw = extracted or "Str0ng!Pass"
        obj.set_password(raw)
        if create:
            obj.save()


# ── Production ───────────────────────────────────────────────────────

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")
    parent = None


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = Brand

    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.Sequence(lambda n: f"brand-{n}")


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    brand = factory.SubFactory(BrandFactory)
    category = factory.SubFactory(CategoryFactory)
    model_year = 2024
    list_price = Decimal("999.99")


# ── Sales ────────────────────────────────────────────────────────────

class StoreFactory(DjangoModelFactory):
    class Meta:
        model = Store

    name = factory.Sequence(lambda n: f"Store {n}")
    phone = factory.Faker("phone_number")
    email = factory.Sequence(lambda n: f"store{n}@bikes.com")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer

    user = factory.SubFactory(UserFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"customer{n}@example.com")
    phone = factory.Faker("phone_number")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")


class StaffFactory(DjangoModelFactory):
    class Meta:
        model = Staff

    user = factory.SubFactory(UserFactory, role=Role.STAFF)
    store = factory.SubFactory(StoreFactory)
    manager = None
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"staff{n}@bikes.com")
    active = True


class StockFactory(DjangoModelFactory):
    class Meta:
        model = Stock

    product = factory.SubFactory(ProductFactory)
    store = factory.SubFactory(StoreFactory)
    quantity = 10


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    customer = factory.SubFactory(CustomerFactory)
    store = factory.SubFactory(StoreFactory)
    staff = None
    status = OrderStatus.PENDING


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1
    list_price = Decimal("999.99")
    discount = Decimal("0.00")
