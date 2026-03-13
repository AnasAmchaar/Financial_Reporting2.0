# Financial Reporting ETL Pipeline
=====================================

## Overview
------------

This is a general-purpose ETL (Extract, Transform, Load) pipeline designed to ingest financial Excel workbooks, transform the data, and load it into a SQLite database. The pipeline is highly customizable and supports various financial data formats.

## Project Roadmap
-----------------

### Current Phase: ETL Pipeline

### Upcoming Phases:

1. **Economic Transformation**: Inflation, PPP adjustments, and other economic indicators.
2. **Interactive Dashboard**: A user-friendly interface for data exploration and visualization.
3. **AI-powered Analysis**: Leveraging machine learning to provide insights and predictions.

## Quick Start
--------------

### Prerequisites

* Install required packages by running `pip install -r requirements.txt`

### Steps

#### Step 1: Prepare Data

* Place your Excel file(s) in `data/raw/`
* Edit `config/settings.py` to describe the sheets in `SOURCES`

#### Step 2: Run ETL Pipeline

* `python run_etl.py` to process all configured sources
* `python run_etl.py data_reel` to process a single table

## Project Structure
---------------------

```markdown
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

## Adding a New Data Source
---------------------------

### Steps

1. **Prepare Data**

    * Place the Excel file in `data/raw/`

2. **Configure Settings**

    * Open `config/settings.py` and add an entry to the `SOURCES` dictionary:

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

3. **Run ETL Pipeline**

    * `python run_etl.py`

## Available Transform Types
-----------------------------

### Overview

The ETL pipeline supports various financial data formats through the following transform types:

### Transform Types

| Type            | Description                                                  |
|-----------------|--------------------------------------------------------------|
| `transactional` | Row-per-transaction data (partner, month, amount)             |
| `budget`        | Budget/forecast tables with a label column                   |
| `balance_sheet` | ID columns + monthly date columns → melted long format        |
| `mapping`       | Account code → hierarchy levels                              |
| `aging`         | Entity name + aging buckets (clients/suppliers)              |
| `time_series`   | ID columns + monthly date columns → melted long format        |
| `generic`       | Clean names, drop empties, deduplicate only                  |

### Optional Transform Options

Each type accepts optional `transform_opts` passed as keyword arguments. For example:

```python
"transform_opts": {"label": "topline_net"}   # for budget type
"transform_opts": {"entity_type": "client"}  # for aging type
```

## Tech Stack
--------------

### Overview

The ETL pipeline is built using the following technologies:

### Technologies

* **Python 3.12**: The primary programming language used for the ETL pipeline.
* **pandas**: A powerful data analysis library for data manipulation and analysis.
* **openpyxl**: A library for reading and writing Excel files.
* **SQLite**: A lightweight embedded database for storing and querying data.
* **Parquet**: An optional columnar storage format for efficient data snapshots.

## Contributing
--------------

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute to this project.

## License
---------

This project is licensed under the [MIT License](LICENSE.md).

## Acknowledgments
-----------------

This project was inspired by various open-source ETL pipelines and financial data analysis libraries.