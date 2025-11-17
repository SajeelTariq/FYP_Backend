from rest_framework import serializers
from .models import ScrapingConfig, ScrapingLog


class ScrapingConfigSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = ScrapingConfig
        fields = '__all__'


class ScrapingLogSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='config.competitor.name', read_only=True)
    
    class Meta:
        model = ScrapingLog
        fields = '__all__'
