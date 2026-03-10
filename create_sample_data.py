"""
Generate sample Excel files in data/raw/ for testing the ETL pipeline.
Run once:  python create_sample_data.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from config.settings import DATA_RAW_DIR

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Sample financial data ────────────────────────────────────────────────────
np.random.seed(42)
dates = pd.date_range("2015-01-01", periods=120, freq="MS")  # monthly
financial_df = pd.DataFrame({
    "Date": dates,
    "Revenue": np.random.uniform(50_000, 200_000, len(dates)).round(2),
    "Expenses": np.random.uniform(30_000, 150_000, len(dates)).round(2),
    "Net Income": None,  # will be cleaned in transform
    "Exchange Rate (USD/EUR)": np.random.uniform(0.85, 0.95, len(dates)).round(4),
})
# Add some realistic gaps
financial_df.loc[[5, 18, 42], "Revenue"] = np.nan
financial_df.loc[100:105, "Expenses"] = np.nan

path1 = DATA_RAW_DIR / "financial_data.xlsx"
financial_df.to_excel(path1, index=False, engine="openpyxl")
print(f"Created {path1}  ({len(financial_df)} rows)")

# ── Sample economic indicators ───────────────────────────────────────────────
years = list(range(2015, 2025))
indicators_df = pd.DataFrame({
    "Date": pd.to_datetime([f"{y}-01-01" for y in years]),
    "CPI": np.linspace(100, 130, len(years)).round(2),           # consumer price index
    "Inflation Rate (%)": np.random.uniform(1.0, 4.5, len(years)).round(2),
    "GDP Deflator": np.linspace(100, 125, len(years)).round(2),
    "PPP Conversion Factor": np.random.uniform(0.9, 1.1, len(years)).round(4),
})

path2 = DATA_RAW_DIR / "economic_indicators.xlsx"
indicators_df.to_excel(path2, index=False, engine="openpyxl")
print(f"Created {path2}  ({len(indicators_df)} rows)")
