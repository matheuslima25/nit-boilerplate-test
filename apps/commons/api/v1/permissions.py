from rest_framework import permissions

from tools.utils import get_user_data


class MineOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        if request.method in ["POST", "PATCH"]:
            if any(key in request.data and request.data[key] == str(request.user.id) for key in
                   ["user", "broker", "agent"]):
                return True
            try:
                instance = view.get_object()
                attributes = ["user", "broker", "agent"]
                if any(hasattr(instance, attr) and getattr(instance, attr) == request.user for attr in attributes):
                    return True
            except Exception:
                return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if request.method in permissions.SAFE_METHODS:
            return True

        profile = get_user_data(request)

        if not profile and not request.user:
            return False

        attributes = ["user", "broker", "agent"]
        if any(hasattr(obj, attr) and getattr(obj, attr) == request.user for attr in attributes):
            return True

        return False
