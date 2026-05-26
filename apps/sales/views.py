"""apps/sales/views.py — Sales views."""

from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsStaffOfStore
from apps.users.models import Role

from . import selectors, services
from .filters import OrderFilter
from .serializers import (
    CustomerSerializer,
    OrderCreateSerializer,
    OrderItemSerializer,
    OrderSerializer,
    StaffSerializer,
    StoreSerializer,
)
from .services import OrderLineInput


@extend_schema_view(
    list=extend_schema(tags=["Stores"]),
    retrieve=extend_schema(tags=["Stores"]),
)
class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StoreSerializer

    def get_queryset(self):
        return selectors.get_all_stores()


@extend_schema_view(
    list=extend_schema(tags=["Users"]),
    retrieve=extend_schema(tags=["Users"]),
)
class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return selectors.get_all_customers()

        user = self.request.user
        if user.role == Role.ADMIN:
            return selectors.get_all_customers()
        return selectors.get_customers_for_user(user_id=user.pk)


@extend_schema_view(
    list=extend_schema(tags=["Users"]),
    retrieve=extend_schema(tags=["Users"]),
)
class StaffViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return selectors.get_no_staff()

        user = self.request.user
        if user.role == Role.ADMIN:
            return selectors.get_all_staff()
        if hasattr(user, "staff_profile"):
            return selectors.get_staff_for_store(store_id=user.staff_profile.store_id)
        return selectors.get_no_staff()


@extend_schema_view(
    list=extend_schema(tags=["Orders"]),
    retrieve=extend_schema(tags=["Orders"]),
)
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return selectors.get_no_orders()

        user = self.request.user
        if user.role == Role.ADMIN:
            return selectors.get_all_orders()
        elif hasattr(user, "staff_profile"):
            return selectors.get_orders_for_store(store_id=user.staff_profile.store_id)
        elif hasattr(user, "customer_profile"):
            return selectors.get_orders_for_customer(
                customer_id=user.customer_profile.pk
            )
        return selectors.get_no_orders()

    @extend_schema(
        tags=["Orders"], request=OrderCreateSerializer, responses={201: OrderSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        lines = [
            OrderLineInput(
                product_id=line["product_id"],
                quantity=line["quantity"],
                discount=line.get("discount", Decimal("0")),
            )
            for line in data["lines"]
        ]

        order = services.create_order(
            customer_id=data["customer_id"],
            store_id=data["store_id"],
            staff_id=data.get("staff_id"),
            required_date=data.get("required_date"),
            lines=lines,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(tags=["Orders"])
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsStaffOfStore],
    )
    def ship(self, request, pk=None):
        order = self.get_object()
        updated_order = services.ship_order(order_id=order.pk)
        return Response(OrderSerializer(updated_order).data)

    @extend_schema(tags=["Orders"])
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsStaffOfStore],
    )
    def cancel(self, request, pk=None):
        order = self.get_object()
        updated_order = services.cancel_order(order_id=order.pk)
        return Response(OrderSerializer(updated_order).data)

    @extend_schema(tags=["Orders"])
    @action(detail=True, methods=["get"])
    def items(self, request, pk=None):
        order = self.get_object()
        serializer = OrderItemSerializer(
            selectors.get_order_items(order_id=order.pk), many=True
        )
        return Response(serializer.data)
