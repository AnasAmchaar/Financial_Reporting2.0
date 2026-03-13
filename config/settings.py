"""
Central configuration for the ETL pipeline.

This module contains the central configuration for the ETL pipeline.
It includes paths, database settings, column mappings, and data sources.

To add a new Excel file:
  1. Drop it in `data/raw/`.
  2. Add an entry to `SOURCES` below.

Each source entry needs:
  - `file`: filename inside `data/raw/`.
  - `sheets`: dict of `table_name` → sheet extraction config.

Each sheet config accepts:
  - `sheet_name`: name of the Excel tab.
  - `header_row`: 0-based row where column headers live (default 0).
  - `usecols`: Excel column range e.g. "A:G" (None = all).
  - `transform_type`: which generic transform to apply (see list below).
  - `transform_opts`: extra kwargs passed to the transform (optional).

Available `transform_type` values:
  - `"transactional"`: rows with category columns + month/year + amount.
  - `"budget"`: partner/channel/month/amount with a budget label.
  - `"balance_sheet"`: id columns + monthly date-columns → melted long.
  - `"mapping"`: account code → hierarchy levels.
  - `"aging"`: entity name + aging buckets.
  - `"time_series"`: id columns + monthly date-columns → melted long.
  - `"generic"`: just clean names, drop empties, deduplicate.
"""

import os
from pathlib import Path


class Config:
    """
    Central configuration for the ETL pipeline.
    """

    def __init__(self):
        # ── Project Paths ───────────────────────────────────────────────────────────
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_raw_dir = self.project_root / "data" / "raw"
        self.data_processed_dir = self.project_root / "data" / "processed"
        self.db_dir = self.project_root / "db"
        self.log_dir = self.project_root / "logs"

        # ── Database Settings ──────────────────────────────────────────────────────
        self.db_path = self.db_dir / "pfa.db"

        # ── Logging Settings ───────────────────────────────────────────────────────
        self.log_file = self.log_dir / "etl.log"
        self.log_level = "INFO"

        # ── Data Transform Settings ─────────────────────────────────────────────────
        self.drop_full_na_rows = True

        # ── Data Sources ────────────────────────────────────────────────────────────
        self.sources = {
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

    @property
    def data_raw_dir_path(self):
        """
        Returns the path to the data/raw directory.
        """
        return self.data_raw_dir

    @property
    def data_processed_dir_path(self):
        """
        Returns the path to the data/processed directory.
        """
        return self.data_processed_dir

    @property
    def db_path_path(self):
        """
        Returns the path to the database file.
        """
        return self.db_path

    @property
    def log_file_path(self):
        """
        Returns the path to the log file.
        """
        return self.log_file

    @property
    def log_level_str(self):
        """
        Returns the log level as a string.
        """
        return self.log_level

    @property
    def drop_full_na_rows_bool(self):
        """
        Returns whether to drop full NA rows.
        """
        return self.drop_full_na_rows

    @property
    def sources_dict(self):
        """
        Returns the data sources.
        """
        return self.sources


# Create a Config instance
config = Config()
