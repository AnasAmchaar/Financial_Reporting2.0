"""
run_etl.py – Main entry point for the ETL pipeline.

Usage:
    python run_etl.py                  # process all sources
    python run_etl.py data_reel        # process a single source
"""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import LOG_DIR, LOG_FILE, LOG_LEVEL, SHEET_CONFIG
from etl.extract import extract_all, extract_sheet
from etl.transform import transform, transform_all
from etl.load import load_all, load_to_sqlite


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_single(source_key: str) -> None:
    """Run the ETL pipeline for one source."""
    logger = logging.getLogger("etl")
    logger.info("═" * 60)
    logger.info("ETL START – source: %s", source_key)

    raw_df = extract_sheet(source_key)
    clean_df = transform(raw_df, source_key)
    load_to_sqlite(clean_df, table_name=source_key)

    logger.info("ETL DONE  – source: %s", source_key)
    logger.info("═" * 60)


def run_all() -> None:
    """Run the ETL pipeline for every configured source."""
    logger = logging.getLogger("etl")
    logger.info("═" * 60)
    logger.info("ETL START – all sources (%d sheets)", len(SHEET_CONFIG))

    raw_frames = extract_all()
    if not raw_frames:
        logger.warning("No data extracted. Check the Excel file in data/raw/.")
        return

    clean_frames = transform_all(raw_frames)
    load_all(clean_frames, to_sqlite=True)

    logger.info("ETL DONE  – processed %d source(s)", len(clean_frames))
    logger.info("═" * 60)


if __name__ == "__main__":
    setup_logging()

    if len(sys.argv) > 1:
        run_single(sys.argv[1])
    else:
        run_all()
