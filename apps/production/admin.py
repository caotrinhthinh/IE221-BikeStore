"""
apps/production/admin.py — Django admin registration for Production models.
"""
from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import Brand, Category, Product, Stock


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    list_display = ("tree_actions", "indented_title", "slug", "version")
    list_display_links = ("indented_title",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "model_year", "list_price")
    list_filter = ("brand", "category", "model_year")
    search_fields = ("name",)
    list_select_related = ("brand", "category")


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "store", "quantity", "updated_at")
    list_filter = ("store",)
    list_select_related = ("product", "store")
    search_fields = ("product__name", "store__name")
