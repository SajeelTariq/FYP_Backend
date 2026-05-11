"""
URL configuration for competitor monitoring system.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
    path('api/scraping/', include('apps.scraping.urls')),
    path('api/rag/', include('apps.rag.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/social-media/', include('apps.social_media.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
