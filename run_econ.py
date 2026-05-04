"""
run_econ.py – Economic adjustment layer entry point.

Usage:
    python run_econ.py fetch              # refresh indicators into econ_indicators
    python run_econ.py fetch --source hcp # only try HCP-backed chain steps
    python run_econ.py apply              # build *_real tables from econ_indicators
    python run_econ.py all                  # fetch + apply
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from config.settings import LOG_DIR, LOG_FILE, LOG_LEVEL
from econ.apply import apply_all
from econ.fetcher import fetch_all, load_econ_indicators_to_sqlite


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


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    parser = argparse.ArgumentParser(description="Economic adjustment layer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="Download macro series and refresh econ_indicators")
    p_fetch.add_argument(
        "--source",
        type=str,
        default=None,
        help="Only run chain steps for this source label (e.g. hcp, fred, worldbank, bam)",
    )

    sub.add_parser("apply", help="Build *_real tables from SQLite + econ_indicators")

    p_all = sub.add_parser("all", help="fetch then apply")
    p_all.add_argument(
        "--source",
        type=str,
        default=None,
        help="Only run chain steps for this source label (e.g. hcp, fred, worldbank, bam)",
    )

    args = parser.parse_args()
    setup_logging()
    log = logging.getLogger("econ")

    if args.cmd == "fetch":
        log.info("ECON FETCH start")
        df = fetch_all(source_filter=args.source)
        load_econ_indicators_to_sqlite(df)
        log.info("ECON FETCH done (%d indicator rows)", len(df))
        return

    if args.cmd == "apply":
        log.info("ECON APPLY start")
        apply_all()
        log.info("ECON APPLY done")
        return

    if args.cmd == "all":
        log.info("ECON ALL start (fetch)")
        df = fetch_all(source_filter=args.source)
        load_econ_indicators_to_sqlite(df)
        log.info("ECON ALL apply")
        apply_all()
        log.info("ECON ALL done")
        return


if __name__ == "__main__":
    main()
