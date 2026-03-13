"""
Quick verification of the SQLite database after ETL.

This script connects to a SQLite database, lists all tables, and verifies their row counts and column structures.
It also prints the first 5 rows of specified tables for sampling.
"""

import sqlite3
import pandas as pd

def connect_to_db(db_path: str) -> sqlite3.Connection:
    """
    Establish a connection to a SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    return sqlite3.connect(db_path)

def get_table_info(cur: sqlite3.Cursor) -> dict:
    """
    Retrieve information about all tables in the database.

    Args:
        cur (sqlite3.Cursor): A cursor object to execute SQL queries.

    Returns:
        dict: A dictionary with table names as keys and their respective row counts and column names as values.
    """
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cur.fetchall()
    table_info = {}
    for (t,) in tables:
        cur.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = cur.fetchone()[0]
        cur.execute(f"PRAGMA table_info([{t}])")
        cols = [row[1] for row in cur.fetchall()]
        table_info[t] = {"row_count": count, "column_names": cols}
    return table_info

def print_table_info(table_info: dict) -> None:
    """
    Print a summary of table information.

    Args:
        table_info (dict): A dictionary with table names as keys and their respective row counts and column names as values.
    """
    print("Tables in pfa.db:")
    print("-" * 60)
    for table, info in table_info.items():
        print(f"  {table:30s} {info['row_count']:>6} rows  cols: {info['column_names']}")

def print_table_samples(cur: sqlite3.Cursor, table_names: list) -> None:
    """
    Print the first 5 rows of specified tables.

    Args:
        cur (sqlite3.Cursor): A cursor object to execute SQL queries.
        table_names (list): A list of table names to sample.
    """
    for table in table_names:
        print(f"\n--- {table} (first 5 rows) ---")
        df = pd.read_sql(f"SELECT * FROM [{table}] LIMIT 5", cur)
        print(df.to_string())

def main() -> None:
    db_path = "db/pfa.db"
    conn = connect_to_db(db_path)
    cur = conn.cursor()
    table_info = get_table_info(cur)
    print_table_info(table_info)
    table_names = ["data_reel", "mapping", "clients", "data_budget_topline"]
    print_table_samples(cur, table_names)
    conn.close()

if __name__ == "__main__":
    main()