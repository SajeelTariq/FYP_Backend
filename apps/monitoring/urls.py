from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompetitorViewSet, MonitoringTaskViewSet, 
    ExtractedLinksViewSet, FilteredLinksViewSet, 
    DailyScraperLinksViewSet, CompetitorHTMLViewSet, 
    CompetitorMetadataViewSet, HTMLSnapshotViewSet, HTMLDifferenceViewSet,
    RegisterView, LoginView, LogoutView
)

router = DefaultRouter()
router.register(r'competitors', CompetitorViewSet, basename='competitor')
router.register(r'tasks', MonitoringTaskViewSet, basename='monitoring-task')
router.register(r'extracted-links', ExtractedLinksViewSet, basename='extracted-links')
router.register(r'filtered-links', FilteredLinksViewSet, basename='filtered-links')
router.register(r'daily-scraper-links', DailyScraperLinksViewSet, basename='daily-scraper-links')
router.register(r'html-content', CompetitorHTMLViewSet, basename='html-content')
router.register(r'metadata', CompetitorMetadataViewSet, basename='metadata')
router.register(r'html-snapshots', HTMLSnapshotViewSet, basename='html-snapshots')
router.register(r'html-differences', HTMLDifferenceViewSet, basename='html-differences')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('', include(router.urls)),
]
