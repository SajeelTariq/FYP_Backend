"""
Company symbol search — used by the "Add Competitor" modal.

Flow:
  1. User types company name → clicks Search
  2. Frontend hits GET /api/dashboard/search-symbol/?name=Apple
  3. Backend calls FMP /stable/search-name, deduplicates, prioritises
     major exchanges (NASDAQ/NYSE first), strips crypto/OTC noise
  4. Frontend shows the list → user picks one → symbol stored on competitor
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.dashboard.services.fmp import fmp_get

# Exchanges we surface first — in priority order
PRIMARY_EXCHANGES = ['NASDAQ', 'NYSE', 'LSE', 'TSX', 'ASX', 'EURONEXT', 'NSE', 'BSE']

# Exchanges we hide entirely — too noisy / irrelevant
EXCLUDED_EXCHANGES = ['CRYPTO', 'OTC', 'PNK', 'CCC']

# Short cache — search results don't need to last long
TEN_MINUTES = 60 * 10


def _sort_key(result):
    """Primary exchanges first, then alphabetical by exchange name."""
    exchange = result.get('exchange', '')
    try:
        return (PRIMARY_EXCHANGES.index(exchange), result.get('name', ''))
    except ValueError:
        return (len(PRIMARY_EXCHANGES), result.get('name', ''))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_symbol(request):
    """
    Search for a company by name and return matching stock symbols.

    Query params:
      name (required) — company name to search e.g. "Apple", "Microsoft"
      limit           — max results to return (default 10, max 20)

    Response:
    {
      "query": "Apple",
      "results": [
        {
          "symbol": "AAPL",
          "name": "Apple Inc.",
          "exchange": "NASDAQ",
          "exchange_full": "NASDAQ Global Select",
          "currency": "USD"
        },
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
    cache_key = f"fmp_search_{name.lower().replace(' ', '_')}"

    try:
        raw, _ = fmp_get(
            "search-name",
            cache_key,
            TEN_MINUTES,
            params={"query": name, "limit": 50},   # fetch more, we filter down
        )
    except RuntimeError:
        return Response(
            {"error": "FMP search unavailable. Try again shortly.", "code": "UPSTREAM_ERROR"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Filter out unwanted exchanges
    filtered = [
        r for r in (raw or [])
        if r.get('exchange') not in EXCLUDED_EXCHANGES
    ]

    # Deduplicate: if the same company appears on multiple exchanges,
    # keep the best-ranked one only
    seen_names = {}
    for r in filtered:
        n = r.get('name', '').lower()
        if n not in seen_names:
            seen_names[n] = r
        else:
            # Replace if current exchange is higher priority
            existing_key = _sort_key(seen_names[n])
            current_key = _sort_key(r)
            if current_key < existing_key:
                seen_names[n] = r

    deduplicated = sorted(seen_names.values(), key=_sort_key)

    results = [
        {
            "symbol":        r.get("symbol"),
            "name":          r.get("name"),
            "exchange":      r.get("exchange"),
            "exchange_full": r.get("exchangeFullName"),
            "currency":      r.get("currency"),
        }
        for r in deduplicated[:limit]
    ]

    return Response({"query": name, "results": results})
