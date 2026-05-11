"""
Section 1 — Competitor Financial Profile  (FMP stable API)
Section 2 — Revenue & Financial Health     (FMP stable API)

All endpoints use https://financialmodelingprep.com/stable/
Field names reflect the stable API response (differ from legacy v3).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.monitoring.models import Competitor
from apps.social_media.models import SocialMediaSnapshot
from apps.dashboard.services.fmp import fmp_get

SEVEN_DAYS = 60 * 60 * 24 * 7


def _get_competitor(competitor_id, user):
    try:
        return Competitor.objects.get(pk=competitor_id, user=user, is_deleted=False)
    except Competitor.DoesNotExist:
        return None


def _no_symbol():
    return Response({"available": False, "reason": "No stock symbol configured"})


def _fmp_error(exc):
    return Response(
        {"error": "FMP API unavailable", "code": "UPSTREAM_ERROR"},
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

    cache_key = f"fmp_profile_{symbol}"
    try:
        raw, stale = fmp_get("profile", cache_key, SEVEN_DAYS, params={"symbol": symbol})
    except RuntimeError as e:
        return _fmp_error(e)

    if not raw:
        return _no_symbol()

    p = raw[0] if isinstance(raw, list) else raw
    return Response({
        "available": True,
        "competitor_id": comp.pk,
        "competitor_name": comp.name,
        "stock_symbol": symbol,
        "logo_url": p.get("image"),
        "ceo": p.get("ceo"),
        "headquarters": p.get("address") or f"{p.get('city','')}, {p.get('state','')}".strip(", ") or None,
        "sector": p.get("sector") or p.get("industry"),
        "industry": p.get("industry"),
        "website": p.get("website"),
        "description": p.get("description"),
        "ipo_date": p.get("ipoDate"),
        "exchange": p.get("exchange"),
        "exchange_full": p.get("exchangeFullName"),
        "currency": p.get("currency"),
        "market_cap": p.get("marketCap"),
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_cap(request, competitor_id):
    """1.2 — Market Cap Over Time"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    years = min(int(request.query_params.get('years', 5)), 10)
    limit = years * 365
    cache_key = f"fmp_market_cap_{symbol}_{years}"

    try:
        raw, stale = fmp_get(
            "historical-market-capitalization",
            cache_key, SEVEN_DAYS,
            params={"symbol": symbol, "limit": limit},
        )
    except RuntimeError as e:
        return _fmp_error(e)

    # Downsample to monthly (last entry per year-month)
    monthly = {}
    for entry in (raw or []):
        d = entry.get("date", "")
        ym = d[:7]
        monthly[ym] = {"date": d, "market_cap": entry.get("marketCap")}
    series = sorted(monthly.values(), key=lambda x: x["date"])

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
    """1.3 — Employee Count Comparison (DB + FMP overlay)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    fmp_series = []
    stale = False

    if symbol:
        cache_key = f"fmp_emp_count_{symbol}"
        try:
            raw, stale = fmp_get(
                "historical-employee-count",
                cache_key, SEVEN_DAYS,
                params={"symbol": symbol},
            )
            fmp_series = [
                {
                    "date": e.get("periodOfReport") or e.get("filingDate"),
                    "employee_count": e.get("employeeCount"),
                }
                for e in (raw or [])
            ]
        except RuntimeError:
            pass

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

    return Response({
        "available": True,
        "fmp_series": fmp_series,
        "db_series": db_series,
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def executives(request, competitor_id):
    """1.4 — Executive Team Panel"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    cache_key = f"fmp_executives_{symbol}"
    try:
        raw, stale = fmp_get(
            "key-executives", cache_key, SEVEN_DAYS,
            params={"symbol": symbol},
        )
    except RuntimeError as e:
        return _fmp_error(e)

    execs = [
        {
            "name": e.get("name"),
            "title": e.get("title"),
            "total_pay": e.get("pay"),
            "currency": e.get("currencyPay"),
            "year_born": e.get("yearBorn"),
            "active": e.get("active"),
        }
        for e in (raw or [])
    ]
    return Response({"available": True, "executives": execs, "stale": stale})


# ─── Section 2 ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def income_statement(request, competitor_id):
    """2.1 — Revenue vs Net Income"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    years = int(request.query_params.get('years', 5))
    cache_key = f"fmp_income_{symbol}_{years}"
    try:
        raw, stale = fmp_get(
            "income-statement",
            cache_key, SEVEN_DAYS,
            params={"symbol": symbol, "period": "annual", "limit": years},
        )
    except RuntimeError as e:
        return _fmp_error(e)

    series = sorted(
        [
            {
                "date": e.get("date"),
                "revenue": e.get("revenue"),
                "net_income": e.get("netIncome"),
                "gross_profit": e.get("grossProfit"),
                "operating_income": e.get("operatingIncome"),
            }
            for e in (raw or [])
        ],
        key=lambda x: x["date"] or "",
    )
    return Response({"available": True, "period": "annual", "series": series, "stale": stale})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_growth(request, competitor_id):
    """2.2 — Revenue Growth Rate  (uses /stable/financial-growth)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    cache_key = f"fmp_growth_{symbol}"
    try:
        raw, stale = fmp_get(
            "financial-growth",
            cache_key, SEVEN_DAYS,
            params={"symbol": symbol, "period": "annual", "limit": 5},
        )
    except RuntimeError as e:
        return _fmp_error(e)

    def pct(v):
        return round(v * 100, 2) if v is not None else None

    series = [
        {
            "date": e.get("date"),
            "revenue_growth_pct": pct(e.get("revenueGrowth")),
            "net_income_growth_pct": pct(e.get("netIncomeGrowth")),
            "eps_growth_pct": pct(e.get("epsgrowth")),
            "free_cash_flow_growth_pct": pct(e.get("freeCashFlowGrowth")),
        }
        for e in (raw or [])
    ]
    return Response({"available": True, "series": series, "stale": stale})


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

    cache_key = f"fmp_ratios_{symbol}"
    try:
        raw, stale = fmp_get(
            "ratios",
            cache_key, SEVEN_DAYS,
            params={"symbol": symbol, "period": "annual", "limit": 1},
        )
    except RuntimeError as e:
        return _fmp_error(e)

    r = (raw or [{}])[0]
    return Response({
        "available": True,
        "period": r.get("date"),
        "ratios": {
            "gross_profit_margin": r.get("grossProfitMargin"),
            "net_profit_margin": r.get("netProfitMargin"),
            "return_on_equity": r.get("returnOnEquity"),
            "return_on_assets": r.get("returnOnAssets"),
            "price_earnings_ratio": r.get("priceToEarningsRatio") or r.get("peRatio"),
            "price_to_book_ratio": r.get("priceToBookRatio"),
            "price_to_sales_ratio": r.get("priceToSalesRatio"),
            "debt_to_equity_ratio": r.get("debtToEquityRatio") or r.get("debtEquityRatio"),
            "current_ratio": r.get("currentRatio"),
        },
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_rating(request, competitor_id):
    """2.4 — Financial Health Score (derived from ratios — rating endpoint not available on this plan)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    # Derive a simple score from ratios since /rating is not on this FMP plan
    cache_key = f"fmp_ratios_{symbol}"
    try:
        raw, stale = fmp_get(
            "ratios",
            cache_key, SEVEN_DAYS,
            params={"symbol": symbol, "period": "annual", "limit": 1},
        )
    except RuntimeError as e:
        return _fmp_error(e)

    r = (raw or [{}])[0]

    def score(value, thresholds):
        """Score 1-5 based on ascending thresholds."""
        if value is None:
            return None
        for i, t in enumerate(thresholds, 1):
            if value <= t:
                return i
        return 5

    roe = r.get("returnOnEquity")
    roa = r.get("returnOnAssets")
    debt_eq = r.get("debtToEquityRatio") or r.get("debtEquityRatio")
    pe = r.get("priceToEarningsRatio") or r.get("peRatio")
    npm = r.get("netProfitMargin")

    roe_s = score(roe, [0.05, 0.10, 0.15, 0.20]) if roe else None
    roa_s = score(roa, [0.02, 0.05, 0.08, 0.12]) if roa else None
    de_s = score(debt_eq, [0.3, 0.6, 1.0, 1.5]) if debt_eq else None
    # For PE and NPM lower is better reversed
    pe_s = (5 - score(pe, [15, 25, 40, 60]) + 1) if pe else None
    npm_s = score(npm, [0.02, 0.05, 0.10, 0.15]) if npm else None

    scores = [s for s in [roe_s, roa_s, de_s, pe_s, npm_s] if s]
    avg = round(sum(scores) / len(scores), 1) if scores else None

    rating_map = {5: "A", 4: "B+", 3: "B", 2: "C+", 1: "C"}
    rec_map = {5: "Strong Buy", 4: "Buy", 3: "Hold", 2: "Underperform", 1: "Sell"}
    avg_int = round(avg) if avg else None

    return Response({
        "available": True,
        "rating": rating_map.get(avg_int, "N/A"),
        "rating_score": avg,
        "recommendation": rec_map.get(avg_int, "N/A"),
        "sub_scores": {
            "roe_score": roe_s,
            "roa_score": roa_s,
            "debt_to_equity_score": de_s,
            "pe_score": pe_s,
            "net_margin_score": npm_s,
        },
        "note": "Derived score — /rating endpoint requires a higher FMP plan",
        "stale": stale,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_per_employee(request, competitor_id):
    """2.5 — Revenue Per Employee (Derived)"""
    comp = _get_competitor(competitor_id, request.user)
    if not comp:
        return Response({"error": "Competitor not found", "code": "NOT_FOUND"}, status=404)

    symbol = getattr(comp, 'stock_symbol', None)
    if not symbol:
        return _no_symbol()

    stale = False
    revenue = revenue_date = fmp_emp = None

    try:
        inc_raw, s1 = fmp_get(
            "income-statement",
            f"fmp_income_{symbol}_1",
            SEVEN_DAYS,
            params={"symbol": symbol, "period": "annual", "limit": 1},
        )
        if inc_raw:
            revenue = inc_raw[0].get("revenue")
            revenue_date = inc_raw[0].get("date")
        stale = stale or s1
    except RuntimeError:
        pass

    try:
        emp_raw, s2 = fmp_get(
            "historical-employee-count",
            f"fmp_emp_count_{symbol}",
            SEVEN_DAYS,
            params={"symbol": symbol},
        )
        if emp_raw:
            fmp_emp = emp_raw[0].get("employeeCount")
        stale = stale or s2
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
        "fmp_employee_count": fmp_emp,
        "db_employee_count": db_emp,
        "revenue_per_employee_fmp": safe_div(revenue, fmp_emp),
        "revenue_per_employee_db": safe_div(revenue, db_emp),
        "currency": "USD",
        "stale": stale,
    })
