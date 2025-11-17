from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CompetitorMetrics, TrendAnalysis
from .serializers import CompetitorMetricsSerializer, TrendAnalysisSerializer


class CompetitorMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing competitor metrics."""
    queryset = CompetitorMetrics.objects.all()
    serializer_class = CompetitorMetricsSerializer
    filterset_fields = ['competitor', 'metric_type', 'date']
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get metrics summary for all competitors."""
        # TODO: Implement metrics aggregation
        return Response({'message': 'Metrics summary to be implemented'})


class TrendAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing trend analysis."""
    queryset = TrendAnalysis.objects.all()
    serializer_class = TrendAnalysisSerializer
    filterset_fields = ['competitor', 'trend_type', 'trend_direction']
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest trends for all competitors."""
        # TODO: Implement latest trends retrieval
        return Response({'message': 'Latest trends to be implemented'})
