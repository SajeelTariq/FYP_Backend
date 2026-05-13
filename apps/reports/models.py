from django.db import models
from django.contrib.auth.models import User
from apps.monitoring.models import Competitor


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('executive', 'Executive'),
        ('analyst', 'Analyst'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=255, blank=True, default='')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    period_start = models.DateField()
    period_end = models.DateField()
    # Empty = all competitors for this user
    competitors = models.ManyToManyField(Competitor, blank=True, related_name='reports')
    content = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.report_type} ({self.period_start} to {self.period_end})"
