"""Factory Boy fixtures for BikeStore domain tests."""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.production.models import Brand, Category, Product, Stock
from apps.sales.models import Customer, Order, OrderItem, OrderStatus, Staff, Store
from apps.users.models import Role, User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = Role.CUSTOMER
    password = factory.PostGenerationMethodCall("set_password", "Str0ng!Pass")


class StoreFactory(DjangoModelFactory):
    class Meta:
        model = Store

    name = factory.Sequence(lambda n: f"Store {n}")
    email = factory.Sequence(lambda n: f"store{n}@example.com")


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer

    user = factory.SubFactory(UserFactory, role=Role.CUSTOMER)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.SelfAttribute("user.email")


class StaffFactory(DjangoModelFactory):
    class Meta:
        model = Staff

    user = factory.SubFactory(UserFactory, role=Role.STAFF)
    store = factory.SubFactory(StoreFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.SelfAttribute("user.email")
    active = True


class ManagerStaffFactory(DjangoModelFactory):
    """Staff profile linked to a user with STORE_MANAGER role."""

    class Meta:
        model = Staff

    user = factory.SubFactory(UserFactory, role=Role.STORE_MANAGER)
    store = factory.SubFactory(StoreFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.SelfAttribute("user.email")
    active = True


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = Brand

    name = factory.Sequence(lambda n: f"Brand {n}")


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Bike {n}")
    brand = factory.SubFactory(BrandFactory)
    category = factory.SubFactory(CategoryFactory)
    model_year = 2026
    list_price = Decimal("999.99")
    description = factory.Faker("sentence")


class StockFactory(DjangoModelFactory):
    class Meta:
        model = Stock

    store = factory.SubFactory(StoreFactory)
    product = factory.SubFactory(ProductFactory)
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
    list_price = factory.SelfAttribute("product.list_price")
    discount = Decimal("0.00")
