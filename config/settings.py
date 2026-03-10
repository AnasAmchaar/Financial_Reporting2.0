"""
Central configuration for the ETL pipeline.
All paths, DB settings, and column mappings live here.
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

# ── Excel source file ───────────────────────────────────────────────────────
EXCEL_FILENAME = "DISLOG_BR_Template 08-2023.xlsx"

# Sheets to extract and their extraction config.
# header_row: 0-based row index where column headers are located.
# usecols:    Excel column letters to read (None = all).
# data_start: 0-based row index where actual data starts (used as skiprows).
SHEET_CONFIG = {
    # ----- Revenue / Sales (actual) -----
    "data_reel": {
        "sheet_name": "DATA_REEL",
        "header_row": 0,
        "usecols": "A:G",       # PARTENAIRE, MARQUE, Channel, MACHINE, mois, YEAR, AMOUNT
    },
    # ----- Budget / Forecast -----
    "data_budget_topline": {
        "sheet_name": "DATA_BUDGET",
        "header_row": 7,         # Row 8 has headers (0-indexed = 7)
        "usecols": "B:E",       # PARTENAIRE, Channel, MOIS, AMOUNT  (Topline Net)
    },
    "data_budget_topline_net": {
        "sheet_name": "DATA_BUDGET",
        "header_row": 7,
        "usecols": "G:J",       # PARTENAIRE, Channel, MOIS, AMOUNT  (Topline Net Net)
    },
    "data_budget_margin": {
        "sheet_name": "DATA_BUDGET",
        "header_row": 7,
        "usecols": "L:N",       # PARTENAIRE, MOIS, AMOUNT  (Margin Net Net)
    },
    "data_budget_pl": {
        "sheet_name": "DATA_BUDGET",
        "header_row": 7,
        "usecols": "T:W",       # Comptes, N1, N2, N3 (P&L mapping)
    },
    # ----- Balance Sheet -----
    "data_bilan": {
        "sheet_name": "DATA_BILAN",
        "header_row": 9,         # Row 10 has headers
        "usecols": None,         # All columns (CLASSE, Compte, monthly values)
    },
    # ----- Account Mapping -----
    "mapping": {
        "sheet_name": "MAPPING",
        "header_row": 0,
        "usecols": "A:F",       # Comptes, N1, N2, N3, N4, flag
    },
    "mapping_opex": {
        "sheet_name": "MAPPING",
        "header_row": 0,
        "usecols": "I:K",       # N1(OPEX label), N2, N3, N4
    },
    # ----- Clients Aging -----
    "clients": {
        "sheet_name": "CLT",
        "header_row": 8,
        "usecols": "J:Q",       # Client name + aging buckets
    },
    # ----- Suppliers Aging -----
    "suppliers": {
        "sheet_name": "FRS",
        "header_row": 8,
        "usecols": "J:P",       # Supplier name + aging buckets
    },
    # ----- HR Synthesis -----
    "hr_synthesis": {
        "sheet_name": "Synthèse RH",
        "header_row": 7,         # Row 8 has month-date headers
        "usecols": "B:O",
    },
}

# ── Transform settings ──────────────────────────────────────────────────────
DROP_FULL_NA_ROWS = True
