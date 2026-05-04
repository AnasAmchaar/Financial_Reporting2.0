"""FRED (St. Louis Fed) observations API."""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd
import requests

from econ.sources.base import normalize_indicator_df

logger = logging.getLogger(__name__)

FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series"
FRED_SEARCH_URL = "https://api.stlouisfed.org/fred/series/search"


def _fred_api_key(api_key: str | None) -> str:
    return (api_key or os.environ.get("FRED_API_KEY", "")).strip()


def fred_series_meta(series_id: str, api_key: str | None = None) -> dict[str, Any] | None:
    """
    GET fred/series — returns one series dict or None if missing / error.
    """
    key = _fred_api_key(api_key)
    if not key:
        logger.warning("FRED_API_KEY not set; skipping series meta for %s", series_id)
        return None
    try:
        r = requests.get(
            FRED_SERIES_URL,
            params={"series_id": series_id, "api_key": key, "file_type": "json"},
            timeout=30,
        )
        payload = r.json()
    except Exception as e:
        logger.warning("FRED series meta request failed %s: %s", series_id, e)
        return None
    if not r.ok:
        err = (payload or {}).get("error_message") or (payload or {}).get("message") or r.text[:300]
        logger.warning(
            "FRED series meta failed series_id=%s status=%s: %s",
            series_id,
            r.status_code,
            err,
        )
        return None
    series_list = payload.get("seriess") or []
    if not series_list:
        return None
    return series_list[0]


def fred_series_search(
    search_text: str,
    *,
    limit: int = 10,
    api_key: str | None = None,
    order_by: str = "popularity",
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    """GET fred/series/search — returns list of series dicts (may be empty)."""
    key = _fred_api_key(api_key)
    if not key:
        logger.warning("FRED_API_KEY not set; skipping series search %r", search_text[:80])
        return []
    try:
        r = requests.get(
            FRED_SEARCH_URL,
            params={
                "search_text": search_text,
                "api_key": key,
                "file_type": "json",
                "limit": limit,
                "order_by": order_by,
                "sort_order": sort_order,
            },
            timeout=45,
        )
        payload = r.json()
    except Exception as e:
        logger.warning("FRED series search failed %r: %s", search_text[:80], e)
        return []
    if not r.ok:
        err = (payload or {}).get("error_message") or (payload or {}).get("message") or r.text[:300]
        logger.warning(
            "FRED series search failed query=%r status=%s: %s",
            search_text[:80],
            r.status_code,
            err,
        )
        return []
    return list(payload.get("seriess") or [])


def _fred_freq_to_code(fred_freq: str | None) -> str:
    if not fred_freq:
        return "M"
    m = {
        "Daily": "D",
        "Weekly": "W",
        "Biweekly": "W",
        "Monthly": "M",
        "Quarterly": "Q",
        "Semiannual": "S",
        "Annual": "A",
    }
    return m.get(str(fred_freq), "M")


def fetch_series(
    series_id: str,
    *,
    logical_code: str,
    country: str = "MAR",
    api_key: str | None = None,
    row_frequency: str | None = None,
) -> pd.DataFrame:
    key = _fred_api_key(api_key)
    if not key:
        logger.warning("FRED_API_KEY not set; skipping series %s", series_id)
        return normalize_indicator_df(pd.DataFrame())

    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "observation_start": "1990-01-01",
    }
    try:
        r = requests.get(FRED_OBS_URL, params=params, timeout=60)
        payload: dict[str, Any]
        try:
            payload = r.json()
        except Exception:
            payload = {}
        if not r.ok:
            err = payload.get("error_message") or payload.get("message") or r.text[:400]
            logger.warning(
                "FRED observations failed series_id=%s status=%s: %s",
                series_id,
                r.status_code,
                err,
            )
            return normalize_indicator_df(pd.DataFrame())
    except Exception as e:
        logger.warning("FRED request failed %s: %s", series_id, e)
        return normalize_indicator_df(pd.DataFrame())

    freq_code = row_frequency
    if freq_code is None:
        meta = fred_series_meta(series_id, api_key=key)
        if meta:
            freq_code = _fred_freq_to_code(meta.get("frequency"))
        else:
            freq_code = "M"

    obs = payload.get("observations") or []
    rows = []
    for o in obs:
        val = o.get("value")
        if val in (".", "", None):
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "date": pd.to_datetime(o.get("date"), errors="coerce"),
                "value": v,
                "frequency": freq_code,
                "unit": _guess_unit(logical_code, series_id),
                "source": "fred",
                "indicator_code": logical_code,
                "country": country,
            }
        )

    df = pd.DataFrame.from_records(rows)
    return normalize_indicator_df(df)


def _guess_unit(logical_code: str, series_id: str) -> str:
    if "yoy" in logical_code.lower() or "CPALTT" in series_id:
        return "pct_yoy"
    if "CPI" in series_id or "cpi" in logical_code:
        return "index_fred"
    return "index_fred"
