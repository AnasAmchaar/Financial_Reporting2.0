"""
EXTRACT – Read sheets from any Excel file defined in SOURCES.
"""

import logging
import pandas as pd

from config.settings import DATA_RAW_DIR, SOURCES

logger = logging.getLogger(__name__)


def read_excel_sheet(filepath: str, sheet_config: dict) -> pd.DataFrame:
    """
    Read a single sheet from *filepath* using the extraction parameters in *sheet_config*.
    Returns a raw DataFrame exactly as read from the file.

    Args:
        filepath (str): Path to the Excel file.
        sheet_config (dict): Extraction parameters for the sheet.

    Returns:
        pd.DataFrame: The extracted sheet data.
    """
    logger.info("Extracting sheet '%s' from %s", sheet_config["sheet_name"], filepath)

    try:
        df = pd.read_excel(
            filepath,
            sheet_name=sheet_config["sheet_name"],
            header=sheet_config.get("header_row", 0),
            usecols=sheet_config.get("usecols"),
            engine="openpyxl",
        )
        logger.info("  → %d rows × %d columns", len(df), len(df.columns))
        return df
    except Exception as exc:
        logger.warning("Failed to extract sheet: %s", exc)
        return None


def extract_all_sheets() -> dict[str, tuple[pd.DataFrame, dict]]:
    """
    Extract every sheet across all files defined in SOURCES.
    Returns {table_name: (DataFrame, sheet_cfg), ...}.

    Returns:
        dict[str, tuple[pd.DataFrame, dict]]: Extracted sheets and their configurations.
    """
    extracted_sheets: dict[str, tuple[pd.DataFrame, dict]] = {}
    for filename, tables in SOURCES.items():
        filepath = DATA_RAW_DIR / filename
        if not filepath.exists():
            logger.warning("File not found, skipping: %s", filepath)
            continue
        for table_name, cfg in tables.items():
            sheet_data = read_excel_sheet(filepath, cfg)
            if sheet_data is not None:
                extracted_sheets[table_name] = (sheet_data, cfg)
    return extracted_sheets
