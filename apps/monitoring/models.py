from django.db import models
from django.contrib.auth.models import User


class Competitor(models.Model):
    """Model to store competitor information."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='competitors')
    name = models.CharField(max_length=255)
    website_base_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    change_count = models.PositiveIntegerField(default=0, help_text="Running total of detected changes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Competitor'
        verbose_name_plural = 'Competitors'
        unique_together = [['user', 'website_base_url']]
        indexes = [
            models.Index(fields=['user', 'is_deleted']),
            models.Index(fields=['website_base_url']),
        ]

    def __str__(self):
        return f"{self.name} - {self.user.username}"


class MonitoringTask(models.Model):
    """Model to track monitoring tasks."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='monitoring_tasks')
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_at']
        verbose_name = 'Monitoring Task'
        verbose_name_plural = 'Monitoring Tasks'

    def __str__(self):
        return f"{self.competitor.name} - {self.task_type} ({self.status})"


class ExtractedLinks(models.Model):
    """Model to store extracted subpage URLs from competitor websites."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='extracted_links')
    links = models.JSONField(default=list, help_text="List of extracted URLs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Extracted Links'
        verbose_name_plural = 'Extracted Links'

    def __str__(self):
        return f"{self.competitor.name} - {len(self.links)} links"


class FilteredLinks(models.Model):
    """Model to store filtered/relevant links from extracted links."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='filtered_links')
    links = models.JSONField(default=list, help_text="List of filtered URLs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Filtered Links'
        verbose_name_plural = 'Filtered Links'

    def __str__(self):
        return f"{self.competitor.name} - {len(self.links)} filtered links"


class DailyScraperLinks(models.Model):
    """Model to store daily scraping links."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='daily_scraper_links')
    links = models.JSONField(default=list, help_text="Links to scrape daily")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Daily Scraper Links'
        verbose_name_plural = 'Daily Scraper Links'

    def __str__(self):
        return f"{self.competitor.name} - Daily scraping"


class CompetitorHTML(models.Model):
    """Model to store HTML content from scraped pages."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='html_content')
    url = models.URLField()
    html_content = models.TextField(help_text="Raw HTML content")
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scraped_at']
        verbose_name = 'Competitor HTML'
        verbose_name_plural = 'Competitor HTML'
        indexes = [
            models.Index(fields=['competitor', '-scraped_at']),
            models.Index(fields=['url']),
        ]

    def __str__(self):
        return f"{self.competitor.name} - {self.url}"


class CompetitorMetadata(models.Model):
    """Model to store extracted metadata for RAG."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='metadata')
    url = models.URLField()
    metadata = models.JSONField(default=dict, help_text="Extracted metadata for RAG")
    extracted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-extracted_at']
        verbose_name = 'Competitor Metadata'
        verbose_name_plural = 'Competitor Metadata'
        indexes = [
            models.Index(fields=['competitor', '-extracted_at']),
        ]

    def __str__(self):
        return f"{self.competitor.name} - Metadata"


class HTMLSnapshot(models.Model):
    """Model to store HTML snapshots for change tracking."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='html_snapshots')
    url = models.URLField()
    html_content = models.TextField(help_text="Full HTML content snapshot")
    content_hash = models.CharField(max_length=64, help_text="SHA256 hash of content for quick comparison")
    snapshot_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-snapshot_at']
        verbose_name = 'HTML Snapshot'
        verbose_name_plural = 'HTML Snapshots'
        indexes = [
            models.Index(fields=['competitor', 'url', '-snapshot_at']),
            models.Index(fields=['content_hash']),
        ]

    def __str__(self):
        return f"{self.competitor.name} - {self.url} ({self.snapshot_at})"


class HTMLDifference(models.Model):
    """Model to track HTML differences between snapshots."""
    CHANGE_TYPE_CHOICES = [
        ('added', 'Content Added'),
        ('removed', 'Content Removed'),
        ('modified', 'Content Modified'),
    ]

    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='html_differences')
    url = models.URLField()
    old_snapshot = models.ForeignKey(
        HTMLSnapshot, 
        on_delete=models.CASCADE, 
        related_name='differences_as_old',
        null=True,
        blank=True
    )
    new_snapshot = models.ForeignKey(
        HTMLSnapshot, 
        on_delete=models.CASCADE, 
        related_name='differences_as_new'
    )
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    diff_summary = models.JSONField(
        default=dict, 
        help_text="Summary of changes: added_sections, removed_sections, modified_sections"
    )
    detailed_diff = models.JSONField(
        default=list,
        help_text="Detailed line-by-line or block-by-block differences"
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    is_significant = models.BooleanField(
        default=False, 
        help_text="Whether this change is significant enough for RAG update"
    )
    llm_summary = models.TextField(
        blank=True,
        default='',
        help_text="LLM-generated human-readable summary of the changes"
    )

    class Meta:
        ordering = ['-detected_at']
        verbose_name = 'HTML Difference'
        verbose_name_plural = 'HTML Differences'
        indexes = [
            models.Index(fields=['competitor', 'url', '-detected_at']),
            models.Index(fields=['is_significant']),
        ]

    def __str__(self):
        return f"{self.competitor.name} - {self.url} - {self.change_type} ({self.detected_at})"
