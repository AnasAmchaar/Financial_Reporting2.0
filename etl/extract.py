"""
EXTRACT – Read sheets from the DISLOG Business Review Excel file.
"""

import logging
from pathlib import Path

import pandas as pd

from config.settings import DATA_RAW_DIR, EXCEL_FILENAME, SHEET_CONFIG

logger = logging.getLogger(__name__)


def extract_sheet(source_key: str) -> pd.DataFrame:
    """
    Read a single sheet identified by its key in SHEET_CONFIG.
    Returns a raw DataFrame exactly as read from the file.
    """
    cfg = SHEET_CONFIG.get(source_key)
    if cfg is None:
        raise KeyError(f"Unknown source key '{source_key}'. "
                       f"Available: {list(SHEET_CONFIG.keys())}")

    filepath = DATA_RAW_DIR / EXCEL_FILENAME
    if not filepath.exists():
        raise FileNotFoundError(f"Expected file not found: {filepath}")

    logger.info("Extracting '%s' from sheet '%s'", source_key, cfg["sheet_name"])

    df = pd.read_excel(
        filepath,
        sheet_name=cfg["sheet_name"],
        header=cfg.get("header_row", 0),
        usecols=cfg.get("usecols"),
        engine="openpyxl",
    )
    logger.info("  → %d rows × %d columns", len(df), len(df.columns))
    return df


def extract_all() -> dict[str, pd.DataFrame]:
    """
    Extract every sheet defined in SHEET_CONFIG.
    Returns {source_key: DataFrame, ...}.
    """
    frames: dict[str, pd.DataFrame] = {}
    for key in SHEET_CONFIG:
        try:
            frames[key] = extract_sheet(key)
        except Exception as exc:
            logger.warning("Skipping '%s': %s", key, exc)
    return frames
