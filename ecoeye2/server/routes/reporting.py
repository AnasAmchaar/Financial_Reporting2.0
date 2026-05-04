"""Reporting-oriented aggregates (nominal vs real, dimension rankings)."""

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


@router.get("/reporting/summary")
def reporting_summary(
    table: str = Query("data_reel", description="Base (nominal) SQLite table name"),
):
    """
    Period bounds and nominal vs real totals.

    `inflation_impact` = sum_nominal - sum_real: nominal activity minus the same
    flows valued at constant prices (after econ apply), not a literal CPI gap.
    """
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
                "Expected columns 'date' and 'amount' on the base table.",
            )

        cur = conn.execute(
            f"""
            SELECT MIN(date) AS period_min, MAX(date) AS period_max,
                   SUM(amount) AS sum_nominal
            FROM {tq}
            WHERE date IS NOT NULL
            """
        )
        row = cur.fetchone()
        period_min = row["period_min"] if row else None
        period_max = row["period_max"] if row else None
        sum_nominal = float(row["sum_nominal"] or 0) if row else 0.0

        real_name = f"{table}_real"
        real_col = _find_real_amount_column(conn, real_name) if real_name in names else None
        sum_real: float | None = None
        inflation_impact: float | None = None
        note: str | None = None

        if real_col:
            rtq = quote_ident(real_name)
            rcq = quote_ident(real_col)
            cur = conn.execute(
                f"""
                SELECT SUM(r.{rcq}) AS sum_real
                FROM {tq} m
                INNER JOIN {rtq} r
                  ON date(m.date) = date(r.date)
                 AND m.partner = r.partner AND m.channel = r.channel
                 AND COALESCE(m.brand, '') = COALESCE(r.brand, '')
                 AND COALESCE(m.machine, '') = COALESCE(r.machine, '')
                WHERE m.date IS NOT NULL
                """
            )
            r2 = cur.fetchone()
            sum_real = float(r2["sum_real"] or 0) if r2 and r2["sum_real"] is not None else 0.0
            inflation_impact = sum_nominal - sum_real
        else:
            note = f"No {real_name} with amount_real_* column; run econ apply for real totals."

        return {
            "table": table,
            "period_min": str(period_min) if period_min is not None else None,
            "period_max": str(period_max) if period_max is not None else None,
            "sum_nominal": sum_nominal,
            "sum_real": sum_real,
            "inflation_impact": inflation_impact,
            "inflation_impact_note": (
                "sum_nominal minus sum_real on matched rows: nominal vs constant-price activity."
                if inflation_impact is not None
                else None
            ),
            "note": note,
        }
    finally:
        conn.close()


@router.get("/reporting/top-dimensions")
def reporting_top_dimensions(
    table: str = Query("data_reel"),
    dim: str = Query("partner", pattern="^(partner|channel)$"),
    limit: int = Query(8, ge=1, le=50),
):
    """Ranked nominal vs real totals per partner or channel."""
    conn = connect()
    try:
        names = set(list_user_tables(conn))
        if table not in names:
            raise HTTPException(404, f"Unknown table {table}")
        tq = quote_ident(table)
        cols = table_columns(conn, table)
        if "date" not in cols or "amount" not in cols:
            raise HTTPException(400, "Expected 'date' and 'amount' on the base table.")
        if dim not in cols:
            raise HTTPException(400, f"Column '{dim}' not present on {table}.")

        real_name = f"{table}_real"
        real_col = _find_real_amount_column(conn, real_name) if real_name in names else None
        if not real_col:
            raise HTTPException(
                400,
                f"No {real_name} with amount_real_*; run econ apply first.",
            )

        rtq = quote_ident(real_name)
        rcq = quote_ident(real_col)
        dmq = quote_ident(dim)

        sql = f"""
            SELECT m.{dmq} AS dim_value,
                   SUM(m.amount) AS nominal,
                   SUM(r.{rcq}) AS real_value
            FROM {tq} m
            INNER JOIN {rtq} r
              ON date(m.date) = date(r.date)
             AND m.partner = r.partner AND m.channel = r.channel
             AND COALESCE(m.brand, '') = COALESCE(r.brand, '')
             AND COALESCE(m.machine, '') = COALESCE(r.machine, '')
            WHERE m.date IS NOT NULL
            GROUP BY m.{dmq}
            ORDER BY nominal DESC
            LIMIT ?
        """
        cur = conn.execute(sql, (limit,))
        rows = []
        for r in cur:
            rows.append(
                {
                    "dim": dim,
                    "value": r["dim_value"],
                    "nominal": float(r["nominal"] or 0),
                    "real": float(r["real_value"] or 0) if r["real_value"] is not None else None,
                }
            )
        return {"table": table, "dim": dim, "limit": limit, "rows": rows}
    finally:
        conn.close()
