from django.contrib import admin
from .models import ScrapingConfig, ScrapingLog


@admin.register(ScrapingConfig)
class ScrapingConfigAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'target_url', 'scraping_frequency', 'is_active', 'created_at']
    list_filter = ['is_active', 'scraping_frequency', 'created_at']
    search_fields = ['competitor__name', 'target_url']


@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    list_display = ['config', 'status', 'items_scraped', 'execution_time', 'completed_at']
    list_filter = ['status', 'completed_at']
    search_fields = ['config__competitor__name']
