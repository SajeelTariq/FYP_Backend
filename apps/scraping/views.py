from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ScrapingConfig, ScrapingLog
from .serializers import ScrapingConfigSerializer, ScrapingLogSerializer


class ScrapingConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for scraping configurations."""
    queryset = ScrapingConfig.objects.all()
    serializer_class = ScrapingConfigSerializer
    filterset_fields = ['competitor', 'is_active']
    
    @action(detail=True, methods=['post'])
    def trigger_scraping(self, request, pk=None):
        """Manually trigger scraping for this config."""
        config = self.get_object()
        # Trigger scraping task (will be implemented with Celery)
        return Response({'status': 'Scraping triggered', 'config_id': config.id})


class ScrapingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing scraping logs."""
    queryset = ScrapingLog.objects.all()
    serializer_class = ScrapingLogSerializer
    filterset_fields = ['config', 'status']
