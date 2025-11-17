from django.db import models
from apps.monitoring.models import Competitor


class ScrapingConfig(models.Model):
    """Configuration for scraping tasks."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='scraping_configs')
    target_url = models.URLField()
    scraping_frequency = models.CharField(max_length=20, default='daily')  # hourly, daily, weekly
    selectors = models.JSONField(default=dict, help_text="CSS selectors for scraping")
    headers = models.JSONField(default=dict, help_text="HTTP headers for requests")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Scraping Config'
        verbose_name_plural = 'Scraping Configs'

    def __str__(self):
        return f"{self.competitor.name} - {self.target_url}"


class ScrapingLog(models.Model):
    """Log for scraping operations."""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]

    config = models.ForeignKey(ScrapingConfig, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    items_scraped = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    execution_time = models.FloatField(help_text="Execution time in seconds")
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField()

    class Meta:
        ordering = ['-completed_at']
        verbose_name = 'Scraping Log'
        verbose_name_plural = 'Scraping Logs'

    def __str__(self):
        return f"{self.config.competitor.name} - {self.status} ({self.completed_at})"
