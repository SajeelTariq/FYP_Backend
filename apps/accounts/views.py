from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from .models import Role, RolePermission, UserProfile
from .serializers import (
    RoleSerializer,
    RolePermissionSerializer,
    UserListSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
)
from .permissions import HasSettingsPermission


# ---------------------------------------------------------------------------
# Role Views
# Accessible by: super_admin + users with settings=True role permission
# Scoped to:     roles created by the current user
# ---------------------------------------------------------------------------

class RoleListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def get(self, request):
        if request.user.profile.user_type == 'super_admin':
            roles = Role.objects.all().select_related('permissions')
        else:
            roles = Role.objects.filter(
                created_by=request.user
            ).select_related('permissions')
        return Response(RoleSerializer(roles, many=True).data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            role = serializer.save()
            return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def _get_role(self, pk):
        if self.request.user.profile.user_type == 'super_admin':
            return get_object_or_404(Role, pk=pk)
        return get_object_or_404(Role, pk=pk, created_by=self.request.user)

    def get(self, request, pk):
        return Response(RoleSerializer(self._get_role(pk)).data)

    def put(self, request, pk):
        role = self._get_role(pk)
        serializer = RoleSerializer(role, data=request.data, context={'request': request})
        if serializer.is_valid():
            role = serializer.save()
            return Response(RoleSerializer(role).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self._get_role(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RolePermissionView(APIView):
    """PATCH page-level permissions for a role."""
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def patch(self, request, pk):
        if request.user.profile.user_type == 'super_admin':
            role = get_object_or_404(Role, pk=pk)
        else:
            role = get_object_or_404(Role, pk=pk, created_by=request.user)
        permissions, _ = RolePermission.objects.get_or_create(role=role)
        serializer = RolePermissionSerializer(permissions, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# My Permissions View
# Accessible by: any authenticated user
# Returns:       the logged-in user's own page-level permissions from DB
# ---------------------------------------------------------------------------

class MyPermissionsView(APIView):
    """
    GET /api/accounts/me/permissions/
    Returns the current user's permissions derived from their assigned role.
    No special permission required — every logged-in user can call this.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'User profile not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if profile.user_type == 'super_admin':
            return Response({
                'dashboard': True,
                'competitors': True,
                'ai_assistant': True,
                'reports': True,
                'settings': True,
                'user_type': 'super_admin',
            })

        if profile.role is None:
            return Response({
                'dashboard': False,
                'competitors': False,
                'ai_assistant': False,
                'reports': False,
                'settings': False,
                'user_type': profile.user_type,
            })

        try:
            perms = profile.role.permissions
            return Response({
                'dashboard': perms.dashboard,
                'competitors': perms.competitors,
                'ai_assistant': perms.ai_assistant,
                'reports': perms.reports,
                'settings': perms.settings,
                'user_type': profile.user_type,
            })
        except RolePermission.DoesNotExist:
            return Response({
                'dashboard': False,
                'competitors': False,
                'ai_assistant': False,
                'reports': False,
                'settings': False,
                'user_type': profile.user_type,
            })


# ---------------------------------------------------------------------------
# User Views
# Accessible by: super_admin + users with settings=True role permission
# Scoped to:     users created by the current user (created_by=request.user)
#                — an admin cannot see other admins' users
# ---------------------------------------------------------------------------

class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def get(self, request):
        utype = request.user.profile.user_type
        if utype == 'super_admin':
            profiles = UserProfile.objects.filter(
                is_deleted=False
            ).select_related('user', 'role')
        else:
            profiles = UserProfile.objects.filter(
                created_by=request.user, is_deleted=False
            ).select_related('user', 'role')
        users = [p.user for p in profiles]
        return Response(UserListSerializer(users, many=True).data)

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, HasSettingsPermission]

    def _get_profile(self, pk):
        if self.request.user.profile.user_type == 'super_admin':
            return get_object_or_404(UserProfile, user__pk=pk, is_deleted=False)
        return get_object_or_404(
            UserProfile, user__pk=pk, created_by=self.request.user, is_deleted=False
        )

    def get(self, request, pk):
        return Response(UserListSerializer(self._get_profile(pk).user).data)

    def put(self, request, pk):
        user = self._get_profile(pk).user
        serializer = UserUpdateSerializer(
            data=request.data,
            context={'request': request, 'user_instance': user},
        )
        if serializer.is_valid():
            user = serializer.update(user, serializer.validated_data)
            return Response(UserListSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Soft delete — sets is_deleted=True, does NOT remove from DB."""
        self._get_profile(pk).soft_delete()
        return Response({'detail': 'User deleted successfully.'}, status=status.HTTP_200_OK)
