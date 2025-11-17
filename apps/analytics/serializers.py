from rest_framework import serializers
from .models import CompetitorMetrics, TrendAnalysis


class CompetitorMetricsSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = CompetitorMetrics
        fields = '__all__'


class TrendAnalysisSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = TrendAnalysis
        fields = '__all__'
