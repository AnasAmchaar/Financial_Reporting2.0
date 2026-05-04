"""Discount factors and present value columns."""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def discount_factor_series(
    dates: pd.Series,
    ref_date: pd.Timestamp,
    *,
    mode: str = "constant",
    annual_rate: float | None = None,
    rate_series: pd.Series | None = None,
) -> pd.Series:
    """
    Per-row discount factor to express `value * factor` ≈ PV at ref_date.

    constant: factor = 1 / (1+r)^((ref - t)/365.25)
    series: uses time-varying annual rate from `rate_series` indexed by month-start
            (linearly converted to effective per-row discount vs ref).
    """
    t = pd.to_datetime(dates, errors="coerce")
    ref = pd.to_datetime(ref_date).normalize()

    if mode == "constant":
        r = float(annual_rate or 0.0)
        # Revalue cashflow dated `t` to `ref`: amount * (1+r)^((ref - t) in years)
        years = (ref - t).dt.days.astype("float64") / 365.25
        return pd.Series(np.power(1.0 + r, years), index=t.index)

    if mode == "series" and rate_series is not None and not rate_series.empty:
        # Approximate: compound using piecewise constant monthly rates between t and ref
        rs = rate_series.copy()
        rs.index = pd.to_datetime(rs.index).to_period("M").to_timestamp()
        rs = rs.sort_index()
        factors = []
        for ts in t:
            if pd.isna(ts):
                factors.append(np.nan)
                continue
            m0 = ts.to_period("M").to_timestamp()
            m1 = ref.to_period("M").to_timestamp()
            if m0 >= m1:
                factors.append(1.0)
                continue
            months = pd.date_range(m0, m1, freq="MS", inclusive="left")
            acc = 1.0
            for m in months:
                rr = float(rs.get(m, np.nan))
                if np.isnan(rr):
                    rr = float(rs.ffill().bfill().reindex([m]).iloc[0])
                # monthly from annual: (1+r)^(1/12)
                acc *= np.power(1.0 + rr, 1.0 / 12.0)
            factors.append(acc)
        return pd.Series(factors, index=t.index)

    logger.warning("discount_factor_series: falling back to 1.0 (mode=%s)", mode)
    return pd.Series(1.0, index=t.index)


def _ref_suffix(ref_date: str | pd.Timestamp) -> str:
    ts = pd.to_datetime(ref_date)
    s = ts.strftime("%Y-%m-%d")
    return re.sub(r"[^\w]+", "_", s)


def apply_present_value(
    df: pd.DataFrame,
    value_col: str,
    date_col: str,
    *,
    ref_date: str | pd.Timestamp,
    mode: str,
    annual_rate: float | None,
    rate_series: pd.Series | None = None,
) -> pd.DataFrame:
    out = df.copy()
    fac = discount_factor_series(
        out[date_col],
        pd.to_datetime(ref_date),
        mode=mode,
        annual_rate=annual_rate,
        rate_series=rate_series,
    )
    sfx = _ref_suffix(ref_date)
    col = f"{value_col}_pv_{sfx}"
    out[col] = pd.to_numeric(out[value_col], errors="coerce") * fac
    out[f"tv_factor_{sfx}"] = fac
    return out
