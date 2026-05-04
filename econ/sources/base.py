"""Shared types and helpers for macro indicator sources."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLS = ("date", "value", "frequency", "unit", "source", "indicator_code", "country")


@dataclass
class IndicatorObservation:
    """Single observation (usually one month)."""

    date: pd.Timestamp
    value: float
    frequency: str
    unit: str
    source: str
    indicator_code: str
    country: str


def indicator_df_schema() -> dict[str, Any]:
    return {
        "date": "datetime64[ns]",
        "value": "float64",
        "frequency": "string",
        "unit": "string",
        "source": "string",
        "indicator_code": "string",
        "country": "string",
    }


def normalize_indicator_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure schema, sorted unique by date."""
    if df is None or df.empty:
        return pd.DataFrame(columns=list(REQUIRED_COLS))
    for c in REQUIRED_COLS:
        if c not in df.columns:
            raise ValueError(f"Missing column {c!r} in indicator DataFrame")
    out = df[list(REQUIRED_COLS)].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["date", "value"])
    out = out.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return out


def month_start(year: int, month: int) -> pd.Timestamp:
    return pd.Timestamp(year=year, month=month, day=1)


_COL_YEAR = re.compile(r"ann[eé]e|year", re.I)
_COL_MONTH = re.compile(r"mois|month", re.I)
_COL_INDEX = re.compile(r"indice|ipc|ippiem|ippi|index", re.I)


def parse_year_month_index_frame(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Try to interpret a wide-ish HCP-style table with year, month, and index columns.
    Returns a DataFrame with columns date, value or None.
    """
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    ycol = mcol = vcol = None
    for c in df.columns:
        if _COL_YEAR.search(c):
            ycol = c
        if _COL_MONTH.search(c):
            mcol = c
        if _COL_INDEX.search(c) and "variation" not in c and "taux" not in c:
            if vcol is None:
                vcol = c

    if ycol and mcol and vcol:
        sub = df[[ycol, mcol, vcol]].dropna(how="all")
        years = pd.to_numeric(sub[ycol], errors="coerce")
        months = pd.to_numeric(sub[mcol], errors="coerce")
        vals = pd.to_numeric(sub[vcol], errors="coerce")
        mask = years.notna() & months.notna() & vals.notna()
        if not mask.any():
            return None
        dates = [month_start(int(y), int(m)) for y, m in zip(years[mask], months[mask])]
        return pd.DataFrame({"date": dates, "value": vals[mask].values})

    # Single sheet: first col year, second month, third value (common layout)
    if len(df.columns) >= 3:
        c0, c1, c2 = df.columns[0], df.columns[1], df.columns[2]
        y = pd.to_numeric(df[c0], errors="coerce")
        m = pd.to_numeric(df[c1], errors="coerce")
        v = pd.to_numeric(df[c2], errors="coerce")
        mask = y.notna() & m.notna() & v.notna() & (m >= 1) & (m <= 12) & (y >= 1990) & (y <= 2100)
        if mask.sum() >= 6:
            dates = [month_start(int(yr), int(mo)) for yr, mo in zip(y[mask], m[mask])]
            return pd.DataFrame({"date": dates, "value": v[mask].values})

    return None


def parse_hcp_excel_all_sheets(content: bytes) -> pd.DataFrame | None:
    """Try reading all sheets and pick the best parse for IPC/IPPIEM-style data."""
    import io

    try:
        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, engine="openpyxl")
    except Exception as e:
        logger.warning("HCP Excel read failed: %s", e)
        return None

    best: pd.DataFrame | None = None
    best_n = 0
    for _name, raw in sheets.items():
        if raw is None or raw.empty:
            continue
        # try different header rows
        for skip in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            try:
                chunk = raw.iloc[skip:].copy()
                chunk.columns = [str(x).strip() for x in chunk.iloc[0]]
                chunk = chunk.iloc[1:].reset_index(drop=True)
            except Exception:
                chunk = raw.copy()
            parsed = parse_year_month_index_frame(chunk)
            if parsed is not None and len(parsed) > best_n:
                best = parsed
                best_n = len(parsed)
        parsed0 = parse_year_month_index_frame(raw)
        if parsed0 is not None and len(parsed0) > best_n:
            best = parsed0
            best_n = len(parsed0)

    return best


def find_xlsx_hrefs(html: str, domain_must_contain: str = "hcp.ma") -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        low = href.lower()
        if ".xlsx" not in low and ".xls" not in low:
            continue
        if href.startswith("http"):
            url = href
        else:
            root = href if href.startswith("/") else "/" + href
            url = "https://hcp.ma" + root
        if domain_must_contain in url.replace("www.hcp.ma", "hcp.ma"):
            out.append(url)
    return out


def fetch_url_bytes(url: str, timeout: int = 60) -> bytes:
    import requests

    r = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        },
    )
    r.raise_for_status()
    return r.content
