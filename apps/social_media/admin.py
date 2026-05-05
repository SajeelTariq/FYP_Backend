from django.contrib import admin
from .models import SocialMediaPost, JobPosting, SocialMediaSnapshot


@admin.register(SocialMediaPost)
class SocialMediaPostAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'platform', 'post_type', 'author_name', 'num_likes', 'posted_at', 'scraped_at']
    list_filter = ['platform', 'post_type', 'competitor']
    search_fields = ['competitor__name', 'content', 'author_name']
    readonly_fields = ['scraped_at']


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'title', 'location', 'seniority_level', 'is_new', 'is_active', 'first_seen_at']
    list_filter = ['is_new', 'is_active', 'competitor', 'seniority_level']
    search_fields = ['competitor__name', 'title', 'location']
    readonly_fields = ['first_seen_at', 'last_seen_at']


@admin.register(SocialMediaSnapshot)
class SocialMediaSnapshotAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'platform', 'follower_count', 'employee_count', 'recorded_at']
    list_filter = ['platform', 'competitor']
    readonly_fields = ['recorded_at']
