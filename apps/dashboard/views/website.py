"""
Section 3 — Website Change Detection  (DB only)
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.monitoring.models import Competitor, HTMLDifference


def _user_competitor_ids(user):
    return Competitor.objects.filter(user=user, is_deleted=False).values_list('id', flat=True)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def change_heatmap(request):
    """3.1 — Change Frequency Heatmap"""
    days = int(request.query_params.get('days', 90))
    cutoff = timezone.now() - timedelta(days=days)
    comp_ids = _user_competitor_ids(request.user)

    qs = HTMLDifference.objects.filter(
        competitor_id__in=comp_ids,
        detected_at__gte=cutoff,
    )
    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = (
        qs
        .annotate(day=TruncDate('detected_at'))
        .values('day', 'competitor_id', 'competitor__name')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    return Response({
        "data": [
            {
                "date": r['day'].isoformat(),
                "competitor_id": r['competitor_id'],
                "competitor_name": r['competitor__name'],
                "count": r['count'],
            }
            for r in data
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def change_type_breakdown(request):
    """3.2 — Change Type Breakdown"""
    comp_ids = _user_competitor_ids(request.user)
    qs = HTMLDifference.objects.filter(competitor_id__in=comp_ids)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    breakdown = list(qs.values('change_type').annotate(count=Count('id')))
    total = sum(r['count'] for r in breakdown)
    return Response({"breakdown": breakdown, "total": total})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def significance_trend(request):
    """3.3 — Significant vs Minor Changes Over Time"""
    weeks = int(request.query_params.get('weeks', 12))
    cutoff = timezone.now() - timedelta(weeks=weeks)
    comp_ids = _user_competitor_ids(request.user)

    qs = HTMLDifference.objects.filter(competitor_id__in=comp_ids, detected_at__gte=cutoff)
    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    rows = (
        qs
        .annotate(week=TruncWeek('detected_at'))
        .values('week', 'is_significant')
        .annotate(count=Count('id'))
        .order_by('week')
    )

    # Pivot significant/minor per week
    pivot = {}
    for r in rows:
        w = r['week'].date().isoformat()
        if w not in pivot:
            pivot[w] = {"week": w, "significant": 0, "minor": 0}
        if r['is_significant']:
            pivot[w]['significant'] += r['count']
        else:
            pivot[w]['minor'] += r['count']

    return Response({"series": sorted(pivot.values(), key=lambda x: x['week'])})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def changes_per_competitor(request):
    """3.4 — Changes Per Competitor"""
    days = int(request.query_params.get('days', 30))
    cutoff = timezone.now() - timedelta(days=days)
    comp_ids = _user_competitor_ids(request.user)

    data = (
        HTMLDifference.objects
        .filter(competitor_id__in=comp_ids, detected_at__gte=cutoff)
        .values('competitor_id', 'competitor__name')
        .annotate(
            total=Count('id'),
            significant=Count('id', filter=Q(is_significant=True)),
        )
        .order_by('-total')
    )
    return Response({
        "competitors": [
            {
                "competitor_id": r['competitor_id'],
                "name": r['competitor__name'],
                "total_changes": r['total'],
                "significant_changes": r['significant'],
            }
            for r in data
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def change_feed(request):
    """3.5 — Recent Changes Activity Feed"""
    comp_ids = _user_competitor_ids(request.user)
    limit = int(request.query_params.get('limit', 20))
    page = int(request.query_params.get('page', 1))
    offset = (page - 1) * limit

    qs = HTMLDifference.objects.filter(competitor_id__in=comp_ids).select_related('competitor')

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    days = request.query_params.get('days')
    if days:
        cutoff = timezone.now() - timedelta(days=int(days))
        qs = qs.filter(detected_at__gte=cutoff)

    category = request.query_params.get('change_category')
    if category:
        qs = qs.filter(change_category=category)

    qs = qs.order_by('-detected_at')

    total = qs.count()
    results = qs[offset: offset + limit]

    base_url = request.build_absolute_uri(request.path)
    next_url = f"{base_url}?page={page+1}&limit={limit}" if offset + limit < total else None
    prev_url = f"{base_url}?page={page-1}&limit={limit}" if page > 1 else None

    return Response({
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": [
            {
                "id": r.pk,
                "competitor_id": r.competitor_id,
                "competitor_name": r.competitor.name,
                "change_type": r.change_type,
                "change_category": r.change_category,
                "is_significant": r.is_significant,
                "detected_at": r.detected_at.isoformat(),
                "llm_summary": r.llm_summary,
            }
            for r in results
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def change_velocity(request):
    """3.6 — Change Velocity (7-day rolling)"""
    days = int(request.query_params.get('days', 60))
    cutoff = timezone.now() - timedelta(days=days + 7)
    comp_ids = _user_competitor_ids(request.user)

    qs = HTMLDifference.objects.filter(competitor_id__in=comp_ids, detected_at__gte=cutoff)
    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    # Build a day → count map first
    daily = (
        qs
        .annotate(day=TruncDate('detected_at'))
        .values('day')
        .annotate(count=Count('id'))
    )
    day_map = {r['day']: r['count'] for r in daily}

    # Rolling 7-day sum for last `days` days
    end = timezone.now().date()
    start = end - timedelta(days=days - 1)
    series = []
    for i in range(days):
        d = start + timedelta(days=i)
        window_sum = sum(
            day_map.get(d - timedelta(days=j), 0) for j in range(7)
        )
        series.append({"date": d.isoformat(), "rolling_7d_count": window_sum})

    return Response({"series": series})
