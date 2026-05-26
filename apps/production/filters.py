"""apps/production/filters.py — Production filters."""

import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="list_price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="list_price", lookup_expr="lte")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Product
        fields = ["brand", "category", "model_year"]
