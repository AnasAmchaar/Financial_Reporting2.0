"""
run_etl.py – Main entry point for the ETL pipeline.

Usage:
    python run_etl.py                  # process all sources
    python run_etl.py <table_name>     # process a single table
"""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import LOG_DIR, LOG_FILE, LOG_LEVEL
from etl.pipeline import run_etl_all, run_etl_single


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


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("etl")

    if len(sys.argv) > 1:
        r = run_etl_single(sys.argv[1])
        if not r.ok:
            logger.error("%s", r.message or r.tables[0].error)
            sys.exit(1)
        logger.info("ETL OK: %s (%d rows)", r.tables[0].table, r.tables[0].rows)
    else:
        r = run_etl_all()
        if not r.ok:
            logger.error("%s", r.message)
            sys.exit(1)
        logger.info("ETL OK: %d table(s)", len(r.tables))
