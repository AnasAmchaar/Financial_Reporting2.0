"""List tables, paginated rows, batch PATCH for raw tables."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ecoeye2.server.dbutil import connect, is_editable_table, list_user_tables, quote_ident, table_columns
router = APIRouter()


class RowUpdate(BaseModel):
    rowid: int
    column: str
    value: str | int | float | None = None


class PatchBody(BaseModel):
    updates: list[RowUpdate] = Field(default_factory=list)


@router.get("/tables")
def list_tables():
    conn = connect()
    try:
        names = list_user_tables(conn)
        s = set(names)
        out = []
        for n in names:
            out.append(
                {
                    "name": n,
                    "editable": is_editable_table(n),
                    "has_real": f"{n}_real" in s,
                }
            )
        return {"tables": out}
    finally:
        conn.close()


@router.get("/tables/{table}/rows")
def get_rows(
    table: str,
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(None, description="column name to sort by (optional)"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    conn = connect()
    try:
        names = set(list_user_tables(conn))
        if table not in names:
            raise HTTPException(404, "Unknown table")
        cols = table_columns(conn, table)
        if sort and sort not in cols:
            raise HTTPException(400, f"Invalid sort column: {sort}")
        tq = quote_ident(table)
        order_sql = ""
        if sort:
            sq = quote_ident(sort)
            order_sql = f" ORDER BY {sq} {order.upper()}"
        cur = conn.execute(f"SELECT rowid AS _rowid, * FROM {tq}{order_sql} LIMIT ? OFFSET ?", (limit, offset))
        rows = [dict(r) for r in cur.fetchall()]
        total = conn.execute(f"SELECT COUNT(*) FROM {tq}").fetchone()[0]
        return {"table": table, "rows": rows, "total": total, "limit": limit, "offset": offset}
    finally:
        conn.close()


@router.patch("/tables/{table}/rows")
def patch_rows(table: str, body: PatchBody):
    if not is_editable_table(table):
        raise HTTPException(403, "This table is read-only (derived or system).")
    if not body.updates:
        raise HTTPException(400, "No updates")
    conn = connect()
    try:
        cols = table_columns(conn, table)
        tq = quote_ident(table)
        conn.execute("BEGIN")
        try:
            for u in body.updates:
                if u.column not in cols or u.column == "_rowid":
                    raise HTTPException(400, f"Invalid column: {u.column}")
                cq = quote_ident(u.column)
                conn.execute(f"UPDATE {tq} SET {cq} = ? WHERE rowid = ?", (u.value, u.rowid))
            conn.execute("COMMIT")
        except HTTPException:
            conn.execute("ROLLBACK")
            raise
        except Exception as e:
            conn.execute("ROLLBACK")
            raise HTTPException(500, str(e)) from e
        return {"ok": True, "updated": len(body.updates)}
    finally:
        conn.close()
