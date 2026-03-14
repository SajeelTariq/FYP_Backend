from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Role, RolePermission, UserProfile


# ---------------------------------------------------------------------------
# Role & Permissions
# ---------------------------------------------------------------------------

class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ['dashboard', 'competitors', 'ai_assistant', 'reports', 'settings', 'updated_at']
        read_only_fields = ['updated_at']


class RoleSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'name', 'permissions', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        request = self.context.get('request')
        qs = Role.objects.filter(name=value, created_by=request.user)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a role with this name.")
        return value

    def create(self, validated_data):
        role = Role.objects.create(
            created_by=self.context['request'].user,
            **validated_data,
        )
        # Auto-create default permissions (all False)
        RolePermission.objects.create(role=role)
        return role


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role_id = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    is_deleted = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'user_type', 'role_id', 'role_name', 'created_by', 'is_deleted', 'date_joined']

    def get_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_role_id(self, obj):
        try:
            return obj.profile.role.id if obj.profile.role else None
        except Exception:
            return None

    def get_role_name(self, obj):
        try:
            return obj.profile.role.name if obj.profile.role else None
        except Exception:
            return None

    def get_user_type(self, obj):
        try:
            return obj.profile.user_type
        except Exception:
            return None

    def get_is_deleted(self, obj):
        try:
            return obj.profile.is_deleted
        except Exception:
            return False

    def get_created_by(self, obj):
        try:
            cb = obj.profile.created_by
            if cb is None:
                return None
            return {'id': cb.id, 'name': cb.get_full_name() or cb.username}
        except Exception:
            return None


class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.none(), required=False, allow_null=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['role'].queryset = Role.objects.filter(created_by=request.user)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        name = validated_data['name']
        name_parts = name.split(' ', 1)

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else '',
        )

        UserProfile.objects.create(
            user=user,
            role=validated_data.get('role'),
            created_by=request.user,
            user_type='user',
        )
        return user


class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.none(), required=False, allow_null=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            self.fields['role'].queryset = Role.objects.filter(created_by=request.user)

    def validate_email(self, value):
        user_instance = self.context.get('user_instance')
        if User.objects.filter(email=value).exclude(pk=user_instance.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def update(self, instance, validated_data):
        name = validated_data.get('name')
        if name:
            name_parts = name.split(' ', 1)
            instance.first_name = name_parts[0]
            instance.last_name = name_parts[1] if len(name_parts) > 1 else ''

        if 'email' in validated_data:
            instance.email = validated_data['email']
            instance.username = validated_data['email']

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])

        instance.save()

        if 'role' in validated_data:
            instance.profile.role = validated_data['role']
            instance.profile.save()

        return instance
