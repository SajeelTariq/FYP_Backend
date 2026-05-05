from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SocialMediaPostViewSet,
    JobPostingViewSet,
    SocialMediaSnapshotViewSet,
    LinkedInTriggerViewSet,
)

router = DefaultRouter()
router.register(r'posts', SocialMediaPostViewSet, basename='social-posts')
router.register(r'jobs', JobPostingViewSet, basename='job-postings')
router.register(r'snapshots', SocialMediaSnapshotViewSet, basename='social-snapshots')
router.register(r'trigger', LinkedInTriggerViewSet, basename='linkedin-trigger')

urlpatterns = [
    path('', include(router.urls)),
]
