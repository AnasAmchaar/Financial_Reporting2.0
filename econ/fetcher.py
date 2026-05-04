"""Orchestrate macro fetches, write Parquet cache, load `econ_indicators` SQLite table."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config.econ_settings import (
    DEFAULT_COUNTRY_ISO3,
    ECON_CACHE_DIR,
    ECON_DB_PATH,
    INDICATOR_CHAIN,
)
from econ.sources import bam, fred, fred_morocco, hcp, worldbank
from econ.sources.base import normalize_indicator_df

logger = logging.getLogger(__name__)


def _ensure_cache_dir() -> None:
    ECON_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _write_cache(logical: str, df: pd.DataFrame) -> Path | None:
    if df.empty:
        return None
    _ensure_cache_dir()
    src = str(df["source"].iloc[0])
    path = ECON_CACHE_DIR / f"{logical}_{src}.parquet"
    df.to_parquet(path, index=False)
    logger.info("Cached %d rows -> %s", len(df), path)
    return path


def fetch_logical_indicator(logical: str, chain: list[dict[str, Any]]) -> pd.DataFrame:
    """Try each source in order until a non-empty series is returned."""
    for spec in chain:
        source = spec.get("source")
        try:
            if source == "hcp":
                kind = spec.get("kind") or ("cpi" if logical == "cpi" else "ppi")
                df = hcp.fetch_hcp_series(kind, logical_code=logical)  # type: ignore[arg-type]
            elif source == "fred":
                sid = spec.get("series_id")
                if not sid:
                    continue
                df = fred.fetch_series(sid, logical_code=logical)
            elif source == "fred_resolve":
                kind = spec.get("kind")
                if kind == "mar_cpi_monthly":
                    df = fred_morocco.fetch_morocco_cpi_monthly(logical_code=logical)
                elif kind == "mar_cpi_yoy":
                    df = fred_morocco.fetch_morocco_cpi_yoy(logical_code=logical)
                else:
                    logger.warning("Unknown fred_resolve kind %r for %s", kind, logical)
                    continue
            elif source == "worldbank":
                ind = spec.get("indicator")
                if not ind:
                    continue
                cc = spec.get("country") or DEFAULT_COUNTRY_ISO3
                df = worldbank.fetch_indicator(cc, ind, logical_code=logical)
            elif source == "bam":
                df = bam.load_policy_rates_csv()
                if not df.empty:
                    df = df.copy()
                    df["indicator_code"] = logical
            else:
                logger.warning("Unknown source %r in chain for %s", source, logical)
                continue
        except Exception as e:
            logger.warning("Fetcher error %s %s: %s", logical, spec, e)
            continue

        if df is not None and not df.empty:
            _write_cache(logical, df)
            return df

    logger.error("All sources failed for logical indicator %s", logical)
    return normalize_indicator_df(pd.DataFrame())


def fetch_all(source_filter: str | None = None) -> pd.DataFrame:
    """
    Fetch every configured logical indicator and concatenate into one frame
    (with `fetched_at`), suitable for `econ_indicators` table.
    """
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    parts: list[pd.DataFrame] = []

    for logical, chain in INDICATOR_CHAIN.items():
        if source_filter and source_filter != "all":
            chain = [s for s in chain if s.get("source") == source_filter]
            if not chain:
                continue
        df = fetch_logical_indicator(logical, chain)
        if df.empty:
            continue
        df = df.copy()
        df["fetched_at"] = now
        parts.append(df)

    if not parts:
        return pd.DataFrame(
            columns=[
                "source",
                "indicator_code",
                "country",
                "date",
                "value",
                "frequency",
                "unit",
                "fetched_at",
            ]
        )

    out = pd.concat(parts, ignore_index=True)
    return out


def load_econ_indicators_to_sqlite(df: pd.DataFrame) -> None:
    """Replace `econ_indicators` table in the project SQLite DB."""
    import sqlite3

    if df.empty:
        logger.warning("No indicator rows to load; skipping SQLite write")
        return

    ECON_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ECON_DB_PATH))
    try:
        conn.execute("DROP TABLE IF EXISTS econ_indicators")
        df.to_sql("econ_indicators", conn, if_exists="replace", index=False)
        logger.info("Loaded %d rows -> econ_indicators", len(df))
    finally:
        conn.close()
