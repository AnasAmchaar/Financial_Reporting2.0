"""Bank Al-Maghrib policy rate — CSV hand-maintained + optional forward-fill to monthly."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config.econ_settings import BAM_POLICY_RATES_CSV
from econ.sources.base import normalize_indicator_df

logger = logging.getLogger(__name__)


def load_policy_rates_csv(path: Path | None = None) -> pd.DataFrame:
    """Load dated policy-rate rows (value = percent per year, e.g. 2.5 for 2.5%)."""
    p = path or BAM_POLICY_RATES_CSV
    if not p.exists():
        logger.warning("BAM policy rates CSV missing: %s", p)
        return normalize_indicator_df(pd.DataFrame())

    raw = pd.read_csv(p)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    if "date" not in raw.columns or "value" not in raw.columns:
        logger.warning("BAM CSV must have date,value columns")
        return normalize_indicator_df(pd.DataFrame())

    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw = raw.dropna(subset=["date", "value"])
    raw = raw.sort_values("date")

    # Expand to month-start series: rate effective until next change
    if raw.empty:
        return normalize_indicator_df(pd.DataFrame())

    start = raw["date"].min().normalize()
    end = pd.Timestamp.today().normalize() + pd.offsets.MonthEnd(0)
    months = pd.date_range(start=start.to_period("M").to_timestamp(), end=end, freq="MS")
    values = []
    j = 0
    current = float(raw.iloc[0]["value"])
    for m in months:
        while j + 1 < len(raw) and pd.Timestamp(raw.iloc[j + 1]["date"]) <= m:
            j += 1
            current = float(raw.iloc[j]["value"])
        values.append(current / 100.0)  # decimal annual rate for PV formulas

    out = pd.DataFrame(
        {
            "date": months,
            "value": values,
            "frequency": "M",
            "unit": "annual_rate_decimal",
            "source": "bam",
            "indicator_code": "policy_rate",
            "country": "MAR",
        }
    )
    return normalize_indicator_df(out)
