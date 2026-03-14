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
        role = get_object_or_404(Role, pk=pk, created_by=request.user)
        permissions, _ = RolePermission.objects.get_or_create(role=role)
        serializer = RolePermissionSerializer(permissions, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
