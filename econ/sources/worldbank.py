"""World Bank Indicators API (no API key)."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests

from econ.sources.base import normalize_indicator_df

logger = logging.getLogger(__name__)

WB_BASE = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"


def fetch_indicator(
    country_iso3: str,
    indicator: str,
    *,
    logical_code: str,
    source_label: str = "worldbank",
) -> pd.DataFrame:
    """
    Fetch annual observations. indicator e.g. FP.CPI.TOTL, FP.CPI.TOTL.ZG.
    """
    url = WB_BASE.format(country=country_iso3, indicator=indicator)
    params: dict[str, Any] = {"format": "json", "per_page": 1000}
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("World Bank request failed %s: %s", indicator, e)
        return normalize_indicator_df(pd.DataFrame())

    if not isinstance(data, list) or len(data) < 2:
        return normalize_indicator_df(pd.DataFrame())

    rows = data[1]
    if not rows:
        return normalize_indicator_df(pd.DataFrame())

    records = []
    for row in rows:
        d = row.get("date")
        v = row.get("value")
        if d is None or v is None:
            continue
        try:
            year = int(d)
        except (TypeError, ValueError):
            continue
        records.append(
            {
                "date": pd.Timestamp(year=year, month=1, day=1),
                "value": float(v),
                "frequency": "A",
                "unit": _unit_for_indicator(indicator),
                "source": source_label,
                "indicator_code": logical_code,
                "country": country_iso3,
            }
        )

    df = pd.DataFrame.from_records(records)
    return normalize_indicator_df(df)


def _unit_for_indicator(indicator: str) -> str:
    if indicator == "FP.CPI.TOTL":
        return "index_wb_2010_100"
    if indicator == "NY.GDP.DEFL.ZS":
        return "gdp_deflator_index"
    if indicator.endswith("ZG") or "ZG" in indicator:
        return "pct_yoy"
    if "DEFL" in indicator:
        return "index"
    if "INR" in indicator or "LEND" in indicator:
        return "pct"
    return "value"
