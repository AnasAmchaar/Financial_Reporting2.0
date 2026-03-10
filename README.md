# Financial Reporting ETL Pipeline

A general-purpose ETL pipeline that ingests **any** financial Excel workbook, transforms the data, and loads it into a SQLite database.

## Project Roadmap

1. **ETL Pipeline** ← *current phase*
2. Economic Transformation (inflation, PPP adjustments)
3. Interactive Dashboard
4. AI-powered Analysis

## Quick Start

```bash
pip install -r requirements.txt

# 1. Drop your Excel file(s) into data/raw/
# 2. Edit config/settings.py → SOURCES to describe the sheets
# 3. Run:
python run_etl.py            # process all configured sources
python run_etl.py data_reel  # process a single table
```

## Project Structure

```
PFA/
├── config/
│   └── settings.py          # Paths, logging, SOURCES configuration
├── data/
│   ├── raw/                  # Drop Excel files here (.gitignored)
│   └── processed/            # Optional Parquet output
├── db/
│   └── pfa.db                # SQLite database (.gitignored)
├── etl/
│   ├── extract.py            # Read Excel sheets → DataFrames
│   ├── transform.py          # Clean, normalise, reshape data
│   └── load.py               # Write to SQLite / Parquet
├── logs/                     # ETL run logs (.gitignored)
├── run_etl.py                # Main entry point
├── verify_db.py              # Quick DB inspection helper
└── requirements.txt
```

## How to Add a New Data Source

1. Place the Excel file in `data/raw/`.
2. Open `config/settings.py` and add an entry to the `SOURCES` dict:

```python
SOURCES = {
    "my_report.xlsx": {
        "revenue": {
            "sheet_name": "Sheet1",
            "header_row": 0,       # 0-based row with column headers
            "usecols": "A:F",      # Excel column range (None = all)
            "transform_type": "transactional",
        },
    },
}
```

3. Run `python run_etl.py`.

## Available Transform Types

| Type            | Use case                                     |
|-----------------|----------------------------------------------|
| `transactional` | Row-per-transaction data (partner, month, amount) |
| `budget`        | Budget/forecast tables with a label column   |
| `balance_sheet` | ID columns + monthly date columns → melted long format |
| `mapping`       | Account code → hierarchy levels              |
| `aging`         | Entity name + aging buckets (clients/suppliers) |
| `time_series`   | ID columns + monthly date columns → melted long format |
| `generic`       | Clean names, drop empties, deduplicate only  |

Each type accepts optional `transform_opts` passed as keyword arguments. For example:

```python
"transform_opts": {"label": "topline_net"}   # for budget type
"transform_opts": {"entity_type": "client"}  # for aging type
```

## Tech Stack

- **Python 3.12** – pandas, openpyxl
- **SQLite** – lightweight embedded database
- **Parquet** – optional columnar snapshots
