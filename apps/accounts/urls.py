from django.urls import path
from . import views

urlpatterns = [
    # ------------------------------------------------------------------
    # Current user's own permissions (no special permission required)
    # GET  /api/accounts/me/permissions/  → returns own role permissions
    # ------------------------------------------------------------------
    path('me/permissions/', views.MyPermissionsView.as_view(), name='my-permissions'),

    # ------------------------------------------------------------------
    # Role endpoints
    # POST   /api/accounts/roles/                  → create role
    # GET    /api/accounts/roles/                  → list my roles
    # GET    /api/accounts/roles/{id}/             → get role
    # PUT    /api/accounts/roles/{id}/             → update role
    # DELETE /api/accounts/roles/{id}/             → delete role
    # PATCH  /api/accounts/roles/{id}/permissions/ → toggle page permissions
    # ------------------------------------------------------------------
    path('roles/', views.RoleListCreateView.as_view(), name='role-list-create'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role-detail'),
    path('roles/<int:pk>/permissions/', views.RolePermissionView.as_view(), name='role-permissions'),

    # ------------------------------------------------------------------
    # User endpoints
    # POST   /api/accounts/users/       → create user
    # GET    /api/accounts/users/       → list my users (non-deleted)
    # GET    /api/accounts/users/{id}/  → get user
    # PUT    /api/accounts/users/{id}/  → update user
    # DELETE /api/accounts/users/{id}/  → soft delete user
    # ------------------------------------------------------------------
    path('users/', views.UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
]
