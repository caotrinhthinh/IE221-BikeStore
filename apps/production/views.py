"""apps/production/views.py — Production views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsStoreManager
from apps.users.models import Role

from . import cache as production_cache
from . import selectors, services
from .filters import ProductFilter
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductSerializer,
    StockSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Catalog"]),
    retrieve=extend_schema(tags=["Catalog"]),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return selectors.get_category_tree()


@extend_schema_view(
    list=extend_schema(tags=["Catalog"]),
    retrieve=extend_schema(tags=["Catalog"]),
)
class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BrandSerializer

    def get_queryset(self):
        return selectors.get_brand_list()


@extend_schema_view(
    list=extend_schema(tags=["Catalog"]),
    retrieve=extend_schema(tags=["Catalog"]),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["list_price", "model_year", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return selectors.get_product_list()

    @extend_schema(
        tags=["Catalog"],
        parameters=[
            OpenApiParameter("q", str, description="Search text", required=True),
            OpenApiParameter(
                "brand", str, description="Brand UUID facet filter", required=False
            ),
            OpenApiParameter(
                "min_price", str, description="Minimum list price", required=False
            ),
            OpenApiParameter(
                "max_price", str, description="Maximum list price", required=False
            ),
        ],
        responses={200: ProductSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """Product search backed by normal database filters."""
        query = request.query_params.get("q", "").strip()
        if not query:
            raise ValidationError({"q": "Search query is required."})

        brand_id = request.query_params.get("brand")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        queryset = selectors.search_products(
            query=query,
            brand_id=brand_id,
            min_price=min_price,
            max_price=max_price,
        )
        page = self.paginate_queryset(queryset)
        results = page if page is not None else queryset
        serializer = self.get_serializer(results, many=True)
        facets = selectors.get_product_facets(queryset)

        if page is not None:
            response = self.get_paginated_response(serializer.data)
            response.data["facets"] = facets
            response.data["engine"] = "database"
            return response

        return Response(
            {"results": serializer.data, "facets": facets, "engine": "database"}
        )

    @extend_schema(
        tags=["Catalog"],
        parameters=[
            OpenApiParameter(
                "store_id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Store UUID",
                required=True,
            )
        ],
        responses={200: dict},
    )
    @action(detail=False, methods=["get"], url_path=r"catalog/(?P<store_id>[^/.]+)")
    def catalog(self, request, store_id=None):
        """Cached product catalog for one store, including stock quantity."""
        return Response(
            production_cache.get_product_catalog_for_store(store_id=store_id)
        )


@extend_schema_view(
    list=extend_schema(tags=["Catalog"]),
    retrieve=extend_schema(tags=["Catalog"]),
    update=extend_schema(tags=["Catalog"]),
    partial_update=extend_schema(tags=["Catalog"]),
)
class StockViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StockSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), IsStoreManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return selectors.get_no_stock()

        user = self.request.user
        if user.role == Role.ADMIN:
            return selectors.get_all_stock()
        elif hasattr(user, "staff_profile"):
            return selectors.get_stock_for_store(store_id=user.staff_profile.store_id)
        return selectors.get_no_stock()

    def perform_update(self, serializer):
        data = serializer.validated_data
        obj = self.get_object()
        serializer.instance = services.update_stock(
            product_id=str(obj.product_id),
            store_id=str(obj.store_id),
            quantity=data.get("quantity", obj.quantity),
        )
