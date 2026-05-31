"""
Overview endpoint — dashboard summary aggregates.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.monitoring.models import Competitor, HTMLDifference
from apps.social_media.models import JobPosting, SocialMediaPost


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview(request):
    """Overview — aggregated counts for all dashboard sections."""
    comp_ids = list(
        Competitor.objects.filter(user=request.user, is_deleted=False)
        .values_list('id', flat=True)
    )
    cutoff_30 = timezone.now() - timedelta(days=30)

    total_competitors = len(comp_ids)

    web_changes_30d = HTMLDifference.objects.filter(
        competitor_id__in=comp_ids, detected_at__gte=cutoff_30, is_onboarding_snapshot=False
    ).count()

    significant_changes_30d = HTMLDifference.objects.filter(
        competitor_id__in=comp_ids, detected_at__gte=cutoff_30, is_significant=True, is_onboarding_snapshot=False
    ).count()

    active_jobs = JobPosting.objects.filter(competitor_id__in=comp_ids, is_active=True).count()

    social_posts_30d = SocialMediaPost.objects.filter(
        competitor_id__in=comp_ids, posted_at__gte=cutoff_30
    ).count()

    return Response({
        "total_competitors": total_competitors,
        "web_changes_30d": web_changes_30d,
        "significant_changes_30d": significant_changes_30d,
        "active_job_postings": active_jobs,
        "social_posts_30d": social_posts_30d,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scraping_health(request):
    """Scraping health — task/log status summary."""
    from apps.monitoring.models import MonitoringTask
    from apps.scraping.models import ScrapingLog

    comp_ids = list(
        Competitor.objects.filter(user=request.user, is_deleted=False)
        .values_list('id', flat=True)
    )
    cutoff_7d = timezone.now() - timedelta(days=7)

    task_stats = (
        MonitoringTask.objects
        .filter(competitor_id__in=comp_ids, scheduled_at__gte=cutoff_7d)
        .values('status')
        .annotate(count=Count('id'))
    )

    log_stats = (
        ScrapingLog.objects
        .filter(started_at__gte=cutoff_7d)
        .values('status')
        .annotate(count=Count('id'))
    )

    return Response({
        "period_days": 7,
        "monitoring_tasks": {r['status']: r['count'] for r in task_stats},
        "scraping_logs": {r['status']: r['count'] for r in log_stats},
    })
