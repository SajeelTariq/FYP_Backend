from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.monitoring.models import Competitor
from .models import SocialMediaPost, JobPosting, SocialMediaSnapshot
from .serializers import (
    SocialMediaPostSerializer,
    JobPostingSerializer,
    SocialMediaSnapshotSerializer,
)


class SocialMediaPostViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SocialMediaPostSerializer

    def get_queryset(self):
        qs = SocialMediaPost.objects.filter(
            competitor__user=self.request.user,
            competitor__is_deleted=False,
        ).select_related('competitor')

        competitor_id = self.request.query_params.get('competitor')
        platform = self.request.query_params.get('platform')
        post_type = self.request.query_params.get('post_type')

        if competitor_id:
            qs = qs.filter(competitor_id=competitor_id)
        if platform:
            qs = qs.filter(platform=platform)
        if post_type:
            qs = qs.filter(post_type=post_type)

        return qs


class JobPostingViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JobPostingSerializer

    def get_queryset(self):
        qs = JobPosting.objects.filter(
            competitor__user=self.request.user,
            competitor__is_deleted=False,
        ).select_related('competitor')

        competitor_id = self.request.query_params.get('competitor')
        is_new = self.request.query_params.get('is_new')
        is_active = self.request.query_params.get('is_active')

        if competitor_id:
            qs = qs.filter(competitor_id=competitor_id)
        if is_new is not None:
            qs = qs.filter(is_new=is_new.lower() == 'true')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        return qs

    @action(detail=False, methods=['get'])
    def new_today(self, request):
        """Return jobs flagged as new (first seen on last scrape)."""
        qs = self.get_queryset().filter(is_new=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class SocialMediaSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SocialMediaSnapshotSerializer

    def get_queryset(self):
        qs = SocialMediaSnapshot.objects.filter(
            competitor__user=self.request.user,
            competitor__is_deleted=False,
        ).select_related('competitor')

        competitor_id = self.request.query_params.get('competitor')
        platform = self.request.query_params.get('platform')

        if competitor_id:
            qs = qs.filter(competitor_id=competitor_id)
        if platform:
            qs = qs.filter(platform=platform)

        return qs


class LinkedInTriggerViewSet(viewsets.ViewSet):
    """Manual trigger endpoints for LinkedIn scraping (for testing without cron)."""
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='scrape-linkedin')
    def scrape_linkedin(self, request, pk=None):
        """
        POST /api/social-media/trigger/{competitor_id}/scrape-linkedin/
        Queues a LinkedIn scrape for the given competitor immediately.
        """
        try:
            competitor = Competitor.objects.get(
                id=pk,
                user=request.user,
                is_deleted=False,
            )
        except Competitor.DoesNotExist:
            return Response(
                {"error": "Competitor not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not competitor.linkedin_url:
            return Response(
                {"error": "This competitor has no LinkedIn URL set."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import scrape_linkedin_for_competitor
        task = scrape_linkedin_for_competitor.delay(competitor.id)

        return Response({
            "message": f"LinkedIn scrape queued for '{competitor.name}'.",
            "task_id": task.id,
            "competitor_id": competitor.id,
            "linkedin_url": competitor.linkedin_url,
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'], url_path='scrape-all-linkedin')
    def scrape_all_linkedin(self, request):
        """
        POST /api/social-media/trigger/scrape-all-linkedin/
        Queues a full LinkedIn scrape for all competitors of the current user.
        """
        from .tasks import run_linkedin_monitoring
        task = run_linkedin_monitoring.delay()

        return Response({
            "message": "LinkedIn scrape queued for all competitors.",
            "task_id": task.id,
        }, status=status.HTTP_202_ACCEPTED)
