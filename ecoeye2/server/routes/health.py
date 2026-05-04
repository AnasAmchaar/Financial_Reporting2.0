from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from config.settings import DB_PATH, DATA_RAW_DIR, PROJECT_ROOT
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
    import os

    return {
        "app": "EcoEye2",
        "status": "ok",
        "db_path": str(DB_PATH),
        "raw_dir": str(DATA_RAW_DIR),
        "project_root": str(PROJECT_ROOT),
        "fred_api_key_set": bool(os.environ.get("FRED_API_KEY", "").strip()),
        "ecoeye2_api_key_set": bool(os.environ.get("ECOEYE2_API_KEY", "").strip()),
    }
