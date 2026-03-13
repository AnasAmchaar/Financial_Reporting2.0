"""
LOAD – Write transformed DataFrames into SQLite and (optionally) Parquet.
"""

import logging
import sqlite3
import os

import pandas as pd

from config.settings import DATA_PROCESSED_DIR, DB_PATH

logger = logging.getLogger(__name__)


def _get_sqlite_connection() -> sqlite3.Connection:
    """
    Return a connection to the project SQLite database, creating the directory if it doesn't exist.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _save_parquet(df: pd.DataFrame, name: str, output_dir: os.PathLike) -> None:
    """
    Save a DataFrame as a Parquet file in the specified directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.parquet"
    df.to_parquet(path, index=False)
    logger.info("Saved %d rows → %s", len(df), path)


def load_to_sqlite(
    df: pd.DataFrame,
    table_name: str,
    if_exists: str = "replace",
) -> None:
    """
    Write a DataFrame to a SQLite table.

    Parameters
    ----------
    df : DataFrame to write.
    table_name : Target table name.
    if_exists : 'replace' (default), 'append', or 'fail'.
    """
    conn = _get_sqlite_connection()
    try:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        logger.info("Loaded %d rows → SQLite table '%s'", len(df), table_name)
    finally:
        conn.close()


def load_to_parquet(df: pd.DataFrame, name: str) -> None:
    """Save a DataFrame as a Parquet file in data/processed/. By default, this is equivalent to calling `load_all` with `to_parquet=True`."""
    _save_parquet(df, name, DATA_PROCESSED_DIR)


def load_all(
    frames: dict[str, pd.DataFrame],
    to_sqlite: bool = True,
    to_parquet: bool = False,
) -> None:
    """
    Load every DataFrame in the dict.
    By default writes to SQLite; optionally also saves Parquet snapshots.
    """
    for key, df in frames.items():
        if to_sqlite:
            load_to_sqlite(df, table_name=key)
        if to_parquet:
            _save_parquet(df, name=key, output_dir=DATA_PROCESSED_DIR)