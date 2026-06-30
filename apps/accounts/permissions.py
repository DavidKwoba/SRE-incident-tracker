from rest_framework.permissions import BasePermission

PLATFORM_ENGINEER_GROUPS = {"platform_engineer", "platform_admin"}
PLATFORM_ADMIN_GROUPS = {"platform_admin"}


class IsReporter(BasePermission):
    """Any authenticated user."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsPlatformEngineer(BasePermission):
    """Members of the platform_engineer or platform_admin group, or staff."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        return request.user.groups.filter(name__in=PLATFORM_ENGINEER_GROUPS).exists()


class IsPlatformAdmin(BasePermission):
    """Members of the platform_admin group, or superusers."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name__in=PLATFORM_ADMIN_GROUPS).exists()
