from django.db import models
from apps.monitoring.models import Competitor


class CompetitorMetrics(models.Model):
    """Aggregated metrics for competitors."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='metrics')
    metric_type = models.CharField(max_length=50)  # e.g., 'price_change', 'content_update'
    metric_value = models.FloatField()
    metric_metadata = models.JSONField(default=dict, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'competitor']
        verbose_name = 'Competitor Metric'
        verbose_name_plural = 'Competitor Metrics'
        indexes = [
            models.Index(fields=['competitor', 'metric_type', '-date']),
        ]

    def __str__(self):
        return f"{self.competitor.name} - {self.metric_type} ({self.date})"


class TrendAnalysis(models.Model):
    """Analysis of competitor trends over time."""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='trends')
    trend_type = models.CharField(max_length=50)
    trend_direction = models.CharField(
        max_length=20,
        choices=[('up', 'Upward'), ('down', 'Downward'), ('stable', 'Stable')]
    )
    confidence_score = models.FloatField(help_text="Confidence score 0-1")
    analysis_data = models.JSONField(default=dict)
    period_start = models.DateField()
    period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Trend Analysis'
        verbose_name_plural = 'Trend Analyses'

    def __str__(self):
        return f"{self.competitor.name} - {self.trend_type} ({self.trend_direction})"
