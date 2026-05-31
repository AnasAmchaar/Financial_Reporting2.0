from __future__ import annotations

import os

from fastapi import APIRouter

from config.settings import DB_PATH, DATA_RAW_DIR, PROJECT_ROOT
from config.econ_settings import INDICATOR_CHAIN
from ecoeye2.server.dbutil import connect

router = APIRouter()


@router.get("/econ/settings-preview")
def settings_preview():
    """Non-secret snapshot of adjustment config (public for Settings UI)."""
    from config.econ_settings import ADJUSTMENTS, BASE_PERIOD, DISCOUNT

    return {
        "base_period": BASE_PERIOD,
        "discount": DISCOUNT,
        "adjustment_tables": list(ADJUSTMENTS.keys()),
    }


@router.get("/health")
def health():
    return {
        "app": "EcoEye2",
        "status": "ok",
        "db_path": str(DB_PATH),
        "raw_dir": str(DATA_RAW_DIR),
        "project_root": str(PROJECT_ROOT),
        "fred_api_key_set": bool(os.environ.get("FRED_API_KEY", "").strip()),
        "ecoeye2_api_key_set": bool(os.environ.get("ECOEYE2_API_KEY", "").strip()),
    }


@router.get("/econ/status")
def econ_status():
    """Macro ingestion snapshot for the UI (no secrets)."""
    fred_set = bool(os.environ.get("FRED_API_KEY", "").strip())
    indicators: dict[str, dict[str, str | None]] = {}
    max_fetched: str | None = None
    
    # Pre-populate all expected indicators with 'bad' status
    for key in INDICATOR_CHAIN.keys():
        indicators[key] = {
            "source": None,
            "fetched_at": None,
            "status": "bad"
        }

    conn = connect()
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='econ_indicators'"
        )
        if not cur.fetchone():
            return {
                "fred_api_key_set": fred_set,
                "indicators": indicators,
                "econ_indicators_last_fetched_at": max_fetched,
                "note": "econ_indicators table not found; run macro fetch from Adjustments.",
            }

        cur = conn.execute("SELECT MAX(fetched_at) AS mx FROM econ_indicators")
        r0 = cur.fetchone()
        if r0 and r0["mx"] is not None:
            max_fetched = str(r0["mx"])

        # Fetch all distinct indicators and their latest fetch time
        cur = conn.execute(
            """
            SELECT indicator_code, source, fetched_at
            FROM econ_indicators
            ORDER BY fetched_at DESC
            """
        )
        seen: set[str] = set()
        for row in cur:
            code = row["indicator_code"]
            if not code or code in seen:
                continue
            seen.add(code)
            
            # If the code is in our expected indicators, update it to good
            if code in indicators:
                indicators[str(code)] = {
                    "source": str(row["source"]) if row["source"] is not None else None,
                    "fetched_at": str(row["fetched_at"]) if row["fetched_at"] is not None else None,
                    "status": "good"
                }
    finally:
        conn.close()

    return {
        "fred_api_key_set": fred_set,
        "indicators": indicators,
        "econ_indicators_last_fetched_at": max_fetched,
    }
