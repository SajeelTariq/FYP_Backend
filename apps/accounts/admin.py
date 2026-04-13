from django.contrib import admin
from .models import Role, RolePermission, UserProfile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_by', 'created_at']
    list_filter = ['created_by']
    search_fields = ['name', 'created_by__username']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'dashboard', 'competitors', 'ai_assistant', 'reports', 'settings']
    list_filter = ['dashboard', 'competitors', 'ai_assistant', 'reports', 'settings']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'user_type', 'created_by', 'is_deleted', 'created_at']
    list_filter = ['user_type', 'is_deleted']
    search_fields = ['user__username', 'user__email', 'created_by__username']
