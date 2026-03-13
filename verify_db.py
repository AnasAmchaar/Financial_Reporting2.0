"""
Quick verification of the SQLite database after ETL.

This script connects to a SQLite database, lists all tables, and verifies their row counts and column structures.
It also prints the first 5 rows of specified tables for sampling.
"""

import sqlite3
import pandas as pd


def establish_database_connection(db_path: str) -> sqlite3.Connection:
    """
    Establish a connection to a SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    return sqlite3.connect(db_path)


def retrieve_table_info(cur: sqlite3.Cursor) -> dict:
    """
    Retrieve information about all tables in the database.

    Args:
        cur (sqlite3.Cursor): A cursor object to execute SQL queries.

    Returns:
        dict: A dictionary with table names as keys and their respective row counts and column names as values.
    """
    # Get a list of all tables in the database
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cur.fetchall()
    table_info = {}
    for table_name in [t[0] for t in tables]:
        # Get the row count for each table
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]

        # Get the column names for each table
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cur.fetchall()]

        # Store the table information in a dictionary
        table_info[table_name] = {"row_count": count, "column_names": columns}
    return table_info


def print_table_summary(table_info: dict) -> None:
    """
    Print a summary of table information.

    Args:
        table_info (dict): A dictionary with table names as keys and their respective row counts and column names as values.
    """
    print("Tables in database:")
    print("-" * 60)
    for table_name, info in table_info.items():
        print(
            f"  {table_name:30s} {info['row_count']:>6} rows  cols: {info['column_names']}"
        )


def print_table_samples(cur: sqlite3.Cursor, table_names: list) -> None:
    """
    Print the first 5 rows of specified tables.

    Args:
        cur (sqlite3.Cursor): A cursor object to execute SQL queries.
        table_names (list): A list of table names to sample.
    """
    for table_name in table_names:
        print(f"\n--- {table_name} (first 5 rows) ---")
        # Read the first 5 rows from each table using pandas
        df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 5", cur)
        print(df.to_string())


def main() -> None:
    db_path = "db/pfa.db"
    conn = establish_database_connection(db_path)
    cur = conn.cursor()
    table_info = retrieve_table_info(cur)
    print_table_summary(table_info)
    table_names = ["data_reel", "mapping", "clients", "data_budget_topline"]
    print_table_samples(cur, table_names)
    conn.close()


if __name__ == "__main__":
    main()
