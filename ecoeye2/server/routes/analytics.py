"""Time series for visualization (nominal vs real / before-after)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ecoeye2.server.dbutil import connect, list_user_tables, quote_ident, table_columns
router = APIRouter()


def _find_real_amount_column(conn, real_table: str) -> str | None:
    cols = table_columns(conn, real_table)
    for c in sorted(cols):
        if c.startswith("amount_real_"):
            return c
    return None


@router.get("/analytics/series")
def analytics_series(
    table: str = Query("data_reel", description="Base (nominal) SQLite table name"),
    mode: str = Query("both", pattern="^(nominal|real|both)$"),
    group_by: str = Query("month", pattern="^(month|partner|channel)$"),
):
    conn = connect()
    try:
        names = set(list_user_tables(conn))
        if table not in names:
            raise HTTPException(404, f"Unknown table {table}")
        tq = quote_ident(table)
        cols = table_columns(conn, table)
        if "date" not in cols or "amount" not in cols:
            raise HTTPException(
                400,
                "This endpoint expects columns 'date' and 'amount' on the base table.",
            )

        real_name = f"{table}_real"
        real_col: str | None = None
        if real_name in names:
            real_col = _find_real_amount_column(conn, real_name)

        if mode in ("real", "both") and not real_col:
            raise HTTPException(
                400,
                f"No {real_name} with amount_real_* column; run econ apply or use mode=nominal.",
            )

        rtq = quote_ident(real_name) if real_col else None
        rcq = quote_ident(real_col) if real_col else None

        if group_by == "month":
            gb_m = "strftime('%Y-%m', m.date)"
            gb_r = "strftime('%Y-%m', r.date)"
            gb_label = "period"
        elif group_by == "partner":
            gb_m = "m.partner"
            gb_r = "r.partner"
            gb_label = "partner"
        else:
            gb_m = "m.channel"
            gb_r = "r.channel"
            gb_label = "channel"

        if mode == "nominal":
            sql = f"""
                SELECT {gb_m} AS grp, SUM(m.amount) AS nominal
                FROM {tq} m
                WHERE m.date IS NOT NULL
                GROUP BY {gb_m}
                ORDER BY {gb_m}
            """
            cur = conn.execute(sql)
            points = [{"period": r["grp"], "nominal": r["nominal"], "real": None} for r in cur]
            return {"table": table, "mode": mode, "group_by": group_by, "points": points}

        assert rtq and rcq

        if mode == "real":
            sql = f"""
                SELECT {gb_r} AS grp, SUM(r.{rcq}) AS real_value
                FROM {rtq} r
                WHERE r.date IS NOT NULL
                GROUP BY {gb_r}
                ORDER BY {gb_r}
            """
            cur = conn.execute(sql)
            points = [{"period": r["grp"], "nominal": None, "real": r["real_value"]} for r in cur]
            return {"table": table, "mode": mode, "group_by": group_by, "points": points}

        sql = f"""
            SELECT {gb_m} AS grp,
                   SUM(m.amount) AS nominal,
                   SUM(r.{rcq}) AS real_value
            FROM {tq} m
            LEFT JOIN {rtq} r ON date(m.date) = date(r.date)
                AND m.partner = r.partner AND m.channel = r.channel
                AND COALESCE(m.brand, '') = COALESCE(r.brand, '')
                AND COALESCE(m.machine, '') = COALESCE(r.machine, '')
            WHERE m.date IS NOT NULL
            GROUP BY {gb_m}
            ORDER BY {gb_m}
        """
        cur = conn.execute(sql)
        points = [
            {"period": r["grp"], "nominal": r["nominal"], "real": r["real_value"]}
            for r in cur.fetchall()
        ]
        return {"table": table, "mode": mode, "group_by": group_by, "points": points}
    finally:
        conn.close()
