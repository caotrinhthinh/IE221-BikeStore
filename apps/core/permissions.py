"""apps/core/permissions.py — custom DRF permissions."""

from rest_framework import permissions

from apps.users.models import Role


class IsStoreManager(permissions.BasePermission):
    """
    Allows access only to users with role STORE_MANAGER (or ADMIN).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in [Role.STORE_MANAGER, Role.ADMIN]


class IsStaffOfStore(permissions.BasePermission):
    """
    Object-level permission to only allow staff of the same store to access the object.
    Object must have a 'store_id' attribute or property.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admins can access everything
        if request.user.role == Role.ADMIN:
            return True

        # User must have a staff profile linked to a store
        if not hasattr(request.user, "staff_profile"):
            return False

        return request.user.staff_profile.store_id == obj.store_id


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to access it.
    Assumes the model instance has an `email` or `user` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.role == Role.ADMIN:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user
        elif hasattr(obj, "email"):
            return obj.email == request.user.email
        return False
