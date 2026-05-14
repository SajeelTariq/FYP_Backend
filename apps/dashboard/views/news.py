"""
Section 6 — News & Correlation

news_feed, sentiment_trend, press_releases, social_sentiment removed —
those endpoints require a paid FMP plan (402 Payment Required on stable API).

Only news_correlation is kept: it uses HTMLDifference (DB) for web changes
and attempts FMP news as a best-effort overlay. Works fully without FMP news.
"""
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.monitoring.models import Competitor, HTMLDifference, NewsArticle
from apps.dashboard.services.fmp import fmp_get

SIX_HOURS = 60 * 60 * 6


def _get_competitor(competitor_id, user):
    try:
        return Competitor.objects.get(pk=competitor_id, user=user, is_deleted=False)
    except Competitor.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def news_feed(request, competitor_id):
    """
    6.1 — Competitor News Feed

    Returns articles fetched from Google News RSS, stored every 6 hours by Celery.

    Query params:
      ?days=30   (default 30)
      ?page=1    (default 1, 20 articles per page)
    """
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    days = int(request.query_params.get('days', 6))
    page = max(1, int(request.query_params.get('page', 1)))
    page_size = 20
    cutoff = timezone.now() - timedelta(days=days)

    qs = (
        NewsArticle.objects
        .filter(competitor=comp, published_at__gte=cutoff)
        .order_by('-published_at')
        .values('title', 'source', 'url', 'published_at', 'fetched_at')
    )

    total = qs.count()
    offset = (page - 1) * page_size
    articles = list(qs[offset: offset + page_size])

    return Response({
        "competitor_id": comp.pk,
        "competitor_name": comp.name,
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

    Primary data: HTMLDifference records from DB (always available).
    News overlay: attempted via FMP stable/news/stock-latest (requires paid plan).
    If FMP news is unavailable, timeline still returns with empty news_articles
    and news_available=false so the frontend can handle it gracefully.

    Query params:
      ?days=60  (default 60)
    """
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    days = int(request.query_params.get('days', 60))
    cutoff = timezone.now() - timedelta(days=days)
    symbol = getattr(comp, 'stock_symbol', None)

    # ── DB: web changes grouped by date ──────────────────────────────────────
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

    # ── FMP: news best-effort overlay ─────────────────────────────────────────
    news_by_date: dict = defaultdict(list)
    news_available = False

    if symbol:
        try:
            raw, _ = fmp_get(
                "news/stock-latest",
                f"fmp_news_{symbol}_200",
                SIX_HOURS,
                params={"symbols": symbol, "limit": 200},
            )
            for a in (raw or []):
                d = (a.get("publishedDate") or a.get("date") or "")[:10]
                if d:
                    news_by_date[d].append({
                        "title": a.get("title"),
                        "source": a.get("site") or a.get("source"),
                    })
            news_available = True
        except RuntimeError:
            pass

    # ── Merge on shared timeline ───────────────────────────────────────────────
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
        "news_available": news_available,
        "competitor_id": comp.pk,
        "stock_symbol": symbol,
        "timeline": timeline,
    })
