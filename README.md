# Financial Reporting ETL Pipeline

A general-purpose ETL pipeline that ingests **any** financial Excel workbook, transforms the data, and loads it into a SQLite database.

## Project Roadmap

1. **ETL Pipeline** (Ingest, clean, and normalise heterogeneous spreadsheets)
2. **Economic Adjustment Layer** (HCP, FRED, and World Bank inflation indexing & present-value discounting)
3. **EcoEye2 Web UI** (Interactive tables, custom charting, and ETL execution dashboard)
4. **AI-Powered Diagnostics & Forecasting** (Ensembled ML forecaster + Model Evaluation & Diagnostics dashboard)
5. **Interactive Chat Assistant** (RAG-supported chat over database records and economic indicators)

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
│   ├── settings.py           # Paths, logging, SOURCES configuration
│   ├── econ_settings.py      # Macro sources, BASE_PERIOD, ADJUSTMENTS
│   └── bam_policy_rates.csv  # Hand-maintained BAM key-rate steps (optional)
├── data/
│   ├── raw/                  # Drop Excel files here (.gitignored)
│   ├── processed/            # Optional Parquet output
│   └── econ/cache/           # Parquet cache for macro fetches (.gitignored)
├── db/
│   └── pfa.db                # SQLite database (.gitignored)
├── etl/
│   ├── extract.py            # Read Excel sheets → DataFrames
│   ├── transform.py          # Clean, normalise, reshape data
│   └── load.py               # Write to SQLite / Parquet
├── econ/
│   ├── fetcher.py            # Pull HCP / World Bank / FRED / BAM → econ_indicators
│   ├── apply.py              # Build parallel `*_real` tables in SQLite
│   ├── sources/              # Per-provider clients + HCP article scraper
│   └── adjusters/            # CPI/PPI deflator + time-value (PV) helpers
├── ecoeye2/
│   ├── server/               # FastAPI (EcoEye2 API + static SPA build)
│   └── web/                  # React + Vite frontend
├── logs/                     # ETL run logs (.gitignored)
├── run_etl.py                # Main ETL entry point
├── run_econ.py               # Macro fetch + apply real-value layer
├── run_ecoeye2.py            # Dev server: uvicorn EcoEye2 API
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

## Economic Adjustment Layer

After ETL has populated `db/pfa.db`, you can fetch macro indicators and create **parallel** `*_real` tables (raw tables are unchanged).

### Sources (automated)

| Priority | Provider | Series (examples) |
|----------|----------|-------------------|
| 1 | **HCP** (hcp.ma) | Latest IPC / IPPI article pages → Excel when linked |
| 2 | **FRED** | `MARCPIALLMINMEI` (monthly CPI), `CPALTT01MAM657N` (YoY) — requires `FRED_API_KEY` |
| 3 | **World Bank** | `FP.CPI.TOTL`, `FP.CPI.TOTL.ZG`; PPI chain falls back to `NY.GDP.DEFL.ZS` (annual GDP deflator) when IPPI is unavailable |
| 4 | **BAM** | Policy rate from [`config/bam_policy_rates.csv`](config/bam_policy_rates.csv) (hand-maintained schedule, expanded to monthly) |

Cache files are written under `data/econ/cache/`. Long-format history is stored in SQLite table **`econ_indicators`**.

### Configuration

- [`config/econ_settings.py`](config/econ_settings.py): `BASE_PERIOD` (deflation anchor, `YYYY-MM`), `INDICATOR_CHAIN` (per-indicator source order), `ADJUSTMENTS` (which table uses CPI vs PPI, dates, optional `year_default` for month-only budgets), `DISCOUNT` (annual rate + PV reference date).
- Copy [`.env.example`](.env.example) to `.env` and set `FRED_API_KEY` for monthly Morocco CPI when HCP Excel is not linked on article pages.

### Commands

```bash
pip install -r requirements.txt

python run_econ.py fetch          # refresh econ_indicators (+ Parquet cache)
python run_econ.py fetch --source worldbank   # only that provider's chain steps
python run_econ.py apply          # build data_reel_real, data_bilan_real, ...
python run_econ.py all            # fetch then apply
```

`apply` adds nominal deflators (`cpi_deflator` / `ppi_deflator`), `amount_real_<BASE>`, and `amount_pv_<refdate>` (time-value to `DISCOUNT["ref_date"]`) where a single `amount` column exists. Wide balance-sheet / HR sheets are auto-melted when columns look like `2023_01_01_00_00_00`. Client/supplier aging uses `as_of_date` from the config.

## EcoEye2 (web application)

**EcoEye2** is a FastAPI + React (TypeScript) UI for the full flow: upload workbooks, run ETL, edit raw SQLite rows, fetch/apply economic adjustments, and visualize **nominal vs real** (before/after) series.

### Run (development)

Terminal 1 – API (loads `.env` from project root for `FRED_API_KEY`, `ECOEYE2_*`):

```bash
pip install -r requirements.txt
python run_ecoeye2.py
# OpenAPI: http://127.0.0.1:8000/docs
```

Terminal 2 – SPA (Vite proxies `/api` to port 8000):

```bash
cd ecoeye2/web
npm install
npm run dev
# App: http://127.0.0.1:5173
```

### Run (single server, production build)

```bash
cd ecoeye2/web && npm run build
uvicorn ecoeye2.server.main:app --host 0.0.0.0 --port 8000
# UI + API: http://127.0.0.1:8000/
```

### Environment

| Variable | Purpose |
|----------|---------|
| `ECOEYE2_DB_PATH` | SQLite file (default `db/pfa.db`) |
| `ECOEYE2_RAW_DIR` | Upload directory (default `data/raw`) |
| `ECOEYE2_API_KEY` | If set, API requires header `X-Api-Key` on mutating routes |
| `VITE_ECOEYE2_API_KEY` | (frontend `.env`) same value for browser requests |
| `FRED_API_KEY` | Monthly Morocco CPI via FRED when HCP Excel is unavailable |

### Docker

```bash
docker compose build
docker compose up
```

Mount a volume with your `data/raw` Excel files and `pfa.db` (or let the app create an empty DB and run ETL from the UI after copying templates).

### Layout

- [`ecoeye2/server/`](ecoeye2/server/) – FastAPI app, REST under `/api/v1/`
- [`ecoeye2/web/`](ecoeye2/web/) – Vite React SPA; `npm run build` outputs to [`ecoeye2/server/static/`](ecoeye2/server/static/)

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

## 🤖 Machine Learning Forecasting & Evaluation

EcoEye2 features an advanced forecasting engine that predicts financial trends (nominal and real) up to $N$ months into the future.

### 1. Hybrid Ensemble Architecture
The forecasting engine employs an ensemble model combining two distinct predictive methodologies:
*   **Gradient Boosting Regressor (`scikit-learn`)**: Captures non-linear interactions, calendar features, and external macroeconomic indicators (CPI, PPI, policy rates).
*   **Holt-Winters Exponential Smoothing (`statsmodels`)**: Captures strong univariate trends and multi-period seasonality.
*   **Prediction Formulation**: A weighted average (**70% GBR / 30% HW**) outputs the final prediction.
*   **Confidence Intervals**: Quantile Gradient Boosting regression models fit to the 10th and 90th percentiles define the upper and lower bands of uncertainty.

### 2. Model Evaluation & Diagnostics Dashboard
To ensure transparency and trust in ML forecasts, the frontend includes a rich evaluation console:
*   **Performance Summary**: Key performance metrics ($R^2$, MAE, RMSE) computed via out-of-fold evaluations.
*   **Cross-Validation Folds**: Tracks metric stability across expanding window folds (`TimeSeriesSplit`).
*   **Validation Fit**: Plots actual historical values against out-of-fold predictions to evaluate model fit on unseen periods.
*   **Residuals Analysis**: Visualizes prediction error distributions over time to identify systematic biases.
*   **Drivers (Feature Importance)**: Identifies which macroeconomic factors or calendar features have the highest predictive weight.

---

## 🛡️ Resilient AI Assistant & Provider Registry

The floating **Chat Assistant** integrates Retrieval-Augmented Generation (RAG) over active database schemas, raw financial tables, and fetched macroeconomic indicators.

### 1. Multi-LLM Provider Switcher
Users can dynamically swap LLM providers at runtime:
*   **Google GenAI**: Configured with `gemini-2.5-flash` as primary.
*   **Groq**: Configured with `llama-3.3-70b-versatile` for high-throughput alternative execution.

### 2. Automatic Failover & High Availability
To bypass rate limits or high-demand errors (e.g. `503 Service Unavailable`), the Google GenAI provider implements a robust **Fallback Model Registry**:
1. It attempts execution using the primary model `gemini-2.5-flash`.
2. On failure, it transparently retries in order: `gemini-2.0-flash` ➔ `gemini-1.5-flash` ➔ `gemini-2.5-pro` ➔ `gemini-1.5-pro`.
3. Only if all fallback models fail is the exception propagated back to the user.

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.12, FastAPI, Uvicorn, Pandas, Scikit-Learn, Statsmodels, SQLite, PyArrow
*   **Frontend**: React 19, Vite 8, TypeScript, TailwindCSS, Recharts, TanStack Table
*   **Containerisation**: Docker, Docker Compose
*   **LLM Clients**: Google GenAI SDK, Groq API Client
