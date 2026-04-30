"""
apps/sales/admin.py — Django admin registration for Sales models.
"""
from django.contrib import admin

from .models import Customer, Order, OrderItem, Staff, Store


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("line_total",)
    fields = ("product", "quantity", "list_price", "discount", "line_total")


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "state", "phone")
    search_fields = ("name", "city")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "city", "state")
    search_fields = ("first_name", "last_name", "email")
    list_select_related = ("user",)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "store", "manager", "active")
    list_filter = ("store", "active")
    search_fields = ("first_name", "last_name", "email")
    list_select_related = ("user", "store", "manager")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "customer", "store", "status", "order_date")
    list_filter = ("status", "store")
    search_fields = ("customer__email", "customer__last_name")
    list_select_related = ("customer", "store", "staff")
    inlines = [OrderItemInline]
    readonly_fields = ("order_date",)
