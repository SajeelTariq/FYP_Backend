from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Allows access only to super admins."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.user_type == 'super_admin'
        except Exception:
            return False


class HasSettingsPermission(BasePermission):
    """
    Grants access to:
      - Super admins (always allowed)
      - Regular users whose assigned role has settings=True
    This permission controls access to user & role management APIs.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            profile = request.user.profile
            if profile.user_type == 'super_admin':
                return True
            return (
                profile.role is not None
                and hasattr(profile.role, 'permissions')
                and profile.role.permissions.settings is True
            )
        except Exception:
            return False
