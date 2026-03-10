"""
EXTRACT – Read sheets from any Excel file defined in SOURCES.
"""

import logging

import pandas as pd

from config.settings import DATA_RAW_DIR, SOURCES

logger = logging.getLogger(__name__)


def extract_sheet(filepath, cfg: dict) -> pd.DataFrame:
    """
    Read a single sheet from *filepath* using the extraction parameters in *cfg*.
    Returns a raw DataFrame exactly as read from the file.
    """
    logger.info("Extracting sheet '%s' from %s", cfg["sheet_name"], filepath.name)

    df = pd.read_excel(
        filepath,
        sheet_name=cfg["sheet_name"],
        header=cfg.get("header_row", 0),
        usecols=cfg.get("usecols"),
        engine="openpyxl",
    )
    logger.info("  → %d rows × %d columns", len(df), len(df.columns))
    return df


def extract_all() -> dict[str, tuple[pd.DataFrame, dict]]:
    """
    Extract every sheet across all files defined in SOURCES.
    Returns {table_name: (DataFrame, sheet_cfg), ...}.
    """
    frames: dict[str, tuple[pd.DataFrame, dict]] = {}
    for filename, tables in SOURCES.items():
        filepath = DATA_RAW_DIR / filename
        if not filepath.exists():
            logger.warning("File not found, skipping: %s", filepath)
            continue
        for table_name, cfg in tables.items():
            try:
                df = extract_sheet(filepath, cfg)
                frames[table_name] = (df, cfg)
            except Exception as exc:
                logger.warning("Skipping '%s': %s", table_name, exc)
    return frames
