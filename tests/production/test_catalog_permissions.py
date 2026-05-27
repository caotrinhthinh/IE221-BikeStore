"""
tests/production/test_catalog_permissions.py

Integration tests for Catalog API CRUD endpoints and store-based permissions.

Coverage:
- Category / Brand / Product: public read, STORE_MANAGER write, Customer/Anon denied.
- Stock: IsAuthenticated read, STORE_MANAGER create scoped to own store,
  Admin can create for any store, manager of another store is denied.
"""

import pytest
from rest_framework import status

from apps.users.models import Role
from tests.factories import (
    BrandFactory,
    CategoryFactory,
    ManagerStaffFactory,
    ProductFactory,
    StockFactory,
    StoreFactory,
    UserFactory,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def force_login(client, user):
    """Authenticate client as *user* using force_authenticate (no throttling)."""
    client.force_authenticate(user=user)
    return client


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestCategoryPermissions:
    url_list = "/api/v1/categories/"

    def test_anonymous_can_list_categories(self, api_client):
        CategoryFactory.create_batch(2)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK

    def test_customer_can_list_categories(self, api_client):
        customer = UserFactory(role=Role.CUSTOMER)
        force_login(api_client, customer)
        CategoryFactory.create_batch(2)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK

    def test_anonymous_cannot_create_category(self, api_client):
        resp = api_client.post(
            self.url_list, {"name": "Roadbikes"}, content_type="application/json"
        )
        # Anonymous → IsAuthenticated fails → 401
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_customer_cannot_create_category(self, api_client):
        customer = UserFactory(role=Role.CUSTOMER)
        force_login(api_client, customer)
        resp = api_client.post(
            self.url_list, {"name": "Roadbikes"}, content_type="application/json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_create_category(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        resp = api_client.post(
            self.url_list, {"name": "Roadbikes"}, content_type="application/json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Roadbikes"

    def test_manager_can_update_category(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        cat = CategoryFactory(name="OldName")
        resp = api_client.patch(
            f"{self.url_list}{cat.id}/",
            {"name": "NewName"},
            content_type="application/json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "NewName"

    def test_manager_can_delete_leaf_category(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        cat = CategoryFactory()
        resp = api_client.delete(f"{self.url_list}{cat.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_manager_cannot_delete_category_with_children(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        parent = CategoryFactory(name="Parent")
        CategoryFactory(name="Child", parent=parent)
        parent.refresh_from_db()
        resp = api_client.delete(f"{self.url_list}{parent.id}/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ══════════════════════════════════════════════════════════════════════════════
# BRANDS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestBrandPermissions:
    url_list = "/api/v1/brands/"

    def test_anonymous_can_list_brands(self, api_client):
        BrandFactory.create_batch(3)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK

    def test_anonymous_cannot_create_brand(self, api_client):
        resp = api_client.post(
            self.url_list, {"name": "Trek"}, content_type="application/json"
        )
        # Anonymous → IsAuthenticated fails → 401
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_manager_can_create_brand(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        resp = api_client.post(
            self.url_list, {"name": "Trek"}, content_type="application/json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Trek"

    def test_manager_can_update_brand(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        brand = BrandFactory(name="OldBrand")
        resp = api_client.patch(
            f"{self.url_list}{brand.id}/",
            {"name": "NewBrand"},
            content_type="application/json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "NewBrand"

    def test_manager_can_delete_brand_without_products(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        brand = BrandFactory()
        resp = api_client.delete(f"{self.url_list}{brand.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_manager_cannot_delete_brand_with_products(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        brand = BrandFactory()
        ProductFactory(brand=brand)
        resp = api_client.delete(f"{self.url_list}{brand.id}/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestProductPermissions:
    url_list = "/api/v1/products/"

    def test_anonymous_can_list_products(self, api_client):
        ProductFactory.create_batch(2)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK

    def test_anonymous_cannot_create_product(self, api_client):
        brand = BrandFactory()
        cat = CategoryFactory()
        payload = {
            "name": "TestBike",
            "brand": str(brand.id),
            "category": str(cat.id),
            "model_year": 2026,
            "list_price": "999.99",
        }
        resp = api_client.post(self.url_list, payload, content_type="application/json")
        # Anonymous → IsAuthenticated fails → 401
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_manager_can_create_product(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        brand = BrandFactory()
        cat = CategoryFactory()
        payload = {
            "name": "NewBike",
            "brand": str(brand.id),
            "category": str(cat.id),
            "model_year": 2026,
            "list_price": "1299.99",
            "description": "A great bike",
        }
        resp = api_client.post(self.url_list, payload, content_type="application/json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "NewBike"

    def test_manager_can_update_product(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        product = ProductFactory(name="OldBike")
        resp = api_client.patch(
            f"{self.url_list}{product.id}/",
            {"name": "UpdatedBike"},
            content_type="application/json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "UpdatedBike"

    def test_manager_can_delete_product_without_orders(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        product = ProductFactory()
        resp = api_client.delete(f"{self.url_list}{product.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# ══════════════════════════════════════════════════════════════════════════════
# STOCKS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestStockPermissions:
    url_list = "/api/v1/stocks/"

    def test_anonymous_cannot_list_stocks(self, api_client):
        resp = api_client.get(self.url_list)
        # Anonymous → IsAuthenticated fails → 401
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_customer_cannot_list_stocks(self, api_client):
        customer = UserFactory(role=Role.CUSTOMER)
        force_login(api_client, customer)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_list_own_store_stocks(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        StockFactory(store=manager_profile.store)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        for item in resp.data["results"]:
            assert str(item["store"]) == str(manager_profile.store.id)

    def test_manager_sees_only_own_store_stocks(self, api_client):
        manager_profile = ManagerStaffFactory()
        other_store = StoreFactory()
        StockFactory(store=manager_profile.store)
        StockFactory(store=other_store)
        force_login(api_client, manager_profile.user)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        ids = {str(item["store"]) for item in resp.data["results"]}
        assert ids == {str(manager_profile.store.id)}

    def test_admin_sees_all_stocks(self, api_client):
        admin = UserFactory(role=Role.ADMIN)
        store1 = StoreFactory()
        store2 = StoreFactory()
        StockFactory(store=store1)
        StockFactory(store=store2)
        force_login(api_client, admin)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        store_ids = {str(item["store"]) for item in resp.data["results"]}
        assert str(store1.id) in store_ids
        assert str(store2.id) in store_ids

    def test_manager_can_create_stock_for_own_store(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        product = ProductFactory()
        payload = {
            "store": str(manager_profile.store.id),
            "product": str(product.id),
            "quantity": 50,
        }
        resp = api_client.post(self.url_list, payload, content_type="application/json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["quantity"] == 50

    def test_manager_cannot_create_stock_for_another_store(self, api_client):
        manager_profile = ManagerStaffFactory()
        other_store = StoreFactory()
        force_login(api_client, manager_profile.user)
        product = ProductFactory()
        payload = {
            "store": str(other_store.id),
            "product": str(product.id),
            "quantity": 10,
        }
        resp = api_client.post(self.url_list, payload, content_type="application/json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_stock_for_any_store(self, api_client):
        admin = UserFactory(role=Role.ADMIN)
        force_login(api_client, admin)
        store = StoreFactory()
        product = ProductFactory()
        payload = {
            "store": str(store.id),
            "product": str(product.id),
            "quantity": 25,
        }
        resp = api_client.post(self.url_list, payload, content_type="application/json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_manager_can_update_own_store_stock(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        stock = StockFactory(store=manager_profile.store, quantity=10)
        resp = api_client.patch(
            f"{self.url_list}{stock.id}/",
            {"quantity": 99},
            content_type="application/json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["quantity"] == 99

    def test_manager_can_delete_own_store_stock(self, api_client):
        manager_profile = ManagerStaffFactory()
        force_login(api_client, manager_profile.user)
        stock = StockFactory(store=manager_profile.store)
        resp = api_client.delete(f"{self.url_list}{stock.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_customer_cannot_create_stock(self, api_client):
        customer = UserFactory(role=Role.CUSTOMER)
        force_login(api_client, customer)
        product = ProductFactory()
        store = StoreFactory()
        payload = {"store": str(store.id), "product": str(product.id), "quantity": 10}
        resp = api_client.post(self.url_list, payload, content_type="application/json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
