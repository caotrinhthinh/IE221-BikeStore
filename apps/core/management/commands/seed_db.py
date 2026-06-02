import random

from allauth.account.models import EmailAddress
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.production.models import Brand, Category, Product, Stock
from apps.sales.models import Customer, Order, OrderItem, OrderStatus, Staff, Store
from apps.users.models import Role, User
from tests.factories import (
    BrandFactory,
    CategoryFactory,
    CustomerFactory,
    OrderFactory,
    OrderItemFactory,
    ProductFactory,
    StockFactory,
    StoreFactory,
)


class Command(BaseCommand):
    help = "Seed database with mock data for development and testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean the database before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clean"]:
            self.stdout.write("Cleaning existing database records...")
            # Delete in order of dependencies (foreign key relationships)
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Stock.objects.all().delete()
            Product.objects.all().delete()
            Brand.objects.all().delete()
            Category.objects.all().delete()
            Staff.objects.all().delete()
            Customer.objects.all().delete()
            Store.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Database cleaned successfully."))

        self.stdout.write("Seeding database...")

        # 1. Create default users (fixed accounts)
        self.stdout.write("Creating default users...")

        # Superuser
        User.objects.create_superuser(
            email="admin@example.com",
            password="Str0ng!Pass",
            first_name="Admin",
            last_name="Super",
        )

        # Store Managers
        manager_hanoi = User.objects.create_user(
            email="manager_hanoi@example.com",
            password="Str0ng!Pass",
            role=Role.STORE_MANAGER,
            first_name="Hanoi",
            last_name="Manager",
        )

        # Keep manager@example.com for backward compatibility
        manager_user = User.objects.create_user(
            email="manager@example.com",
            password="Str0ng!Pass",
            role=Role.STORE_MANAGER,
            first_name="Manager",
            last_name="Store",
        )

        manager_saigon = User.objects.create_user(
            email="manager_saigon@example.com",
            password="Str0ng!Pass",
            role=Role.STORE_MANAGER,
            first_name="Saigon",
            last_name="Manager",
        )

        manager_danang = User.objects.create_user(
            email="manager_danang@example.com",
            password="Str0ng!Pass",
            role=Role.STORE_MANAGER,
            first_name="Danang",
            last_name="Manager",
        )

        # Staff
        staff_user = User.objects.create_user(
            email="staff@example.com",
            password="Str0ng!Pass",
            role=Role.STAFF,
            first_name="Staff",
            last_name="One",
        )

        # Customer
        customer_user = User.objects.create_user(
            email="customer@example.com",
            password="Str0ng!Pass",
            role=Role.CUSTOMER,
            first_name="Customer",
            last_name="One",
        )

        # (Email verification moved to the end of script)

        # 2. Create Stores
        self.stdout.write("Creating stores...")
        hanoi_store = StoreFactory(name="Hanoi BikeStore", email="hanoi@bikestore.com")
        saigon_store = StoreFactory(
            name="Saigon BikeStore", email="saigon@bikestore.com"
        )
        danang_store = StoreFactory(
            name="Danang BikeStore", email="danang@bikestore.com"
        )

        # Assign staff and managers to stores
        Staff.objects.create(
            user=manager_hanoi,
            store=hanoi_store,
            first_name=manager_hanoi.first_name,
            last_name=manager_hanoi.last_name,
            email=manager_hanoi.email,
            active=True,
        )
        Staff.objects.create(
            user=manager_user,
            store=hanoi_store,
            first_name=manager_user.first_name,
            last_name=manager_user.last_name,
            email=manager_user.email,
            active=True,
        )
        Staff.objects.create(
            user=manager_saigon,
            store=saigon_store,
            first_name=manager_saigon.first_name,
            last_name=manager_saigon.last_name,
            email=manager_saigon.email,
            active=True,
        )
        Staff.objects.create(
            user=manager_danang,
            store=danang_store,
            first_name=manager_danang.first_name,
            last_name=manager_danang.last_name,
            email=manager_danang.email,
            active=True,
        )
        Staff.objects.create(
            user=staff_user,
            store=hanoi_store,
            first_name=staff_user.first_name,
            last_name=staff_user.last_name,
            email=staff_user.email,
            active=True,
        )

        # Create Customer record for customer user
        customer_profile = Customer.objects.create(
            user=customer_user,
            first_name=customer_user.first_name,
            last_name=customer_user.last_name,
            email=customer_user.email,
        )

        # Create additional random customers
        customers = [customer_profile]
        for _ in range(10):
            customers.append(CustomerFactory())

        # 3. Create Brands and Categories
        self.stdout.write("Creating brands and categories...")
        brands = [
            BrandFactory(name="Giant"),
            BrandFactory(name="Trek"),
            BrandFactory(name="Specialized"),
            BrandFactory(name="Cannondale"),
        ]

        categories = [
            CategoryFactory(name="Road Bikes"),
            CategoryFactory(name="Mountain Bikes"),
            CategoryFactory(name="Electric Bikes"),
            CategoryFactory(name="City Bikes"),
        ]

        # 4. Create Products
        self.stdout.write("Creating products...")
        products = []
        bike_names = [
            ("Giant Defy Advanced", 0, 0, "1200.00"),
            ("Giant Talon 2", 0, 1, "650.00"),
            ("Trek Domane AL", 1, 0, "1100.00"),
            ("Trek Marlin 5", 1, 1, "700.00"),
            ("Specialized Tarmac SL7", 2, 0, "3200.00"),
            ("Specialized Rockhopper", 2, 1, "800.00"),
            ("Cannondale Synapse", 3, 0, "1300.00"),
            ("Cannondale Trail 8", 3, 1, "550.00"),
            ("Giant FastRoad E+", 0, 2, "2500.00"),
            ("Trek Powerfly FS", 1, 2, "4500.00"),
        ]

        for name, brand_idx, cat_idx, price in bike_names:
            product = ProductFactory(
                name=name,
                brand=brands[brand_idx],
                category=categories[cat_idx],
                list_price=price,
                model_year=2026,
            )
            products.append(product)

        # 5. Create Stocks for Hanoi, Saigon, and Danang stores
        self.stdout.write("Creating stocks...")
        stores = [hanoi_store, saigon_store, danang_store]
        for store in stores:
            for product in products:
                StockFactory(
                    store=store,
                    product=product,
                    quantity=random.randint(5, 30),
                )

        # 6. Create some orders
        self.stdout.write("Creating orders...")
        hanoi_staff = Staff.objects.filter(store=hanoi_store, active=True).first()

        # Order 1: Pending Order
        order1 = OrderFactory(
            customer=random.choice(customers),
            store=hanoi_store,
            staff=hanoi_staff,
            status=OrderStatus.PENDING,
        )
        # Select 2 random products
        for prod in random.sample(products, 2):
            OrderItemFactory(
                order=order1,
                product=prod,
                quantity=random.randint(1, 2),
                list_price=prod.list_price,
            )

        # Order 2: Completed Order
        order2 = OrderFactory(
            customer=random.choice(customers),
            store=hanoi_store,
            staff=hanoi_staff,
            status=OrderStatus.COMPLETED,
        )
        for prod in random.sample(products, 1):
            OrderItemFactory(
                order=order2,
                product=prod,
                quantity=1,
                list_price=prod.list_price,
            )

        # Order 3: Rejected Order
        order3 = OrderFactory(
            customer=random.choice(customers),
            store=hanoi_store,
            staff=hanoi_staff,
            status=OrderStatus.REJECTED,
        )
        for prod in random.sample(products, 1):
            OrderItemFactory(
                order=order3,
                product=prod,
                quantity=1,
                list_price=prod.list_price,
            )

        # 7. Verify all created users' emails
        self.stdout.write("Verifying user emails...")
        for user in User.objects.all():
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={"primary": True, "verified": True},
            )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
