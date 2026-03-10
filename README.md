# PFA – Financial Data Analysis Platform

A Python-based ETL pipeline that extracts financial data from Excel Business Review templates, transforms it into clean structured tables, and loads it into a SQLite database — ready for economic transformation and interactive visualization.

## Project Roadmap

| Step | Description | Status |
|------|-------------|--------|
| 1 | Environment Setup | ✅ Done |
| 2 | ETL Pipeline (Extract → Transform → Load) | ✅ Done |
| 3 | Economic Transformation (inflation, PPP, monetary adjustments) | 🔲 Planned |
| 4 | Interactive Visualization & Dashboard | 🔲 Planned |
| 5 | AI Integration (optional, advanced features) | 🔲 Planned |

## Project Structure

```
PFA/
├── config/
│   ├── __init__.py
│   └── settings.py          # Central configuration (paths, sheet mappings)
├── data/
│   ├── raw/                 # Source Excel files (input)
│   └── processed/           # Processed output files (Parquet, optional)
├── db/
│   └── pfa.db               # SQLite database (pipeline output)
├── etl/
│   ├── __init__.py
│   ├── extract.py           # Extract: reads Excel sheets into DataFrames
│   ├── transform.py         # Transform: cleans, normalizes, reshapes data
│   └── load.py              # Load: writes DataFrames to SQLite
├── logs/
│   └── etl.log              # Pipeline execution logs
├── run_etl.py               # Main entry point
├── verify_db.py             # Database verification script
├── requirements.txt         # Python dependencies
└── README.md
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Place your data

Put your Business Review Excel file in `data/raw/`. The pipeline is currently configured for:

```
data/raw/DISLOG_BR_Template 08-2023.xlsx
```

### 3. Run the ETL pipeline

```bash
# Process all configured sheets
python run_etl.py

# Process a single source
python run_etl.py data_reel
```

### 4. Verify the results

```bash
python verify_db.py
```

## ETL Pipeline Details

### Extract

Reads 11 configured regions from the DISLOG Business Review Excel workbook. Each region is defined in `config/settings.py` with its sheet name, header row, and column range.

### Transform

Each sheet has a dedicated transform function:

| Source | Transform | Description |
|--------|-----------|-------------|
| `data_reel` | Column normalization, date construction (month+year → date), type casting | Actual revenue/sales data |
| `data_budget_*` | Column mapping, budget type labeling, deduplication | Budget & forecast data |
| `data_bilan` | Monthly columns preserved with proper naming | Balance sheet |
| `mapping` | Account code standardization, hierarchy levels | Account classification (COGS/OPEX) |
| `clients` | Entity tagging, aging bucket cleanup | Client receivables aging |
| `suppliers` | Entity tagging, aging bucket cleanup | Supplier payables aging |
| `hr_synthesis` | Monthly metric extraction | HR headcount & payroll |

Common operations: empty row removal, duplicate elimination, numeric type coercion, string trimming.

### Load

Writes all cleaned DataFrames into SQLite tables at `db/pfa.db`.

## Database Schema

After running the pipeline, `db/pfa.db` contains:

| Table | Rows | Key Columns |
|-------|------|-------------|
| `data_reel` | 9,004 | partner, brand, channel, machine, month, year, amount, date |
| `data_budget_topline` | 985 | partner, channel, month, amount, budget_type |
| `data_budget_topline_net` | 985 | partner, channel, month, amount, budget_type |
| `data_budget_margin` | 192 | partner, month, amount, budget_type |
| `data_budget_pl` | 148 | account_code, n1, n2, n3, budget_type |
| `data_bilan` | 312 | classe, compte_principal, intitulé, monthly values |
| `mapping` | 182 | account_code, level_1, level_2, level_3, level_4 |
| `mapping_opex` | 53 | OPEX sub-categories |
| `clients` | 31 | name, aging buckets (0-15 to 90+), entity_type |
| `suppliers` | 31 | name, aging buckets, entity_type |
| `hr_synthesis` | 27 | HR metrics by month |

## Reading the Database

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("db/pfa.db")

# Read a table
df = pd.read_sql("SELECT * FROM data_reel", conn)

# Query with aggregation
result = pd.read_sql("""
    SELECT partner, SUM(amount) as total
    FROM data_reel
    WHERE year = 2023
    GROUP BY partner
    ORDER BY total DESC
""", conn)

conn.close()
```

## Configuration

All pipeline settings are in `config/settings.py`:

- **Sheet mappings**: which sheets to extract, header rows, column ranges
- **File paths**: raw data directory, database location, log directory
- **Transform settings**: row cleanup behavior

To add a new sheet, add an entry to `SHEET_CONFIG` in `settings.py` and (optionally) a transform function in `etl/transform.py`.

## Tech Stack

- **Python 3.12**
- **pandas** – data manipulation
- **openpyxl** – Excel file reading
- **SQLite** – lightweight database storage
