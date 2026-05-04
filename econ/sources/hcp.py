"""HCP (Haut-Commissariat au Plan) — scrape listing + latest article pages for IPC / IPPI Excel."""

from __future__ import annotations

import logging
import re
from typing import Literal
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from econ.sources.base import (
    fetch_url_bytes,
    find_xlsx_hrefs,
    normalize_indicator_df,
    parse_hcp_excel_all_sheets,
)

logger = logging.getLogger(__name__)

# Listing pages (https://hcp.ma/)
IPC_PAGE = "https://hcp.ma/Indices-des-prix-a-la-consommation-IPC_r348.html"
PPI_PAGE = "https://hcp.ma/Indices-des-prix-a-la-production-industrielle-IPPI_r624.html"

_ARTICLE_ID = re.compile(r"_a(\d+)\.html", re.I)


def _abs_url(href: str) -> str:
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return urljoin("https://hcp.ma", href)
    return urljoin("https://hcp.ma/", href)


def _latest_article_urls(listing_html: str, kind: Literal["cpi", "ppi"]) -> list[str]:
    """Collect article URLs from a thematic listing page, newest `_a####` first."""
    soup = BeautifulSoup(listing_html, "lxml")
    scored: list[tuple[int, str]] = []
    for a in soup.find_all("a", href=True):
        full = _abs_url(a["href"])
        low = full.lower()
        if "wmaker.net" in low or "testhcp" in low:
            continue
        m = _ARTICLE_ID.search(full)
        if not m:
            continue
        aid = int(m.group(1))
        if kind == "cpi":
            if not re.search(r"Indice-des-prix-a-la-consommation-IPC|IPC-Base-100", full, re.I):
                continue
            if re.search(r"grandes-divisions|par-grandes-divisions", full, re.I):
                continue
        else:
            if not re.search(
                r"Indice-des-prix-a-la-production|IPPI|production-industrielle|"
                r"production-des-industries",
                full,
                re.I,
            ):
                continue
        scored.append((aid, full))
    scored.sort(key=lambda x: -x[0])
    # de-dup preserve order
    seen: set[str] = set()
    out: list[str] = []
    for _aid, u in scored:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _pick_excel_url(urls: list[str], kind: Literal["cpi", "ppi"]) -> str | None:
    if not urls:
        return None
    low = [u.lower() for u in urls]

    def score(i: int) -> int:
        u = low[i]
        s = 0
        if kind == "cpi":
            if "ipc" in u:
                s += 5
            if "consommation" in u:
                s += 2
        else:
            if "ippi" in u or "ippiem" in u or "production" in u:
                s += 5
        if u.endswith(".xlsx"):
            s += 2
        if u.endswith(".xls") and not u.endswith(".xlsx"):
            s += 1
        return s

    best_i = max(range(len(urls)), key=score)
    if score(best_i) == 0:
        return urls[0]
    return urls[best_i]


def _download_excel_from_articles(article_urls: list[str], kind: Literal["cpi", "ppi"]) -> bytes | None:
    for art in article_urls[:12]:
        try:
            html = fetch_url_bytes(art).decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug("HCP article fetch skip %s: %s", art, e)
            continue
        hrefs = find_xlsx_hrefs(html)
        if not hrefs:
            # Some pages embed attachment links without hcp.ma host
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                h = a["href"].strip().lower()
                if ".xlsx" in h or ".xls" in h:
                    hrefs.append(_abs_url(a["href"]))
        if not hrefs:
            continue
        xurl = _pick_excel_url(hrefs, kind)
        if not xurl:
            continue
        try:
            return fetch_url_bytes(xurl)
        except Exception as e:
            logger.debug("HCP excel download skip %s: %s", xurl, e)
            continue
    return None


def fetch_hcp_series(
    kind: Literal["cpi", "ppi"],
    *,
    logical_code: str,
    country: str = "MAR",
) -> pd.DataFrame:
    page = IPC_PAGE if kind == "cpi" else PPI_PAGE
    unit = "index_hcp_2017_100" if kind == "cpi" else "index_hcp_ippiem"

    try:
        listing_html = fetch_url_bytes(page).decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("HCP listing fetch failed (%s): %s", kind, e)
        return normalize_indicator_df(pd.DataFrame())

    blob: bytes | None = None

    # 1) Direct XLSX on listing (older site layout)
    hrefs_listing = find_xlsx_hrefs(listing_html)
    if hrefs_listing:
        xurl = _pick_excel_url(hrefs_listing, kind)
        if xurl:
            try:
                blob = fetch_url_bytes(xurl)
            except Exception as e:
                logger.debug("HCP listing excel failed: %s", e)

    # 2) Latest thematic articles (current hcp.ma layout)
    if blob is None:
        articles = _latest_article_urls(listing_html, kind)
        if not articles:
            logger.warning("No HCP article links found for %s", kind)
            return normalize_indicator_df(pd.DataFrame())
        blob = _download_excel_from_articles(articles, kind)

    if blob is None:
        logger.warning("No downloadable HCP Excel for %s", kind)
        return normalize_indicator_df(pd.DataFrame())

    parsed = parse_hcp_excel_all_sheets(blob)
    if parsed is None or parsed.empty:
        logger.warning("Could not parse HCP Excel for %s", kind)
        return normalize_indicator_df(pd.DataFrame())

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(parsed["date"]),
            "value": pd.to_numeric(parsed["value"], errors="coerce"),
            "frequency": "M",
            "unit": unit,
            "source": "hcp",
            "indicator_code": logical_code,
            "country": country,
        }
    )
    return normalize_indicator_df(out)
