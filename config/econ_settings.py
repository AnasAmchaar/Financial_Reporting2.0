"""
Economic adjustment layer configuration.

- BASE_PERIOD: YYYY-MM for deflation anchor (first day of month).
- ADJUSTMENTS: per SQLite table → how to build dates and which deflator to use.
- INDICATOR_CHAIN: logical indicators and ordered source fallbacks.
- DISCOUNT: time-value (present value) settings.
"""

from pathlib import Path

from config.settings import DB_PATH, PROJECT_ROOT

# ── Paths ───────────────────────────────────────────────────────────────────
ECON_CACHE_DIR = PROJECT_ROOT / "data" / "econ" / "cache"
BAM_POLICY_RATES_CSV = Path(__file__).resolve().parent / "bam_policy_rates.csv"

# Same DB as ETL
ECON_DB_PATH = DB_PATH

# ── Deflation anchor ────────────────────────────────────────────────────────
BASE_PERIOD = "2023-12"  # YYYY-MM

# ── Discount / time-value ───────────────────────────────────────────────────
DISCOUNT = {
    "mode": "constant",  # "constant" | "series"
    "rate": 0.025,  # annual, e.g. BAM key rate when mode is constant
    "ref_date": "2023-12-01",  # PV as-of this date (YYYY-MM-DD)
    # When mode is "series", use indicator_code from econ_indicators (e.g. cpi_yoy as decimal)
    "series_indicator": "cpi_yoy",
    "series_source_priority": ("fred", "worldbank", "hcp"),
}

# ── Logical indicators: try sources in order until data is returned ───────────
INDICATOR_CHAIN = {
    "cpi": [
        {"source": "hcp", "kind": "cpi"},
        {"source": "fred_resolve", "kind": "mar_cpi_monthly"},
        {"source": "worldbank", "indicator": "FP.CPI.TOTL", "country": "MAR"},
    ],
    "ppi": [
        {"source": "hcp", "kind": "ppi"},
        # Annual proxy when monthly IPPI Excel is unavailable (rebased in apply via interpolation).
        {"source": "worldbank", "indicator": "NY.GDP.DEFL.ZS", "country": "MAR"},
    ],
    "cpi_yoy": [
        {"source": "fred_resolve", "kind": "mar_cpi_yoy"},
        {"source": "worldbank", "indicator": "FP.CPI.TOTL.ZG", "country": "MAR"},
    ],
    "policy_rate": [
        {"source": "bam", "kind": "policy_rate"},
    ],
}

# ISO3 country for World Bank / defaults
DEFAULT_COUNTRY_ISO3 = "MAR"

# ── Per-table adjustment rules (SQLite table name → spec) ───────────────────
# date_from: build period-start date from year + month columns
# date_col: use existing column
# wide_amount: if True, melt columns that parse as dates into (date, amount)
# as_of_date: fixed snapshot date for aging tables (YYYY-MM-DD)
ADJUSTMENTS = {
    "data_reel": {
        "value_col": "amount",
        "deflator": "cpi",
        "date_from": ("year", "month"),
    },
    # Workbook budget sheets often have month only; align with template fiscal year.
    "data_budget_topline": {
        "value_col": "amount",
        "deflator": "cpi",
        "date_from": ("year", "month"),
        "year_default": 2023,
    },
    "data_budget_topline_net": {
        "value_col": "amount",
        "deflator": "cpi",
        "date_from": ("year", "month"),
        "year_default": 2023,
    },
    "data_budget_margin": {
        "value_col": "amount",
        "deflator": "cpi",
        "date_from": ("year", "month"),
        "year_default": 2023,
    },
    # data_budget_pl in DB is account hierarchy (no monthly amounts); skip in ADJUSTMENTS.
    "data_bilan": {
        "value_col": "amount",
        "deflator": "ppi",
        "date_col": "date",
        "wide_amount": True,
    },
    "clients": {
        "value_cols": None,  # all numeric except metadata → see apply.py
        "deflator": "cpi",
        "as_of_date": "2023-08-31",
    },
    "suppliers": {
        "value_cols": None,
        "deflator": "cpi",
        "as_of_date": "2023-08-31",
    },
    "hr_synthesis": {
        "value_col": "value",
        "deflator": "cpi",
        "date_col": "date",
        "wide_amount": True,
    },
}
