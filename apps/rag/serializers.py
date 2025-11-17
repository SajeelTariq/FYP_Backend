from rest_framework import serializers
from .models import VectorDocument, QueryLog


class VectorDocumentSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(
        source='competitor_data.competitor.name', 
        read_only=True
    )
    
    class Meta:
        model = VectorDocument
        fields = '__all__'


class QueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryLog
        fields = '__all__'


class QueryRequestSerializer(serializers.Serializer):
    """Serializer for RAG query requests."""
    query = serializers.CharField(required=True)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=20)
    similarity_threshold = serializers.FloatField(default=0.7, min_value=0.0, max_value=1.0)
    competitor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Filter by specific competitor IDs"
    )
