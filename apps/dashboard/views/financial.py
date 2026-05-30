"""
Financial dashboard views — powered by yfinance (Yahoo Finance).

Section 1 — Competitor Financial Profile
Section 2 — Revenue & Financial Health
"""
import yfinance as yf
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.monitoring.models import Competitor
from apps.social_media.models import SocialMediaSnapshot
from apps.dashboard.services.yfinance_service import yf_fetch, df_to_records

SEVEN_DAYS = 60 * 60 * 24 * 7

INCOME_ROW_MAP = {
    "revenue":          ["Total Revenue"],
    "net_income":       ["Net Income"],
    "gross_profit":     ["Gross Profit"],
    "operating_income": ["Operating Income", "Total Operating Income As Reported"],
}


def _get_competitor(competitor_id, user):
    try:
        return Competitor.objects.get(pk=competitor_id, user=user, is_deleted=False)
    except Competitor.DoesNotExist:
        return None


def _no_symbol():
    return Response({"available": False, "reason": "No stock symbol configured"})


def _yf_error(exc):
    return Response(
        {"error": "Financial data unavailable", "code": "UPSTREAM_ERROR"},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


# ─── Section 1 ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_profile(request, competitor_id):
    """1.1 — Competitor Profile Card"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    try:
        info, stale = yf_fetch(
            f"yf_profile_{symbol}",
            SEVEN_DAYS,
            lambda: yf.Ticker(symbol).info,
        )
    except RuntimeError as e:
        return _yf_error(e)

    if not info or info.get('quoteType') == 'NONE':
        return _no_symbol()

    city = info.get('city', '')
    country = info.get('country', '')
    hq = ', '.join(filter(None, [city, country])) or None

    return Response({
        "available": True,
        "competitor_id": comp.pk,
        "competitor_name": comp.name,
        "stock_symbol": symbol,
        "logo_url": info.get("logo_url"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
        "description": info.get("longBusinessSummary"),
        "headquarters": hq,
        "exchange": info.get("exchange"),
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap"),
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_cap(request, competitor_id):
    """1.2 — Historical Market Cap (approximated as price × shares outstanding)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    years = min(int(request.query_params.get('years', 5)), 10)

    def fetch():
        t = yf.Ticker(symbol)
        shares = t.info.get('sharesOutstanding')
        if not shares:
            return []
        hist = t.history(period=f"{years}y")
        if hist.empty:
            return []
        monthly = {}
        for date, row in hist.iterrows():
            ym = date.strftime('%Y-%m')
            monthly[ym] = {
                "date": date.strftime('%Y-%m-%d'),
                "market_cap": round(row['Close'] * shares),
            }
        return sorted(monthly.values(), key=lambda x: x["date"])

    try:
        series, stale = yf_fetch(f"yf_market_cap_{symbol}_{years}", SEVEN_DAYS, fetch)
    except RuntimeError as e:
        return _yf_error(e)

    return Response({
        "available": True,
        "stock_symbol": symbol,
        "unit": "USD",
        "series": series,
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_count(request, competitor_id):
    """1.3 — Employee Count from LinkedIn snapshots (DB only)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    db_qs = (
        SocialMediaSnapshot.objects
        .filter(competitor_id=competitor_id, platform='linkedin')
        .order_by('recorded_at')
        .values('recorded_at', 'employee_count')
    )
    db_series = [
        {"date": r['recorded_at'].date().isoformat(), "employee_count": r['employee_count']}
        for r in db_qs
    ]

    return Response({"available": True, "series": db_series})


# ─── Section 2 ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def income_statement(request, competitor_id):
    """2.1 — Revenue vs Net Income (annual)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    years = int(request.query_params.get('years', 5))

    def fetch():
        df = yf.Ticker(symbol).income_stmt
        if df is None or df.empty:
            return []
        return df_to_records(df, INCOME_ROW_MAP)

    try:
        series, stale = yf_fetch(f"yf_income_{symbol}", SEVEN_DAYS, fetch)
    except RuntimeError as e:
        return _yf_error(e)

    return Response({
        "available": True,
        "period": "annual",
        "series": series[-years:],
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_growth(request, competitor_id):
    """2.2 — Revenue & Net Income Growth Rate (year-over-year, calculated)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    def fetch():
        df = yf.Ticker(symbol).income_stmt
        if df is None or df.empty:
            return []
        return df_to_records(df, INCOME_ROW_MAP)

    try:
        base_series, stale = yf_fetch(f"yf_income_{symbol}", SEVEN_DAYS, fetch)
    except RuntimeError as e:
        return _yf_error(e)

    def yoy(curr, prev):
        if curr is not None and prev and prev != 0:
            return round((curr - prev) / abs(prev) * 100, 2)
        return None

    growth = []
    for i in range(1, len(base_series)):
        prev, curr = base_series[i - 1], base_series[i]
        growth.append({
            "date": curr["date"],
            "revenue_growth_pct": yoy(curr["revenue"], prev["revenue"]),
            "net_income_growth_pct": yoy(curr["net_income"], prev["net_income"]),
            "gross_profit_growth_pct": yoy(curr["gross_profit"], prev["gross_profit"]),
        })

    return Response({"available": True, "series": growth, "stale": stale})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_ratios(request, competitor_id):
    """2.3 — Financial Ratios"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    try:
        info, stale = yf_fetch(
            f"yf_profile_{symbol}",
            SEVEN_DAYS,
            lambda: yf.Ticker(symbol).info,
        )
    except RuntimeError as e:
        return _yf_error(e)

    return Response({
        "available": True,
        "ratios": {
            "gross_profit_margin":   info.get("grossMargins"),
            "net_profit_margin":     info.get("profitMargins"),
            "return_on_equity":      info.get("returnOnEquity"),
            "return_on_assets":      info.get("returnOnAssets"),
            "price_earnings_ratio":  info.get("trailingPE"),
            "price_to_book_ratio":   info.get("priceToBook"),
            "price_to_sales_ratio":  info.get("priceToSalesTrailing12Months"),
            "debt_to_equity_ratio":  info.get("debtToEquity"),
            "current_ratio":         info.get("currentRatio"),
        },
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_rating(request, competitor_id):
    """2.4 — Derived Financial Health Score"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    try:
        info, stale = yf_fetch(
            f"yf_profile_{symbol}",
            SEVEN_DAYS,
            lambda: yf.Ticker(symbol).info,
        )
    except RuntimeError as e:
        return _yf_error(e)

    def score(value, thresholds):
        if value is None:
            return None
        for i, t in enumerate(thresholds, 1):
            if value <= t:
                return i
        return 5

    roe     = info.get("returnOnEquity")
    roa     = info.get("returnOnAssets")
    debt_eq = info.get("debtToEquity")
    pe      = info.get("trailingPE")
    npm     = info.get("profitMargins")

    roe_s  = score(roe,     [0.05, 0.10, 0.15, 0.20]) if roe is not None else None
    roa_s  = score(roa,     [0.02, 0.05, 0.08, 0.12]) if roa is not None else None
    de_s   = score(debt_eq, [0.3,  0.6,  1.0,  1.5])  if debt_eq is not None else None
    pe_s   = (5 - score(pe, [15, 25, 40, 60]) + 1)     if pe is not None else None
    npm_s  = score(npm,     [0.02, 0.05, 0.10, 0.15])  if npm is not None else None

    scores = [s for s in [roe_s, roa_s, de_s, pe_s, npm_s] if s is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else None

    rating_map = {5: "A", 4: "B+", 3: "B", 2: "C+", 1: "C"}
    rec_map    = {5: "Strong Buy", 4: "Buy", 3: "Hold", 2: "Underperform", 1: "Sell"}
    avg_int = round(avg) if avg is not None else None

    return Response({
        "available": True,
        "rating":         rating_map.get(avg_int, "N/A"),
        "rating_score":   avg,
        "recommendation": rec_map.get(avg_int, "N/A"),
        "sub_scores": {
            "roe_score":           roe_s,
            "roa_score":           roa_s,
            "debt_to_equity_score": de_s,
            "pe_score":            pe_s,
            "net_margin_score":    npm_s,
        },
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_per_employee(request, competitor_id):
    """2.5 — Revenue Per Employee (revenue from yfinance, headcount from DB)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    revenue = revenue_date = None
    stale = False

    def fetch_income():
        df = yf.Ticker(symbol).income_stmt
        if df is None or df.empty:
            return []
        return df_to_records(df, INCOME_ROW_MAP)

    try:
        series, stale = yf_fetch(f"yf_income_{symbol}", SEVEN_DAYS, fetch_income)
        if series:
            latest = series[-1]
            revenue = latest.get("revenue")
            revenue_date = latest.get("date")
    except RuntimeError:
        pass

    db_snap = (
        SocialMediaSnapshot.objects
        .filter(competitor_id=competitor_id)
        .order_by('-recorded_at')
        .first()
    )
    db_emp = db_snap.employee_count if db_snap else None

    def safe_div(a, b):
        return round(a / b) if a and b else None

    return Response({
        "available": True,
        "revenue": revenue,
        "revenue_date": revenue_date,
        "employee_count": db_emp,
        "revenue_per_employee": safe_div(revenue, db_emp),
        "currency": "USD",
        "stale": stale,
    })
