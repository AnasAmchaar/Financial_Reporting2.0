"""
Central configuration for the ETL pipeline.
All paths, DB settings, and column mappings live here.

To add a new Excel file:
  1. Drop it in  data/raw/
  2. Add an entry to  SOURCES  below.

Each source entry needs:
  - file      : filename inside data/raw/
  - sheets    : dict of  table_name → sheet extraction config

Each sheet config accepts:
  - sheet_name     : name of the Excel tab
  - header_row     : 0-based row where column headers live (default 0)
  - usecols        : Excel column range e.g. "A:G" (None = all)
  - transform_type : which generic transform to apply (see list below)
  - transform_opts : extra kwargs passed to the transform (optional)

Available transform_type values:
  "transactional"  – rows with category columns + month/year + amount
  "budget"         – partner/channel/month/amount with a budget label
  "balance_sheet"  – id columns + monthly date-columns → melted long
  "mapping"        – account code → hierarchy levels
  "aging"          – entity name + aging buckets
  "time_series"    – id columns + monthly date-columns → melted long
  "generic"        – just clean names, drop empties, deduplicate
"""

from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_DIR = PROJECT_ROOT / "db"
LOG_DIR = PROJECT_ROOT / "logs"

DB_PATH = DB_DIR / "pfa.db"

# ── Logging ─────────────────────────────────────────────────────────────────
LOG_FILE = LOG_DIR / "etl.log"
LOG_LEVEL = "INFO"

# ── Transform settings ──────────────────────────────────────────────────────
DROP_FULL_NA_ROWS = True

# ── Data sources ────────────────────────────────────────────────────────────
# Define one or more Excel files.  Each file lists the sheets to extract.
# You can add as many files / sheets as you need.

SOURCES = {
    # ── Example source (replace with your own files) ────────────────────────
    "DISLOG_BR_Template 08-2023.xlsx": {
        # ----- Revenue / Sales (actual) -----
        "data_reel": {
            "sheet_name": "DATA_REEL",
            "header_row": 0,
            "usecols": "A:G",
            "transform_type": "transactional",
        },
        # ----- Budget / Forecast -----
        "data_budget_topline": {
            "sheet_name": "DATA_BUDGET",
            "header_row": 7,
            "usecols": "B:E",
            "transform_type": "budget",
            "transform_opts": {"label": "topline_net"},
        },
        "data_budget_topline_net": {
            "sheet_name": "DATA_BUDGET",
            "header_row": 7,
            "usecols": "G:J",
            "transform_type": "budget",
            "transform_opts": {"label": "topline_net_net"},
        },
        "data_budget_margin": {
            "sheet_name": "DATA_BUDGET",
            "header_row": 7,
            "usecols": "L:N",
            "transform_type": "budget",
            "transform_opts": {"label": "margin_net_net"},
        },
        "data_budget_pl": {
            "sheet_name": "DATA_BUDGET",
            "header_row": 7,
            "usecols": "T:W",
            "transform_type": "budget",
            "transform_opts": {"label": "pl_accounts"},
        },
        # ----- Balance Sheet -----
        "data_bilan": {
            "sheet_name": "DATA_BILAN",
            "header_row": 9,
            "usecols": None,
            "transform_type": "balance_sheet",
        },
        # ----- Account Mapping -----
        "mapping": {
            "sheet_name": "MAPPING",
            "header_row": 0,
            "usecols": "A:F",
            "transform_type": "mapping",
        },
        "mapping_opex": {
            "sheet_name": "MAPPING",
            "header_row": 0,
            "usecols": "I:K",
            "transform_type": "mapping",
        },
        # ----- Clients Aging -----
        "clients": {
            "sheet_name": "CLT",
            "header_row": 8,
            "usecols": "J:Q",
            "transform_type": "aging",
            "transform_opts": {"entity_type": "client"},
        },
        # ----- Suppliers Aging -----
        "suppliers": {
            "sheet_name": "FRS",
            "header_row": 8,
            "usecols": "J:P",
            "transform_type": "aging",
            "transform_opts": {"entity_type": "supplier"},
        },
        # ----- HR Synthesis -----
        "hr_synthesis": {
            "sheet_name": "Synthèse RH",
            "header_row": 7,
            "usecols": "B:O",
            "transform_type": "time_series",
        },
    },

    # ── Add more files here ─────────────────────────────────────────────────
    # "another_report.xlsx": {
    #     "revenue": {
    #         "sheet_name": "Sheet1",
    #         "header_row": 0,
    #         "usecols": None,
    #         "transform_type": "transactional",
    #     },
    # },
}
