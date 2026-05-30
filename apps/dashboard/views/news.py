"""
Section 6 — News & Correlation
"""
from collections import defaultdict
from datetime import timedelta

from django.db.models import F, Min
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.monitoring.models import Competitor, HTMLDifference, NewsArticle


def _get_competitor(competitor_id, user):
    try:
        return Competitor.objects.get(pk=competitor_id, user=user, is_deleted=False)
    except Competitor.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def news_feed(request):
    """
    6.1 — All Competitors News Feed

    Returns latest news across all user's competitors in one feed,
    sorted by published_at descending.

    Query params:
      ?days=6    (default 6)
      ?page=1    (default 1, 20 articles per page)
    """
    days = int(request.query_params.get('days', 6))
    page = max(1, int(request.query_params.get('page', 1)))
    page_size = 20
    cutoff = timezone.now() - timedelta(days=days)

    competitor_ids = Competitor.objects.filter(
        user=request.user, is_deleted=False
    ).values_list('id', flat=True)

    unique_ids = (
        NewsArticle.objects
        .filter(competitor_id__in=competitor_ids, published_at__gte=cutoff)
        .values('url')
        .annotate(min_id=Min('id'))
        .values_list('min_id', flat=True)
    )

    qs = (
        NewsArticle.objects
        .filter(id__in=unique_ids)
        .order_by('-published_at')
        .values(
            'title', 'source', 'url', 'published_at', 'fetched_at',
            competitor_name=F('competitor__name'),
        )
    )

    total = qs.count()
    offset = (page - 1) * page_size
    articles = list(qs[offset: offset + page_size])

    return Response({
        "days": days,
        "total": total,
        "page": page,
        "page_size": page_size,
        "articles": articles,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def news_correlation(request, competitor_id):
    """
    6.5 — Website Change + News Correlation

    Correlates web changes (DB) with news articles (DB via Google News scraping).

    Query params:
      ?days=60  (default 60)
    """
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    days = int(request.query_params.get('days', 60))
    cutoff = timezone.now() - timedelta(days=days)

    db_changes = (
        HTMLDifference.objects
        .filter(competitor_id=competitor_id, detected_at__gte=cutoff)
        .values('detected_at', 'change_type', 'is_significant', 'llm_summary')
        .order_by('detected_at')
    )

    changes_by_date: dict = defaultdict(list)
    for c in db_changes:
        d = c['detected_at'].date().isoformat()
        changes_by_date[d].append({
            "change_type": c['change_type'],
            "is_significant": c['is_significant'],
            "summary": c['llm_summary'],
        })

    news_by_date: dict = defaultdict(list)
    news_qs = (
        NewsArticle.objects
        .filter(competitor_id=competitor_id, published_at__gte=cutoff)
        .values('title', 'source', 'url', 'published_at')
        .order_by('published_at')
    )
    for a in news_qs:
        d = a['published_at'].date().isoformat()
        news_by_date[d].append({"title": a['title'], "source": a['source'], "url": a['url']})

    all_dates = sorted(set(list(changes_by_date.keys()) + list(news_by_date.keys())))
    timeline = [
        {
            "date": d,
            "web_changes": changes_by_date.get(d, []),
            "news_articles": news_by_date.get(d, []),
            "correlated": bool(
                any(c['is_significant'] for c in changes_by_date.get(d, []))
                and news_by_date.get(d)
            ),
        }
        for d in all_dates
    ]

    return Response({
        "available": True,
        "competitor_id": comp.pk,
        "timeline": timeline,
    })
