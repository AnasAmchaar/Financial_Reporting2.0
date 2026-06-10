"""Build `*_real` SQLite tables from raw ETL tables + `econ_indicators`."""

from __future__ import annotations

import logging
import re
import sqlite3

import numpy as np
import pandas as pd

from config.econ_settings import ADJUSTMENTS, BASE_PERIOD, DISCOUNT, ECON_DB_PATH
from econ.adjusters.inflation import apply_deflator, build_deflator_series
from econ.adjusters.time_value import apply_present_value

logger = logging.getLogger(__name__)

_WIDE_DATE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})")


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(str(ECON_DB_PATH))


def _list_tables(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {r[0] for r in cur.fetchall()}


def _wide_to_long(df: pd.DataFrame, value_name: str) -> pd.DataFrame | None:
    """Detect YYYY_MM_DD... column names (SQLite-mangled datetimes) and melt."""
    id_cols: list[str] = []
    pairs: list[tuple[str, pd.Timestamp]] = []
    for c in df.columns:
        s = str(c)
        m = _WIDE_DATE.match(s)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                pairs.append((c, pd.Timestamp(year=y, month=mo, day=d)))
            except ValueError:
                continue
        else:
            id_cols.append(c)
    if len(pairs) < 2:
        return None
    long = df.melt(
        id_vars=id_cols,
        value_vars=[p[0] for p in pairs],
        var_name="_col",
        value_name=value_name,
    )
    cmap = {k: v for k, v in pairs}
    long["date"] = long["_col"].map(cmap)
    long.drop(columns=["_col"], inplace=True)
    long[value_name] = pd.to_numeric(long[value_name], errors="coerce")
    long["date"] = pd.to_datetime(long["date"], errors="coerce")
    return long


def _date_from_year_month(df: pd.DataFrame, ycol: str, mcol: str) -> pd.Series:
    y = pd.to_numeric(df[ycol], errors="coerce")
    m = pd.to_numeric(df[mcol], errors="coerce")
    ok = y.notna() & m.notna()
    out = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    if ok.any():
        out.loc[ok] = pd.to_datetime(
            dict(year=y[ok].astype(int), month=m[ok].astype(int), day=1),
            errors="coerce",
        )
    return out


def _deflator_at(defl: pd.Series, ts: pd.Timestamp) -> float:
    if defl.empty:
        return float("nan")
    ts = ts.to_period("M").to_timestamp()
    if ts in defl.index:
        return float(defl.loc[ts])
    sub = defl[defl.index <= ts]
    if len(sub):
        return float(sub.iloc[-1])
    return float(defl.iloc[0])


def apply_all() -> None:
    """Materialise all `*_real` tables defined in ADJUSTMENTS."""
    conn = _conn()
    try:
        tables = _list_tables(conn)
        if "econ_indicators" not in tables:
            logger.error("Missing econ_indicators table. Run `python run_econ.py fetch` first.")
            return

        ind_all = pd.read_sql("SELECT * FROM econ_indicators", conn)
        if ind_all.empty:
            logger.error("econ_indicators is empty. Run fetch first.")
            return

        cpi_df = ind_all[ind_all["indicator_code"] == "cpi"].copy()
        ppi_df = ind_all[ind_all["indicator_code"] == "ppi"].copy()
        if cpi_df.empty:
            logger.warning("No CPI rows in econ_indicators; CPI-based real columns will be NaN.")
        if ppi_df.empty:
            logger.warning("No PPI rows in econ_indicators; PPI-based real columns will be NaN.")

        cpi_def = build_deflator_series(cpi_df, BASE_PERIOD) if not cpi_df.empty else pd.Series(dtype=float)
        ppi_def = build_deflator_series(ppi_df, BASE_PERIOD) if not ppi_df.empty else pd.Series(dtype=float)
        if ppi_def.empty and not cpi_def.empty:
            logger.warning("PPI deflator unavailable; using CPI deflator for PPI-mapped tables.")
            ppi_def = cpi_def

        ref = DISCOUNT.get("ref_date", f"{BASE_PERIOD}-01")
        mode = DISCOUNT.get("mode", "constant")
        rate = float(DISCOUNT.get("rate", 0.0))
        ref_ts = pd.to_datetime(ref)
        sfx = str(ref_ts.date()).replace("-", "_")

        for table, spec in ADJUSTMENTS.items():
            if table not in tables:
                logger.warning("Table %s not in DB; skip", table)
                continue

            raw = pd.read_sql(f'SELECT * FROM "{table}"', conn)
            if raw.empty:
                logger.info("Table %s empty; skip", table)
                continue

            df = raw.copy()

            # --- Aging / snapshot: deflate numeric buckets from as_of_date ---
            if spec.get("as_of_date"):
                as_of = pd.to_datetime(spec["as_of_date"])
                dcode = spec.get("deflator", "cpi")
                defl = cpi_def if dcode == "cpi" else ppi_def
                fac = _deflator_at(defl, as_of)
                df["as_of_date"] = as_of
                suffix = BASE_PERIOD.replace("-", "_")
                num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                years_tv = (ref_ts - as_of).days / 365.25
                tv_mult = float(np.power(1.0 + rate, years_tv)) if mode == "constant" else 1.0

                for c in num_cols:
                    base_amt = pd.to_numeric(df[c], errors="coerce")
                    df[f"{c}_real_{suffix}"] = base_amt * fac
                    df[f"{c}_pv_{sfx}"] = base_amt * tv_mult

                df[f"{dcode}_deflator_asof"] = fac
                df[f"tv_factor_{sfx}"] = tv_mult

                out_name = f"{table}_real"
                df.to_sql(out_name, conn, if_exists="replace", index=False)
                logger.info("Wrote %d rows -> %s", len(df), out_name)
                continue

            value_col = spec.get("value_col")
            if not value_col:
                logger.warning("No value_col for %s", table)
                continue

            # --- Wide melt (balance sheet, HR) ---
            if spec.get("wide_amount"):
                if "date" in df.columns and value_col in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                else:
                    long_df = _wide_to_long(df, value_name=value_col)
                    if long_df is None:
                        logger.warning("Could not melt wide dates for %s", table)
                        continue
                    df = long_df

            if spec.get("date_from"):
                yc, mc = spec["date_from"]
                if yc in df.columns and mc in df.columns:
                    df["date"] = _date_from_year_month(df, yc, mc)
                elif mc in df.columns and spec.get("year_default") is not None:
                    yd = int(spec["year_default"])
                    tmp_y = pd.Series(yd, index=df.index, dtype="float64")
                    df["date"] = _date_from_year_month(
                        df.assign(_budget_year=tmp_y), "_budget_year", mc
                    )
                elif "date" not in df.columns:
                    logger.warning("Missing %s/%s for %s", yc, mc, table)
                    continue
            elif spec.get("date_col") and spec["date_col"] in df.columns:
                df["date"] = pd.to_datetime(df[spec["date_col"]], errors="coerce")

            if value_col not in df.columns:
                logger.warning("Missing value column %r for %s", value_col, table)
                continue

            dcode = spec.get("deflator", "cpi")
            defl = cpi_def if dcode == "cpi" else ppi_def
            dname = f"{dcode}_deflator"
            
            if spec.get("granular_demo") and value_col in df.columns:
                # Demo: Revenue (positive) uses CPI, Costs (negative) use PPI
                rev_mask = pd.to_numeric(df[value_col], errors="coerce") > 0
                
                df_rev = apply_deflator(df[rev_mask].copy(), value_col, "date", cpi_def, base_period=BASE_PERIOD, deflator_col_name="cpi_deflator")
                df_cost = apply_deflator(df[~rev_mask].copy(), value_col, "date", ppi_def, base_period=BASE_PERIOD, deflator_col_name="ppi_deflator")
                
                suffix = BASE_PERIOD.replace("-", "_")
                real_col = f"{value_col}_real_{suffix}"
                
                # Tag which deflator was used for each row
                df_rev["deflator_type"] = "cpi"
                df_cost["deflator_type"] = "ppi"
                
                # Fill missing cross-deflator columns with 1.0 (neutral)
                # so downstream queries always find non-null values
                if "ppi_deflator" not in df_rev.columns:
                    df_rev["ppi_deflator"] = 1.0
                if "cpi_deflator" not in df_cost.columns:
                    df_cost["cpi_deflator"] = 1.0
                
                df = pd.concat([df_rev, df_cost], ignore_index=True)
            else:
                df = apply_deflator(df, value_col, "date", defl, base_period=BASE_PERIOD, deflator_col_name=dname)
            df = apply_present_value(df, value_col, "date", ref_date=ref, mode=mode, annual_rate=rate)

            out_name = f"{table}_real"
            df.to_sql(out_name, conn, if_exists="replace", index=False)
            logger.info("Wrote %d rows -> %s", len(df), out_name)

    finally:
        conn.close()
