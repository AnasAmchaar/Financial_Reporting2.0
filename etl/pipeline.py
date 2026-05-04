"""
Callable ETL pipeline for CLI (run_etl.py) and EcoEye2 API.

Returns structured results instead of only logging.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import DATA_RAW_DIR, DB_PATH, SOURCES
from etl.extract import extract_all, extract_sheet
from etl.transform import transform, transform_all
from etl.load import load_all, load_to_sqlite

logger = logging.getLogger(__name__)


@dataclass
class EtlTableResult:
    table: str
    ok: bool
    rows: int = 0
    error: str | None = None


@dataclass
class EtlRunResult:
    ok: bool
    tables: list[EtlTableResult] = field(default_factory=list)
    message: str | None = None


def find_table(table_name: str) -> tuple[Path, dict] | None:
    """Locate table_name in SOURCES -> (filepath, sheet_cfg) or None."""
    for filename, tables in SOURCES.items():
        if table_name in tables:
            return DATA_RAW_DIR / filename, tables[table_name]
    return None


def run_etl_single(
    table_name: str,
    *,
    raw_dir: Path | None = None,
    db_path: Path | None = None,
) -> EtlRunResult:
    """Run ETL for one logical table name."""
    raw_dir = raw_dir or DATA_RAW_DIR
    db_path = db_path or DB_PATH
    res = EtlTableResult(table=table_name, ok=False)
    found = find_table(table_name)
    if found is None:
        res.error = f"Unknown table {table_name!r}; not in SOURCES."
        return EtlRunResult(ok=False, tables=[res], message=res.error)
    filepath, cfg = found
    if not filepath.exists():
        res.error = f"Excel file not found: {filepath}"
        return EtlRunResult(ok=False, tables=[res], message=res.error)
    try:
        raw_df = extract_sheet(filepath, cfg)
        clean_df = transform(raw_df, cfg.get("transform_type", "generic"), cfg.get("transform_opts"))
        load_to_sqlite(clean_df, table_name=table_name, db_path=db_path)
        res.ok = True
        res.rows = len(clean_df)
    except Exception as e:
        logger.exception("ETL failed for %s", table_name)
        res.error = str(e)
        return EtlRunResult(ok=False, tables=[res], message=res.error)
    return EtlRunResult(ok=True, tables=[res])


def run_etl_all(
    *,
    raw_dir: Path | None = None,
    sources: dict | None = None,
    db_path: Path | None = None,
) -> EtlRunResult:
    """Run ETL for every configured table."""
    raw_dir = raw_dir or DATA_RAW_DIR
    db_path = db_path or DB_PATH
    src = sources if sources is not None else SOURCES
    raw_frames = extract_all(raw_dir=raw_dir, sources=src)
    if not raw_frames:
        return EtlRunResult(
            ok=False,
            message="No data extracted. Check Excel files exist under data/raw and SOURCES.",
        )
    results: list[EtlTableResult] = []
    try:
        clean_frames = transform_all(raw_frames)
        load_all(clean_frames, to_sqlite=True, db_path=db_path)
        for name, df in clean_frames.items():
            results.append(EtlTableResult(table=name, ok=True, rows=len(df)))
    except Exception as e:
        logger.exception("ETL batch failed")
        return EtlRunResult(ok=False, tables=results, message=str(e))
    return EtlRunResult(ok=True, tables=results)


def run_etl_for_file(
    filename: str,
    *,
    table_names: list[str] | None = None,
    raw_dir: Path | None = None,
    db_path: Path | None = None,
) -> EtlRunResult:
    """
    Run ETL for one workbook filename (key in SOURCES).
    If table_names is None, all tables for that file are processed.
    """
    raw_dir = raw_dir or DATA_RAW_DIR
    db_path = db_path or DB_PATH
    if filename not in SOURCES:
        return EtlRunResult(
            ok=False,
            message=f"Filename {filename!r} is not registered in SOURCES.",
        )
    file_tables = SOURCES[filename]
    names = list(file_tables.keys()) if not table_names else [t for t in table_names if t in file_tables]
    if not names:
        return EtlRunResult(ok=False, message="No valid table names for this file.")
    subset = {filename: {t: file_tables[t] for t in names}}
    raw_frames = extract_all(raw_dir=raw_dir, sources=subset)
    if not raw_frames:
        return EtlRunResult(
            ok=False,
            message=f"No sheets extracted for {filename}. Is the file present at {raw_dir / filename}?",
        )
    results: list[EtlTableResult] = []
    try:
        clean_frames = transform_all(raw_frames)
        load_all(clean_frames, to_sqlite=True, db_path=db_path)
        for name, df in clean_frames.items():
            results.append(EtlTableResult(table=name, ok=True, rows=len(df)))
    except Exception as e:
        logger.exception("ETL file batch failed")
        return EtlRunResult(ok=False, tables=results, message=str(e))
    return EtlRunResult(ok=True, tables=results)
