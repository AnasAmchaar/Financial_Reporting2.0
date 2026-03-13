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
    Establish a connection to the project SQLite database, creating the database directory if it doesn't exist.

    Returns:
        sqlite3.Connection: A connection to the SQLite database.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _save_parquet(df: pd.DataFrame, name: str, output_dir: os.PathLike) -> None:
    """
    Save a DataFrame as a Parquet file in the specified directory.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        name (str): The name of the Parquet file.
        output_dir (os.PathLike): The directory where the Parquet file will be saved.
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

    Args:
        df (pd.DataFrame): The DataFrame to write.
        table_name (str): The target table name.
        if_exists (str, optional): 'replace' (default), 'append', or 'fail'. Defaults to "replace".
    """
    conn = _get_sqlite_connection()
    try:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        logger.info("Loaded %d rows → SQLite table '%s'", len(df), table_name)
    finally:
        conn.close()


def save_to_parquet(
    df: pd.DataFrame, name: str, output_dir: os.PathLike = DATA_PROCESSED_DIR
) -> None:
    """
    Save a DataFrame as a Parquet file in the specified directory.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        name (str): The name of the Parquet file.
        output_dir (os.PathLike, optional): The directory where the Parquet file will be saved. Defaults to DATA_PROCESSED_DIR.
    """
    _save_parquet(df, name, output_dir)


def load_all(
    frames: dict[str, pd.DataFrame],
    to_sqlite: bool = True,
    to_parquet: bool = False,
) -> None:
    """
    Load every DataFrame in the dict.

    Args:
        frames (dict[str, pd.DataFrame]): A dictionary of DataFrames to load.
        to_sqlite (bool, optional): Whether to write to SQLite. Defaults to True.
        to_parquet (bool, optional): Whether to save Parquet snapshots. Defaults to False.
    """
    for key, df in frames.items():
        if to_sqlite:
            load_to_sqlite(df, table_name=key)
        if to_parquet:
            save_to_parquet(df, name=key)
