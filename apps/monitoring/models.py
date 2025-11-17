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
