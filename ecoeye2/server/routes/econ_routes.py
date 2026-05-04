"""Expose econ_indicators for the Adjustments UI."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ecoeye2.server.dbutil import connect, list_user_tables, quote_ident

router = APIRouter()

@router.get("/econ/indicators")
def get_indicators(
    limit: int = Query(500, ge=1, le=20000),
    offset: int = Query(0, ge=0),
    indicator_code: str | None = None,
):
    conn = connect()
    try:
        if "econ_indicators" not in list_user_tables(conn):
            return {"rows": [], "total": 0}
        tq = quote_ident("econ_indicators")
        where = ""
        params: list = []
        if indicator_code:
            where = " WHERE indicator_code = ?"
            params.append(indicator_code)
        cur = conn.execute(
            f"SELECT * FROM {tq}{where} ORDER BY date DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        rows = [dict(r) for r in cur.fetchall()]
        total = conn.execute(f"SELECT COUNT(*) FROM {tq}{where}", params).fetchone()[0]
        return {"rows": rows, "total": total, "limit": limit, "offset": offset}
    finally:
        conn.close()


