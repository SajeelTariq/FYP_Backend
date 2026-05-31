"""
Section 7 — Job Postings & Hiring Signals  (DB only)
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.monitoring.models import Competitor
from apps.social_media.models import JobPosting


def _user_competitor_ids(user):
    return Competitor.objects.filter(user=user, is_deleted=False).values_list('id', flat=True)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_openings(request):
    """7.1 — Active Openings Per Competitor"""
    comp_ids = _user_competitor_ids(request.user)
    data = (
        JobPosting.objects
        .filter(competitor_id__in=comp_ids, is_active=True)
        .values('competitor_id', 'competitor__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    total = sum(r['count'] for r in data)
    return Response({
        "total_active": total,
        "competitors": [
            {"competitor_id": r['competitor_id'], "name": r['competitor__name'], "active_openings": r['count']}
            for r in data
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hiring_trend(request):
    """7.2 — Hiring Trend Over Time"""
    weeks = int(request.query_params.get('weeks', 12))
    cutoff = timezone.now() - timedelta(weeks=weeks)
    comp_ids = _user_competitor_ids(request.user)

    qs = JobPosting.objects.filter(competitor_id__in=comp_ids, posted_at__gte=cutoff)
    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = (
        qs
        .annotate(week=TruncWeek('posted_at'))
        .values('week', 'competitor_id', 'competitor__name')
        .annotate(
            new_postings=Count('id', filter=Q(is_new=True)),
            total=Count('id'),
        )
        .order_by('week')
    )
    return Response({
        "series": [
            {
                "week": r['week'].date().isoformat() if r['week'] else None,
                "competitor_id": r['competitor_id'],
                "name": r['competitor__name'],
                "new_postings": r['new_postings'],
                "total": r['total'],
            }
            for r in data
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def function_breakdown(request):
    """7.3 — Job Function Breakdown"""
    comp_ids = _user_competitor_ids(request.user)
    qs = JobPosting.objects.filter(competitor_id__in=comp_ids, is_active=True)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = list(qs.values('job_function').annotate(count=Count('id')).order_by('-count'))
    return Response({"breakdown": data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seniority_distribution(request):
    """7.4 — Seniority Distribution"""
    comp_ids = _user_competitor_ids(request.user)
    qs = JobPosting.objects.filter(competitor_id__in=comp_ids, is_active=True)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = list(qs.values('seniority_level').annotate(count=Count('id')).order_by('-count'))
    return Response({"breakdown": data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_locations(request):
    """7.5 — Top Hiring Locations"""
    limit = int(request.query_params.get('limit', 10))
    comp_ids = _user_competitor_ids(request.user)
    qs = JobPosting.objects.filter(competitor_id__in=comp_ids, is_active=True)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = list(qs.values('location').annotate(count=Count('id')).order_by('-count')[:limit])
    return Response({"locations": data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def new_vs_closed(request):
    """7.6 — New vs Closed Jobs Ratio"""
    months = int(request.query_params.get('months', 3))
    cutoff = timezone.now() - timedelta(days=months * 30)
    comp_ids = _user_competitor_ids(request.user)

    qs_base = JobPosting.objects.filter(competitor_id__in=comp_ids, posted_at__gte=cutoff)
    new_count = qs_base.filter(is_new=True).count()
    closed_count = qs_base.filter(is_active=False).count()

    ratio = round(new_count / closed_count, 2) if closed_count else None
    if new_count == 0 and closed_count == 0:
        signal = "no_data"
    elif ratio is None:
        signal = "growing"
    elif ratio > 1.2:
        signal = "growing"
    elif ratio >= 0.8:
        signal = "stable"
    else:
        signal = "consolidating"

    return Response({
        "period_months": months,
        "new_jobs": new_count,
        "closed_jobs": closed_count,
        "ratio": ratio,
        "signal": signal,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employment_type(request):
    """7.7 — Employment Type Split"""
    comp_ids = _user_competitor_ids(request.user)
    qs = JobPosting.objects.filter(competitor_id__in=comp_ids, is_active=True)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = list(qs.values('employment_type').annotate(count=Count('id')).order_by('-count'))
    return Response({"breakdown": data})
