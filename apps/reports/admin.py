from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'report_type', 'status', 'period_start', 'period_end', 'created_at']
    list_filter = ['report_type', 'status']
    search_fields = ['user__username']
    readonly_fields = ['content', 'created_at', 'completed_at']
