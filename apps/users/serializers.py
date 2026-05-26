"""apps/users/serializers.py — auth serializers."""

from dj_rest_auth.registration.serializers import (
    RegisterSerializer as BaseRegisterSerializer,
)
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "date_joined",
        ]
        read_only_fields = ["id", "role", "date_joined"]


class RegisterSerializer(BaseRegisterSerializer):
    """Extends dj-rest-auth to capture first/last name on registration."""

    first_name = serializers.CharField(required=False, max_length=150)
    last_name = serializers.CharField(required=False, max_length=150)
    username = None  # remove username field

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data["first_name"] = self.validated_data.get("first_name", "")
        data["last_name"] = self.validated_data.get("last_name", "")
        return data

    def save(self, request):  # type: ignore[override]
        user = super().save(request)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.save(update_fields=["first_name", "last_name"])
        return user
