"""
Section 8 — Metrics & Trend Analysis  (DB only)
"""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.analytics.models import CompetitorMetrics, TrendAnalysis
from apps.monitoring.models import Competitor


def _user_competitor_ids(user):
    return Competitor.objects.filter(user=user, is_deleted=False).values_list('id', flat=True)


def _confidence_label(score):
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _alert_label(competitor_name, trend_direction, trend_type):
    readable = trend_type.replace('_', ' ')
    direction_text = "surging" if trend_direction == "up" else "declining"
    return f"{competitor_name} {readable} {direction_text} with high confidence"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def direction_summary(request):
    """8.1 — Trend Direction Summary"""
    comp_ids = _user_competitor_ids(request.user)
    data = (
        TrendAnalysis.objects
        .filter(competitor_id__in=comp_ids)
        .values('trend_direction')
        .annotate(count=Count('id'))
    )
    summary = [{"direction": r['trend_direction'], "count": r['count']} for r in data]
    total = sum(r['count'] for r in summary)
    return Response({"summary": summary, "total": total})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def metric_series(request):
    """8.2 — Metric Value Over Time"""
    comp_ids = _user_competitor_ids(request.user)
    competitor_id = request.query_params.get('competitor_id')
    metric_type = request.query_params.get('metric_type')
    months = int(request.query_params.get('months', 6))
    cutoff = (timezone.now() - timedelta(days=months * 30)).date()

    available_metrics = list(
        CompetitorMetrics.objects
        .filter(competitor_id__in=comp_ids)
        .values_list('metric_type', flat=True)
        .distinct()
    )

    qs = CompetitorMetrics.objects.filter(competitor_id__in=comp_ids, date__gte=cutoff)
    if competitor_id:
        qs = qs.filter(competitor_id=competitor_id)
    if metric_type:
        qs = qs.filter(metric_type=metric_type)

    series = [
        {"date": r.date.isoformat(), "value": r.metric_value}
        for r in qs.order_by('date')
    ]
    return Response({
        "competitor_id": competitor_id,
        "metric_type": metric_type,
        "available_metrics": available_metrics,
        "series": series,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def confidence_table(request):
    """8.3 — Confidence Score Table"""
    comp_ids = _user_competitor_ids(request.user)
    min_confidence = float(request.query_params.get('min_confidence', 0.0))

    data = (
        TrendAnalysis.objects
        .filter(competitor_id__in=comp_ids, confidence_score__gte=min_confidence)
        .select_related('competitor')
        .order_by('-confidence_score')
        .values(
            'competitor__name', 'competitor_id',
            'trend_type', 'trend_direction',
            'confidence_score', 'period_start', 'period_end',
        )
    )
    return Response({
        "trends": [
            {
                "competitor_id": r['competitor_id'],
                "competitor_name": r['competitor__name'],
                "trend_type": r['trend_type'],
                "trend_direction": r['trend_direction'],
                "confidence_score": r['confidence_score'],
                "period_start": r['period_start'].isoformat() if r['period_start'] else None,
                "period_end": r['period_end'].isoformat() if r['period_end'] else None,
                "confidence_label": _confidence_label(r['confidence_score']),
            }
            for r in data
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def high_confidence_alerts(request):
    """8.4 — High-Confidence Alerts"""
    comp_ids = _user_competitor_ids(request.user)
    data = (
        TrendAnalysis.objects
        .filter(
            competitor_id__in=comp_ids,
            confidence_score__gte=0.8,
            trend_direction__in=['up', 'down'],
        )
        .select_related('competitor')
        .order_by('-confidence_score')
    )
    return Response({
        "alerts": [
            {
                "competitor_id": t.competitor_id,
                "competitor_name": t.competitor.name,
                "trend_type": t.trend_type,
                "trend_direction": t.trend_direction,
                "confidence_score": t.confidence_score,
                "period_start": t.period_start.isoformat() if t.period_start else None,
                "period_end": t.period_end.isoformat() if t.period_end else None,
                "alert_label": _alert_label(t.competitor.name, t.trend_direction, t.trend_type),
            }
            for t in data
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trend_coverage(request):
    """8.5 — Trend Period Coverage (Gantt data)"""
    comp_ids = _user_competitor_ids(request.user)
    data = (
        TrendAnalysis.objects
        .filter(competitor_id__in=comp_ids)
        .select_related('competitor')
        .values(
            'competitor_id', 'competitor__name',
            'trend_type', 'period_start', 'period_end', 'trend_direction',
        )
        .order_by('competitor_id', 'period_start')
    )
    return Response({
        "coverage": [
            {
                "competitor_id": r['competitor_id'],
                "competitor_name": r['competitor__name'],
                "trend_type": r['trend_type'],
                "period_start": r['period_start'].isoformat() if r['period_start'] else None,
                "period_end": r['period_end'].isoformat() if r['period_end'] else None,
                "trend_direction": r['trend_direction'],
            }
            for r in data
        ]
    })
