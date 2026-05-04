"""
Resolve Morocco CPI on FRED without hardcoding obsolete series IDs.

FRED often has no *monthly* Morocco CPI (OECD IDs may be removed); this module
validates candidates via fred/series, searches with scoring, and returns empty
so INDICATOR_CHAIN can fall through to World Bank.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from econ.sources import fred
from econ.sources.base import normalize_indicator_df

logger = logging.getLogger(__name__)

# Known-good IDs can be added when FRED exposes monthly Morocco CPI again;
# each entry is validated with fred/series (must exist and be Monthly).
MAR_CPI_MONTHLY_ALLOWLIST: tuple[str, ...] = ()

_SEARCH_QUERIES: tuple[str, ...] = (
    "Morocco consumer price index",
    "Morocco CPI all items",
    "Morocco CPI monthly",
    "MAR CPI OECD",
    "MARCPI",
)


def _title(s: dict[str, Any]) -> str:
    return (s.get("title") or "").lower()


def _morocco_cpi_monthly_score(s: dict[str, Any]) -> float:
    """Higher is better; 0 means not a candidate."""
    title = _title(s)
    sid = (s.get("id") or "").upper()
    if "morocco" not in title and "MAR" not in sid:
        return 0.0
    if s.get("frequency") != "Monthly":
        return 0.0
    score = 1.0
    if "consumer price" in title or "cpi" in title:
        score += 4.0
    if "all items" in title or "total" in title or "headline" in title:
        score += 2.0
    if "core" in title:
        score -= 1.0
    units = (s.get("units") or "").lower()
    if "index" in units:
        score += 1.0
    return score


def resolve_morocco_cpi_monthly_series_id(api_key: str | None = None) -> str | None:
    """Return a validated Monthly Morocco CPI series id, or None."""
    key = (api_key or "").strip() or None

    for sid in MAR_CPI_MONTHLY_ALLOWLIST:
        meta = fred.fred_series_meta(sid, api_key=key)
        if meta and meta.get("frequency") == "Monthly":
            logger.info("Morocco CPI (FRED): using allowlisted series_id=%s", sid)
            return sid

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for q in _SEARCH_QUERIES:
        for s in fred.fred_series_search(q, limit=30, api_key=key):
            sid = s.get("id")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            meta = fred.fred_series_meta(sid, api_key=key)
            if not meta or meta.get("frequency") != "Monthly":
                continue
            merged = {**s, **{k: v for k, v in meta.items() if v is not None}}
            candidates.append(merged)

    best_id: str | None = None
    best_score = 0.0
    for s in candidates:
        sc = _morocco_cpi_monthly_score(s)
        if sc > best_score:
            best_score = sc
            best_id = s.get("id")

    if best_id:
        logger.info(
            "Morocco CPI (FRED): resolved_series_id=%s (search score=%.1f)",
            best_id,
            best_score,
        )
    else:
        logger.info(
            "Morocco CPI (FRED): no monthly series resolved (allowlist/search); "
            "falling through to next source in chain",
        )
    return best_id


def fetch_morocco_cpi_monthly(*, logical_code: str = "cpi") -> pd.DataFrame:
    sid = resolve_morocco_cpi_monthly_series_id()
    if not sid:
        return normalize_indicator_df(pd.DataFrame())
    df = fred.fetch_series(sid, logical_code=logical_code, row_frequency="M")
    if not df.empty:
        logger.info(
            "Morocco CPI (FRED): fetched %d observations for resolved_series_id=%s",
            len(df),
            sid,
        )
    return df


def fetch_morocco_cpi_yoy(*, logical_code: str = "cpi_yoy") -> pd.DataFrame:
    """
    Prefer YoY computed from resolved monthly CPI index (single source of truth).
    Returns empty if no monthly FRED CPI is available.
    """
    sid = resolve_morocco_cpi_monthly_series_id()
    if not sid:
        return normalize_indicator_df(pd.DataFrame())

    df = fred.fetch_series(sid, logical_code="cpi", row_frequency="M")
    if df.empty or len(df) < 13:
        return normalize_indicator_df(pd.DataFrame())

    work = df.sort_values("date").reset_index(drop=True)
    v = work["value"].astype(float)
    yoy = (v / v.shift(12) - 1.0) * 100.0
    work["value"] = yoy
    work = work.iloc[12:].copy()
    work["indicator_code"] = logical_code
    work["unit"] = "pct_yoy"
    work["frequency"] = "M"
    logger.info(
        "Morocco CPI YoY (FRED): derived from monthly index resolved_series_id=%s (%d rows)",
        sid,
        len(work),
    )
    return normalize_indicator_df(work)
