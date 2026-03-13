"""
Generate sample Excel files in data/raw/ for testing the ETL pipeline.

Run once:  python create_sample_data.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from config.settings import DATA_RAW_DIR


def create_sample_financial_data(data_raw_directory: Path) -> None:
    """
    Generate sample financial data and save it to an Excel file.

    The data includes revenue, expenses, net income, and exchange rates.
    Some realistic gaps are added to the data.

    Args:
        data_raw_directory (Path): The directory where the sample data will be saved.
    """
    np.random.seed(42)
    # Generate a range of dates from 2015-01-01 to 2025-12-01, with one date per month
    dates = pd.date_range("2015-01-01", periods=120, freq="MS")
    # Create a DataFrame with the financial data
    financial_data = pd.DataFrame(
        {
            "Date": dates,
            "Revenue": np.random.uniform(50_000, 200_000, len(dates)).round(2),
            "Expenses": np.random.uniform(30_000, 150_000, len(dates)).round(2),
            "Net Income": None,  # will be cleaned in transform
            "Exchange Rate (USD/EUR)": np.random.uniform(0.85, 0.95, len(dates)).round(
                4
            ),
        }
    )
    # Add some realistic gaps to the data
    # Set revenue to NaN for certain dates
    financial_data.loc[[5, 18, 42], "Revenue"] = np.nan
    # Set expenses to NaN for a range of dates
    financial_data.loc[100:105, "Expenses"] = np.nan

    # Save the financial data to an Excel file
    file_path = data_raw_directory / "financial_data.xlsx"
    financial_data.to_excel(file_path, index=False, engine="openpyxl")
    print(f"Created {file_path}  ({len(financial_data)} rows)")


def create_sample_economic_indicators(data_raw_directory: Path) -> None:
    """
    Generate sample economic indicators and save them to an Excel file.

    The data includes consumer price index, inflation rate, GDP deflator, and PPP conversion factor.

    Args:
        data_raw_directory (Path): The directory where the sample data will be saved.
    """
    # Generate a list of years from 2015 to 2024
    years = list(range(2015, 2025))
    # Create a DataFrame with the economic indicators
    economic_indicators = pd.DataFrame(
        {
            "Date": pd.to_datetime([f"{y}-01-01" for y in years]),
            "CPI": np.linspace(100, 130, len(years)).round(2),  # consumer price index
            "Inflation Rate (%)": np.random.uniform(1.0, 4.5, len(years)).round(2),
            "GDP Deflator": np.linspace(100, 125, len(years)).round(2),
            "PPP Conversion Factor": np.random.uniform(0.9, 1.1, len(years)).round(4),
        }
    )

    # Save the economic indicators to an Excel file
    file_path = data_raw_directory / "economic_indicators.xlsx"
    economic_indicators.to_excel(file_path, index=False, engine="openpyxl")
    print(f"Created {file_path}  ({len(economic_indicators)} rows)")


def main() -> None:
    """
    Generate sample data for testing the ETL pipeline.
    """
    # Get the project root directory
    project_root = Path(__file__).resolve().parent
    # Add the project root directory to the system path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Create the data/raw directory if it does not exist
    data_raw_directory = Path("data/raw")
    data_raw_directory.mkdir(parents=True, exist_ok=True)
    # Generate the sample financial data
    create_sample_financial_data(data_raw_directory)
    # Generate the sample economic indicators
    create_sample_economic_indicators(data_raw_directory)


if __name__ == "__main__":
    main()
