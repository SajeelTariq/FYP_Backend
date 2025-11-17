from django.contrib import admin
from .models import CompetitorMetrics, TrendAnalysis


@admin.register(CompetitorMetrics)
class CompetitorMetricsAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'metric_type', 'metric_value', 'date', 'created_at']
    list_filter = ['metric_type', 'date', 'created_at']
    search_fields = ['competitor__name', 'metric_type']


@admin.register(TrendAnalysis)
class TrendAnalysisAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'trend_type', 'trend_direction', 'confidence_score', 'period_start', 'period_end']
    list_filter = ['trend_type', 'trend_direction', 'created_at']
    search_fields = ['competitor__name', 'trend_type']
