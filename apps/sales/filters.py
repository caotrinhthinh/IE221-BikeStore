"""apps/sales/filters.py — Sales filters."""

import django_filters

from .models import Order


class OrderFilter(django_filters.FilterSet):
    min_date = django_filters.DateFilter(field_name="order_date", lookup_expr="gte")
    max_date = django_filters.DateFilter(field_name="order_date", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ["status", "customer", "store"]
