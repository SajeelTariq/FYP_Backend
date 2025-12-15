from django.contrib import admin
from .models import (
    Competitor, MonitoringTask, ExtractedLinks, 
    FilteredLinks, DailyScraperLinks, CompetitorHTML, CompetitorMetadata,
    HTMLSnapshot, HTMLDifference
)


@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'website_base_url', 'is_deleted', 'created_at']
    list_filter = ['is_deleted', 'created_at', 'user']
    search_fields = ['name', 'website_base_url', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']


@admin.register(MonitoringTask)
class MonitoringTaskAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'task_type', 'status', 'scheduled_at', 'completed_at']
    list_filter = ['status', 'task_type', 'scheduled_at']
    search_fields = ['competitor__name']


@admin.register(ExtractedLinks)
class ExtractedLinksAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'link_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['competitor__name']
    
    def link_count(self, obj):
        return len(obj.links) if obj.links else 0
    link_count.short_description = 'Number of Links'


@admin.register(FilteredLinks)
class FilteredLinksAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'link_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['competitor__name']
    
    def link_count(self, obj):
        return len(obj.links) if obj.links else 0
    link_count.short_description = 'Number of Links'


@admin.register(DailyScraperLinks)
class DailyScraperLinksAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'link_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['competitor__name']
    
    def link_count(self, obj):
        return len(obj.links) if obj.links else 0
    link_count.short_description = 'Number of Links'


@admin.register(CompetitorHTML)
class CompetitorHTMLAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'url', 'html_size', 'scraped_at']
    list_filter = ['scraped_at']
    search_fields = ['competitor__name', 'url']
    
    def html_size(self, obj):
        size = len(obj.html_content) if obj.html_content else 0
        if size > 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        elif size > 1024:
            return f"{size / 1024:.2f} KB"
        return f"{size} bytes"
    html_size.short_description = 'HTML Size'


@admin.register(CompetitorMetadata)
class CompetitorMetadataAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'url', 'extracted_at']
    list_filter = ['extracted_at']
    search_fields = ['competitor__name', 'url']


@admin.register(HTMLSnapshot)
class HTMLSnapshotAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'url', 'content_hash_short', 'html_size', 'snapshot_at']
    list_filter = ['snapshot_at', 'competitor']
    search_fields = ['competitor__name', 'url', 'content_hash']
    readonly_fields = ['snapshot_at', 'content_hash']
    
    def content_hash_short(self, obj):
        return obj.content_hash[:16] + '...' if obj.content_hash else ''
    content_hash_short.short_description = 'Hash'
    
    def html_size(self, obj):
        size = len(obj.html_content) if obj.html_content else 0
        if size > 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        elif size > 1024:
            return f"{size / 1024:.2f} KB"
        return f"{size} bytes"
    html_size.short_description = 'Size'


@admin.register(HTMLDifference)
class HTMLDifferenceAdmin(admin.ModelAdmin):
    list_display = [
        'competitor', 'url', 'change_type', 'is_significant', 
        'total_changes', 'detected_at'
    ]
    list_filter = ['change_type', 'is_significant', 'detected_at', 'competitor']
    search_fields = ['competitor__name', 'url']
    readonly_fields = ['detected_at']
    
    def total_changes(self, obj):
        if obj.diff_summary and isinstance(obj.diff_summary, dict):
            return obj.diff_summary.get('total_changes', 0)
        return 0
    total_changes.short_description = 'Changes'

