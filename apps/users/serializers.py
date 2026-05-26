"""apps/users/serializers.py — auth serializers."""

from dj_rest_auth.registration.serializers import (
    RegisterSerializer as BaseRegisterSerializer,
)
from dj_rest_auth.serializers import LoginSerializer as DjRestAuthLoginSerializer
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

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


class CustomLoginSerializer(DjRestAuthLoginSerializer):
    """
    Overrides dj-rest-auth's LoginSerializer to raise AuthenticationFailed (401)
    instead of ValidationError (400) when login fails due to bad credentials or inactive user.
    """

    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except serializers.ValidationError as e:
            if isinstance(e.detail, list):
                err_strs = [str(err) for err in e.detail]
                non_field_errors = e.detail
            elif isinstance(e.detail, dict):
                non_field_errors = e.detail.get("non_field_errors", [])
                err_strs = [str(err) for err in non_field_errors]
            else:
                err_strs = [str(e.detail)]
                non_field_errors = [e.detail]

            target_phrases = [
                "Unable to log in with provided credentials.",
                "User account is disabled.",
                str(_("Unable to log in with provided credentials.")),
                str(_("User account is disabled.")),
            ]

            if any(any(phrase in err for phrase in target_phrases) for err in err_strs):
                raise AuthenticationFailed(detail=non_field_errors) from e
            raise e
