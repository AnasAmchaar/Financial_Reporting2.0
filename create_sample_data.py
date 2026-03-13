"""
Generate sample Excel files in data/raw/ for testing the ETL pipeline.

Run once:  python create_sample_data.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from config.settings import DATA_RAW_DIR

def create_sample_financial_data(data_raw_dir: Path) -> None:
    """
    Generate sample financial data and save it to an Excel file.

    The data includes revenue, expenses, net income, and exchange rates.
    Some realistic gaps are added to the data.
    """
    np.random.seed(42)
    dates = pd.date_range("2015-01-01", periods=120, freq="MS")  # monthly
    financial_df = pd.DataFrame(
        {
            "Date": dates,
            "Revenue": np.random.uniform(50_000, 200_000, len(dates)).round(2),
            "Expenses": np.random.uniform(30_000, 150_000, len(dates)).round(2),
            "Net Income": None,  # will be cleaned in transform
            "Exchange Rate (USD/EUR)": np.random.uniform(0.85, 0.95, len(dates)).round(4),
        }
    )
    # Add some realistic gaps
    financial_df.loc[[5, 18, 42], "Revenue"] = np.nan
    financial_df.loc[100:105, "Expenses"] = np.nan

    path = data_raw_dir / "financial_data.xlsx"
    financial_df.to_excel(path, index=False, engine="openpyxl")
    print(f"Created {path}  ({len(financial_df)} rows)")


def create_sample_economic_indicators(data_raw_dir: Path) -> None:
    """
    Generate sample economic indicators and save them to an Excel file.

    The data includes consumer price index, inflation rate, GDP deflator, and PPP conversion factor.
    """
    years = list(range(2015, 2025))
    indicators_df = pd.DataFrame(
        {
            "Date": pd.to_datetime([f"{y}-01-01" for y in years]),
            "CPI": np.linspace(100, 130, len(years)).round(2),  # consumer price index
            "Inflation Rate (%)": np.random.uniform(1.0, 4.5, len(years)).round(2),
            "GDP Deflator": np.linspace(100, 125, len(years)).round(2),
            "PPP Conversion Factor": np.random.uniform(0.9, 1.1, len(years)).round(4),
        }
    )

    path = data_raw_dir / "economic_indicators.xlsx"
    indicators_df.to_excel(path, index=False, engine="openpyxl")
    print(f"Created {path}  ({len(indicators_df)} rows)")


def main() -> None:
    """
    Generate sample data for testing the ETL pipeline.
    """
    PROJECT_ROOT = Path(__file__).resolve().parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    create_sample_financial_data(DATA_RAW_DIR)
    create_sample_economic_indicators(DATA_RAW_DIR)


if __name__ == "__main__":
    main()
```

This improved code includes:

*   Concise and helpful comments
*   Improved docstrings for functions
*   Improved variable and function names for better readability
*   Improved structure and organization
*   Preservation of all existing functionality and external behavior
*   Adherence to PEP 8 and Python best practices