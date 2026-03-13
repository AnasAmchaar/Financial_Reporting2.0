"""Quick verification of the SQLite database after ETL."""

import sqlite3
import pandas as pd

conn = sqlite3.connect("db/pfa.db")
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print("Tables in pfa.db:")
print("-" * 60)
for (t,) in tables:
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    count = cur.fetchone()[0]
    cur.execute(f"PRAGMA table_info([{t}])")
    cols = [row[1] for row in cur.fetchall()]
    print(f"  {t:30s} {count:>6} rows  cols: {cols}")

# Samples
for table in ["data_reel", "mapping", "clients", "data_budget_topline"]:
    print(f"\n--- {table} (first 5 rows) ---")
    df = pd.read_sql(f"SELECT * FROM [{table}] LIMIT 5", conn)
    print(df.to_string())

conn.close()
