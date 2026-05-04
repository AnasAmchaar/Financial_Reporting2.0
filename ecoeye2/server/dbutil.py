"""SQLite helpers with identifier whitelisting."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from config.settings import DB_PATH

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_ident(name: str) -> str:
    if not _IDENT.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def list_user_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall()]


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    q = quote_ident(table)
    cur = conn.execute(f"PRAGMA table_info({q})")
    return {row[1] for row in cur.fetchall()}


def is_editable_table(name: str) -> bool:
    if not _IDENT.match(name):
        return False
    if name.endswith("_real") or name == "econ_indicators":
        return False
    return True
