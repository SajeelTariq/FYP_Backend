from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScrapingConfigViewSet, ScrapingLogViewSet

router = DefaultRouter()
router.register(r'configs', ScrapingConfigViewSet)
router.register(r'logs', ScrapingLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
