"""
Section 4 — Social Media Posts    (DB only)
Section 5 — Follower & Employee Snapshots  (DB only)
"""
from datetime import timedelta

from django.db.models import Count, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import (
    ExtractHour, ExtractWeekDay, TruncWeek,
)
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.monitoring.models import Competitor
from apps.social_media.models import SocialMediaPost, SocialMediaSnapshot

WEEKDAY_LABELS = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday',
                  5: 'Thursday', 6: 'Friday', 7: 'Saturday'}


def _user_competitor_ids(user):
    return Competitor.objects.filter(user=user, is_deleted=False).values_list('id', flat=True)


# ─── Section 4 ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def engagement_per_competitor(request):
    """4.1 — Engagement Per Competitor"""
    days = int(request.query_params.get('days', 30))
    cutoff = timezone.now() - timedelta(days=days)
    comp_ids = _user_competitor_ids(request.user)

    qs = SocialMediaPost.objects.filter(competitor_id__in=comp_ids, posted_at__gte=cutoff)
    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = (
        qs
        .values('competitor_id', 'competitor__name')
        .annotate(
            total_likes=Sum('num_likes'),
            total_comments=Sum('num_comments'),
            total_shares=Sum('num_shares'),
            total_engagement=Sum(F('num_likes') + F('num_comments') + F('num_shares')),
        )
        .order_by('-total_engagement')
    )
    return Response({
        "period_days": days,
        "competitors": [
            {
                "competitor_id": r['competitor_id'],
                "name": r['competitor__name'],
                "total_likes": r['total_likes'] or 0,
                "total_comments": r['total_comments'] or 0,
                "total_shares": r['total_shares'] or 0,
                "total_engagement": r['total_engagement'] or 0,
            }
            for r in data
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def post_volume_trend(request):
    """4.2 — Post Volume Over Time"""
    from datetime import date
    weeks = int(request.query_params.get('weeks', 12))
    cutoff = timezone.now() - timedelta(weeks=weeks)
    comp_ids = _user_competitor_ids(request.user)

    qs = SocialMediaPost.objects.filter(competitor_id__in=comp_ids, posted_at__gte=cutoff)
    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    rows = (
        qs
        .annotate(week=TruncWeek('posted_at'))
        .values('week', 'platform')
        .annotate(count=Count('id'))
        .order_by('week', 'platform')
    )

    # Build pivot: {week_str: {platform: count}}
    pivot = {}
    platforms = set()
    for r in rows:
        w = r['week'].date().isoformat()
        p = r['platform']
        platforms.add(p)
        if w not in pivot:
            pivot[w] = {}
        pivot[w][p] = r['count']

    # Generate all week slots in range (Monday-aligned), zero-fill missing
    all_weeks = []
    today = timezone.now().date()
    # Start from the Monday of the cutoff week
    start = cutoff.date()
    start = start - timedelta(days=start.weekday())
    current = start
    while current <= today:
        all_weeks.append(current.isoformat())
        current += timedelta(weeks=1)

    series = []
    for w in all_weeks:
        for p in sorted(platforms):
            series.append({
                "week": w,
                "platform": p,
                "count": pivot.get(w, {}).get(p, 0),
            })

    return Response({"series": series})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def post_type_distribution(request):
    """4.3 — Post Type Distribution"""
    comp_ids = _user_competitor_ids(request.user)
    qs = SocialMediaPost.objects.filter(competitor_id__in=comp_ids)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    distribution = list(qs.values('post_type').annotate(count=Count('id')))
    total = sum(r['count'] for r in distribution)
    return Response({
        "competitor_id": competitor_id,
        "distribution": distribution,
        "total": total,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_posts(request):
    """4.4 — Top Performing Posts"""
    days = int(request.query_params.get('days', 30))
    page_size = int(request.query_params.get('limit', 8))
    page = max(1, int(request.query_params.get('page', 1)))
    offset = (page - 1) * page_size
    cutoff = timezone.now() - timedelta(days=days)
    comp_ids = _user_competitor_ids(request.user)

    qs = (
        SocialMediaPost.objects
        .filter(competitor_id__in=comp_ids, posted_at__gte=cutoff)
        .annotate(total_engagement=F('num_likes') + F('num_comments') + F('num_shares'))
        .select_related('competitor')
        .order_by('-total_engagement')
    )
    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    total = qs.count()
    return Response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "posts": [
            {
                "id": p.pk,
                "competitor_id": p.competitor_id,
                "competitor_name": p.competitor.name,
                "author_name": p.author_name,
                "platform": p.platform,
                "post_type": p.post_type,
                "post_url": p.post_url,
                "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                "num_likes": p.num_likes,
                "num_comments": p.num_comments,
                "num_shares": p.num_shares,
                "total_engagement": p.total_engagement,
            }
            for p in qs[offset: offset + page_size]
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def posting_frequency_heatmap(request):
    """4.5 — Posting Frequency Heatmap (day × hour)"""
    comp_ids = _user_competitor_ids(request.user)
    qs = SocialMediaPost.objects.filter(competitor_id__in=comp_ids)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = (
        qs
        .annotate(hour=ExtractHour('posted_at'), weekday=ExtractWeekDay('posted_at'))
        .values('weekday', 'hour')
        .annotate(count=Count('id'))
        .order_by('weekday', 'hour')
    )
    return Response({
        "heatmap": [
            {
                "weekday": r['weekday'],
                "weekday_label": WEEKDAY_LABELS.get(r['weekday'], ''),
                "hour": r['hour'],
                "count": r['count'],
            }
            for r in data
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def author_leaderboard(request):
    """4.6 — Author Leaderboard"""
    limit = int(request.query_params.get('limit', 10))
    comp_ids = _user_competitor_ids(request.user)
    qs = SocialMediaPost.objects.filter(competitor_id__in=comp_ids)

    competitor_id = request.query_params.get('competitor_id')
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)

    data = (
        qs
        .values('author_name')
        .annotate(
            post_count=Count('id'),
            total_engagement=Sum(F('num_likes') + F('num_comments') + F('num_shares')),
        )
        .order_by('-total_engagement')
        [:limit]
    )
    return Response({
        "authors": [
            {
                "author_name": r['author_name'],
                "post_count": r['post_count'],
                "total_engagement": r['total_engagement'] or 0,
            }
            for r in data
        ]
    })


# ─── Section 5 ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def follower_growth(request):
    """5.1 — Follower Growth Over Time"""
    months = int(request.query_params.get('months', 6))
    cutoff = timezone.now() - timedelta(days=months * 30)
    comp_ids = _user_competitor_ids(request.user)

    competitor_id = request.query_params.get('competitor_id')
    platform = request.query_params.get('platform')

    qs = SocialMediaSnapshot.objects.filter(
        competitor_id__in=comp_ids,
        recorded_at__gte=cutoff,
    ).order_by('recorded_at')

    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)
    if platform:
        qs = qs.filter(platform=platform)

    return Response({
        "competitor_id": competitor_id,
        "platform": platform,
        "series": [
            {"date": r.recorded_at.date().isoformat(), "follower_count": r.follower_count}
            for r in qs.values_list('recorded_at', 'follower_count', named=True)
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def follower_growth_rate(request):
    """5.2 — Month-over-Month Growth %"""
    platform = request.query_params.get('platform', 'linkedin')
    comp_ids = _user_competitor_ids(request.user)
    cutoff = timezone.now() - timedelta(days=45)

    competitors = Competitor.objects.filter(id__in=comp_ids)
    result = []

    for comp in competitors:
        snaps = (
            SocialMediaSnapshot.objects
            .filter(competitor=comp, platform=platform, recorded_at__gte=cutoff)
            .order_by('recorded_at')
        )
        if snaps.count() < 2:
            continue
        previous = snaps.first()
        current = snaps.last()
        if not previous.follower_count or not current.follower_count:
            continue
        growth = ((current.follower_count - previous.follower_count) / previous.follower_count) * 100
        result.append({
            "competitor_id": comp.pk,
            "name": comp.name,
            "current_followers": current.follower_count,
            "previous_followers": previous.follower_count,
            "growth_pct": round(growth, 2),
            "direction": "up" if growth > 0 else "down",
        })

    return Response({"platform": platform, "competitors": result})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_comparison(request):
    """5.3 — Platform Follower Comparison"""
    comp_ids = _user_competitor_ids(request.user)

    latest = (
        SocialMediaSnapshot.objects
        .filter(competitor=OuterRef('competitor'), platform=OuterRef('platform'))
        .order_by('-recorded_at')
        .values('id')[:1]
    )
    snapshots = (
        SocialMediaSnapshot.objects
        .filter(id__in=Subquery(latest), competitor_id__in=comp_ids)
        .values('competitor_id', 'competitor__name', 'platform', 'follower_count')
    )

    # Group by competitor
    grouped = {}
    for s in snapshots:
        cid = s['competitor_id']
        if cid not in grouped:
            grouped[cid] = {"competitor_id": cid, "name": s['competitor__name'], "platforms": {}}
        grouped[cid]['platforms'][s['platform']] = s['follower_count']

    return Response({"competitors": list(grouped.values())})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def follower_employee_ratio(request):
    """5.4 — Follower-to-Employee Ratio"""
    comp_ids = _user_competitor_ids(request.user)

    latest = (
        SocialMediaSnapshot.objects
        .filter(competitor=OuterRef('competitor'), platform=OuterRef('platform'))
        .order_by('-recorded_at')
        .values('id')[:1]
    )
    snapshots = (
        SocialMediaSnapshot.objects
        .filter(id__in=Subquery(latest), competitor_id__in=comp_ids)
        .values('competitor_id', 'competitor__name', 'follower_count', 'employee_count')
    )

    result = []
    for s in snapshots:
        fc = s['follower_count'] or 0
        ec = s['employee_count'] or 0
        ratio = round(fc / ec, 2) if ec else None
        result.append({
            "competitor_id": s['competitor_id'],
            "name": s['competitor__name'],
            "follower_count": fc,
            "employee_count": ec,
            "ratio": ratio,
        })

    return Response({"competitors": sorted(result, key=lambda x: x['ratio'] or 0, reverse=True)})
