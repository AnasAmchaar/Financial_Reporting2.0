"""Build CPI/PPI deflator series and apply to nominal amounts."""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)


def _to_monthly_index(series: pd.Series) -> pd.Series:
    """
    Reindex to month-start, interpolate numeric gaps.
    `series` is indexed by Timestamp with index levels as dates.
    """
    s = series.copy()
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    if s.empty:
        return s
    full = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    s = s.reindex(full)
    s = s.interpolate(method="linear", limit_direction="both")
    s = s.ffill().bfill()
    return s


def build_deflator_series(
    indicator_df: pd.DataFrame,
    base_period: str,
    *,
    date_col: str = "date",
    value_col: str = "value",
) -> pd.Series:
    """
    Return a Series indexed by month-start `date` with deflator D(t) = index_base / index_t.
    Nominal * D = real in base-period prices.
    """
    if indicator_df.empty:
        return pd.Series(dtype="float64")

    sub = indicator_df[[date_col, value_col]].dropna().copy()
    sub[date_col] = pd.to_datetime(sub[date_col]).dt.to_period("M").dt.to_timestamp()
    sub[value_col] = pd.to_numeric(sub[value_col], errors="coerce")
    sub = sub.dropna()
    sub = sub.groupby(date_col, as_index=True)[value_col].mean()
    sub = _to_monthly_index(sub)

    base_ts = pd.Timestamp(base_period + "-01") if len(base_period) == 7 else pd.to_datetime(base_period)
    base_ts = base_ts.to_period("M").to_timestamp()
    if base_ts not in sub.index:
        # nearest prior month
        prior = sub.index[sub.index <= base_ts]
        if len(prior):
            base_ts = prior.max()
        else:
            base_ts = sub.index.min()

    idx_base = float(sub.loc[base_ts])
    if idx_base == 0 or pd.isna(idx_base):
        raise ValueError(f"Invalid index value at base period {base_ts!r}")

    deflator = idx_base / sub
    deflator.name = "deflator"
    return deflator


def _sanitize_suffix(base_period: str) -> str:
    return re.sub(r"[^\w]+", "_", base_period.strip()).strip("_")


def apply_deflator(
    df: pd.DataFrame,
    value_col: str,
    date_col: str,
    deflator: pd.Series,
    *,
    base_period: str,
    deflator_col_name: str = "deflator",
) -> pd.DataFrame:
    """Add `<value_col>_real_<suffix>`, `<deflator_col_name>`, based on month alignment."""
    out = df.copy()
    dts = pd.to_datetime(out[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp()
    out["_econ_period"] = dts
    f = deflator.reindex(out["_econ_period"].values).to_numpy()
    out[deflator_col_name] = f
    suffix = _sanitize_suffix(base_period)
    real_col = f"{value_col}_real_{suffix}"
    out[real_col] = pd.to_numeric(out[value_col], errors="coerce") * out[deflator_col_name]
    out.drop(columns=["_econ_period"], inplace=True)
    return out
