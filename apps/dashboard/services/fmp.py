"""
FMP (Financial Modeling Prep) API client with stale-while-revalidate caching.

Cache strategy:
  - primary key   → TTL-based (7d / 6h / 24h depending on endpoint)
  - stale key     → 30-day fallback, updated on every successful fetch
On FMP error, returns last stale value with {"stale": True}.
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

FMP_BASE_URL = getattr(settings, 'FMP_BASE_URL', 'https://financialmodelingprep.com/api/v3')
STALE_TTL = 60 * 60 * 24 * 30  # 30 days


def fmp_get(path: str, cache_key: str, ttl: int, params: dict | None = None):
    """
    Fetch `path` from FMP with caching.

    Returns (data, is_stale).
    Raises RuntimeError if both live fetch and stale cache fail.
    """
    api_key = getattr(settings, 'FMP_API_KEY', '')

    cached = cache.get(cache_key)
    if cached is not None:
        return cached, False

    url = f"{FMP_BASE_URL}/{path.lstrip('/')}"
    req_params = dict(params or {})
    req_params['apikey'] = api_key

    try:
        resp = requests.get(url, params=req_params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        cache.set(cache_key, data, ttl)
        cache.set(f"stale_{cache_key}", data, STALE_TTL)
        return data, False
    except Exception as exc:
        logger.warning("FMP fetch failed for %s: %s", path, exc)
        stale = cache.get(f"stale_{cache_key}")
        if stale is not None:
            return stale, True
        raise RuntimeError(f"FMP unavailable and no cached data for {path}") from exc
