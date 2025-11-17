from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompetitorMetricsViewSet, TrendAnalysisViewSet

router = DefaultRouter()
router.register(r'metrics', CompetitorMetricsViewSet)
router.register(r'trends', TrendAnalysisViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
