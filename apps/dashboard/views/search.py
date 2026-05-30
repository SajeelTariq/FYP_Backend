"""
Company symbol search — used by the "Add Competitor" modal.

Flow:
  1. User types company name → clicks Search
  2. Frontend hits GET /api/dashboard/search-symbol/?name=Apple
  3. Backend calls yf.Search, filters to equities only, deduplicates
  4. Frontend shows the list → user picks one → symbol stored on competitor
"""
import yfinance as yf
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

TEN_MINUTES = 60 * 10

# Yahoo Finance internal exchange codes → display names
EXCHANGE_MAP = {
    'NMS': 'NASDAQ', 'NGM': 'NASDAQ', 'NCM': 'NASDAQ',
    'NYQ': 'NYSE',   'NYE': 'NYSE',
    'PCX': 'NYSE Arca',
    'BTS': 'NYSE',
    'LSE': 'LSE',
    'TOR': 'TSX',
    'ASX': 'ASX',
}

PRIMARY_EXCHANGES = ['NASDAQ', 'NYSE', 'LSE', 'TSX', 'ASX']

EXCLUDED_QUOTE_TYPES = {'CRYPTOCURRENCY', 'CURRENCY', 'FUTURE', 'OPTION', 'INDEX', 'MUTUALFUND'}


def _exchange_display(q: dict) -> str:
    raw = q.get('exchange', '')
    return EXCHANGE_MAP.get(raw, q.get('exchDisp', raw))


def _sort_key(exchange: str, name: str):
    try:
        return (PRIMARY_EXCHANGES.index(exchange), name)
    except ValueError:
        return (len(PRIMARY_EXCHANGES), name)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_symbol(request):
    """
    Search for a company by name and return matching stock symbols.

    Query params:
      name  (required) — company name e.g. "Apple", "Microsoft"
      limit — max results (default 10, max 20)

    Response:
    {
      "query": "Apple",
      "results": [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "currency": "USD"},
        ...
      ]
    }
    """
    name = request.query_params.get('name', '').strip()
    if not name:
        return Response(
            {"error": "Query param 'name' is required.", "code": "MISSING_PARAM"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    limit = min(int(request.query_params.get('limit', 10)), 20)
    cache_key = f"yf_search_{name.lower().replace(' ', '_')}"

    cached = cache.get(cache_key)
    if cached is not None:
        return Response({"query": name, "results": cached})

    try:
        quotes = yf.Search(name, max_results=30).quotes
    except Exception:
        return Response(
            {"error": "Symbol search unavailable. Try again shortly.", "code": "UPSTREAM_ERROR"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    seen_names = {}
    for q in quotes:
        if q.get('quoteType') in EXCLUDED_QUOTE_TYPES:
            continue

        display_name = q.get('longname') or q.get('shortname') or ''
        symbol = q.get('symbol', '')
        if not display_name or not symbol:
            continue

        exchange = _exchange_display(q)
        key = display_name.lower()

        if key not in seen_names:
            seen_names[key] = {'symbol': symbol, 'name': display_name,
                               'exchange': exchange, 'currency': q.get('currency')}
        else:
            existing = seen_names[key]
            if _sort_key(exchange, display_name) < _sort_key(existing['exchange'], existing['name']):
                seen_names[key] = {'symbol': symbol, 'name': display_name,
                                   'exchange': exchange, 'currency': q.get('currency')}

    results = sorted(seen_names.values(), key=lambda r: _sort_key(r['exchange'], r['name']))[:limit]
    cache.set(cache_key, results, TEN_MINUTES)
    return Response({"query": name, "results": results})
