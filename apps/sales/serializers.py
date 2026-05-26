"""apps/sales/serializers.py — Sales serializers."""

from rest_framework import serializers

from .models import Customer, Order, OrderItem, Staff, Store


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name", "phone", "email", "street", "city", "state", "zip_code"]
        read_only_fields = ["id"]


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "street",
            "city",
            "state",
            "zip_code",
        ]
        read_only_fields = ["id", "full_name"]

    def get_full_name(self, obj) -> str:
        return obj.full_name


class StaffSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            "id",
            "store",
            "manager",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "active",
        ]
        read_only_fields = ["id", "full_name"]

    def get_full_name(self, obj) -> str:
        return obj.full_name


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    line_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "list_price",
            "discount",
            "line_total",
        ]
        read_only_fields = ["id", "list_price", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_name",
            "store",
            "store_name",
            "staff",
            "status",
            "order_date",
            "required_date",
            "shipped_date",
            "items",
            "total_amount",
            "items_count",
        ]
        read_only_fields = ["id", "status", "order_date", "shipped_date"]


class OrderLineInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    discount = serializers.DecimalField(
        max_digits=4, decimal_places=2, required=False, default=0
    )


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    store_id = serializers.UUIDField()
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    required_date = serializers.DateField(required=False, allow_null=True)
    lines = OrderLineInputSerializer(many=True, allow_empty=False)

    def validate_lines(self, value):
        if not value:
            raise serializers.ValidationError(
                "An order must have at least one line item."
            )
        return value
