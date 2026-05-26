"""apps/production/serializers.py — Production serializers."""

from rest_framework import serializers

from .models import Brand, Category, Product, Stock


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent", "created_at"]
        read_only_fields = ["id", "created_at"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "brand_name",
            "category",
            "category_name",
            "model_year",
            "list_price",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Stock
        fields = ["id", "product", "product_name", "store", "store_name", "quantity"]
        read_only_fields = ["id"]
