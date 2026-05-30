import logging

import pandas as pd
import yfinance as yf
from django.core.cache import cache

logger = logging.getLogger(__name__)

STALE_TTL = 60 * 60 * 24 * 30  # 30 days


def yf_fetch(cache_key: str, ttl: int, fetch_fn):
    """
    Generic cached yfinance fetcher.
    Returns (data, is_stale).
    Raises RuntimeError if both live fetch and stale cache fail.
    """
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, False

    try:
        data = fetch_fn()
        cache.set(cache_key, data, ttl)
        cache.set(f"stale_{cache_key}", data, STALE_TTL)
        return data, False
    except Exception as exc:
        logger.warning("yfinance fetch failed [%s]: %s", cache_key, exc)
        stale = cache.get(f"stale_{cache_key}")
        if stale is not None:
            return stale, True
        raise RuntimeError(f"yfinance unavailable and no cached data: {exc}") from exc


def df_to_records(df: pd.DataFrame, row_map: dict) -> list:
    """
    Convert a yfinance financials DataFrame to a list of yearly dicts.
    df columns are Timestamps (newest first), rows are line item labels.
    row_map: {output_key: [candidate_row_labels_in_priority_order]}
    """
    records = []
    for col in df.columns:
        record = {"date": col.strftime("%Y-%m-%d")}
        for out_key, labels in row_map.items():
            val = None
            for label in labels:
                if label in df.index:
                    raw = df.loc[label, col]
                    val = float(raw) if pd.notna(raw) else None
                    break
            record[out_key] = val
        records.append(record)
    return sorted(records, key=lambda x: x["date"])
