from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Role(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='created_roles'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'created_by']

    def __str__(self):
        return f"{self.name} (by {self.created_by.username})"


class RolePermission(models.Model):
    role = models.OneToOneField(Role, on_delete=models.CASCADE, related_name='permissions')
    dashboard = models.BooleanField(default=False)
    competitors = models.BooleanField(default=False)
    ai_assistant = models.BooleanField(default=False)
    reports = models.BooleanField(default=False)
    settings = models.BooleanField(default=False)
    alerts = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Permissions for {self.role.name}"


class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('user', 'User'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    # Which admin created/manages this user
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_users',
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='user')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.user_type})"

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()


class AlertPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='alert_preference')
    alert_email = models.EmailField(blank=True, null=True, help_text="Email for alerts (uses account email if blank)")
    notify_website_changes = models.BooleanField(default=True)
    notify_new_jobs = models.BooleanField(default=True)
    notify_follower_change = models.BooleanField(default=True)
    notify_new_pages = models.BooleanField(default=True)
    notify_news_mentions = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AlertPreference({self.user.username})"

    def get_alert_email(self):
        return self.alert_email or None
