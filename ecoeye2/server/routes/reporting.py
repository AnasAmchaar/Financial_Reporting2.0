"""Reporting-oriented aggregates (nominal vs real, dimension rankings)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from config.econ_settings import WACC_DEMO_CONFIG
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

    Uses independent queries against the base and ``_real`` tables to avoid
    join fan-out from duplicate keys.

    ``purchasing_power_delta`` = sum_real − sum_nominal:
    - Positive → past nominal flows represented MORE real purchasing power
      than face value (data is from before the base period).
    - Negative → inflation has eroded purchasing power since the base period
      (data extends beyond the base period).
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
        purchasing_power_delta: float | None = None
        note: str | None = None

        if real_col:
            # Independent query — no join, no fan-out
            rtq = quote_ident(real_name)
            rcq = quote_ident(real_col)
            cur = conn.execute(
                f"""
                SELECT SUM({rcq}) AS sum_real
                FROM {rtq}
                WHERE date IS NOT NULL
                """
            )
            r2 = cur.fetchone()
            sum_real = float(r2["sum_real"] or 0) if r2 and r2["sum_real"] is not None else 0.0
            purchasing_power_delta = sum_real - sum_nominal
        else:
            note = f"No {real_name} with amount_real_* column; run econ apply for real totals."

        return {
            "table": table,
            "period_min": str(period_min) if period_min is not None else None,
            "period_max": str(period_max) if period_max is not None else None,
            "sum_nominal": sum_nominal,
            "sum_real": sum_real,
            "purchasing_power_delta": purchasing_power_delta,
            "methodology": (
                "Real values are computed using D(t) = CPI_base / CPI_t. "
                "For dates before the base period, real > nominal because past MAD "
                "had greater purchasing power. purchasing_power_delta = sum_real − sum_nominal: "
                "positive means past flows were worth more in constant prices."
            )
            if purchasing_power_delta is not None
            else None,
            # Keep legacy key for frontend compatibility, but with correct sign
            "inflation_impact": -purchasing_power_delta if purchasing_power_delta is not None else None,
            "inflation_impact_note": (
                "Estimated cumulative inflation impact (negative of purchasing_power_delta). "
                "A negative value means inflation has not eroded value vs. the base period."
            )
            if purchasing_power_delta is not None
            else None,
            "note": note,
        }
    finally:
        conn.close()


@router.get("/reporting/eva-demo")
def reporting_eva_demo():
    """
    Computes Economic Value Added (EVA) for demo purposes.

    EVA = NOPAT − (Invested Capital × WACC)

    WACC = We × Ce + Wd × Cd × (1 − T)
    where We = 1/(1+D/E), Wd = (D/E)/(1+D/E).

    NOPAT is proxied as (net revenue) × (1 − tax_rate).
    Invested Capital is proxied from ``data_bilan_real``.
    """
    de = WACC_DEMO_CONFIG["debt_to_equity"]
    we = 1.0 / (1.0 + de)
    wd = de / (1.0 + de)
    ce = WACC_DEMO_CONFIG["cost_of_equity"]
    cd = WACC_DEMO_CONFIG["cost_of_debt"]
    tax = WACC_DEMO_CONFIG["tax_rate"]

    wacc = we * ce + wd * cd * (1.0 - tax)

    conn = connect()
    try:
        # Verify data_bilan_real exists
        cur_t = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_bilan_real'")
        if not cur_t.fetchone():
            return {"demo": "Economic Value Added", "wacc": wacc, "points": []}

        sql = """
            SELECT
                strftime('%Y-%m', r.date) AS period,
                SUM(r.amount) AS net_revenue,
                (SELECT SUM(b.amount) FROM data_bilan_real b WHERE strftime('%Y-%m', b.date) = strftime('%Y-%m', r.date)) AS invested_capital
            FROM data_reel r
            WHERE r.date IS NOT NULL
            GROUP BY period
            ORDER BY period
        """
        cur = conn.execute(sql)
        rows = cur.fetchall()

        points = []
        for r in rows:
            net_rev = float(r["net_revenue"] or 0)
            nopat = net_rev * (1.0 - tax)
            ic = float(r["invested_capital"] or 0)
            capital_charge = ic * (wacc / 12)  # Monthly charge
            eva = nopat - capital_charge
            points.append({
                "period": r["period"],
                "net_revenue": net_rev,
                "nopat": nopat,
                "invested_capital": ic,
                "wacc": round(wacc, 6),
                "capital_charge": capital_charge,
                "eva": eva,
            })

        return {
            "demo": "Economic Value Added",
            "wacc": round(wacc, 6),
            "wacc_components": {
                "We": round(we, 4),
                "Wd": round(wd, 4),
                "Ce": ce,
                "Cd": cd,
                "tax_rate": tax,
                "D_E": de,
            },
            "methodology": (
                f"WACC = We×Ce + Wd×Cd×(1−T) = {we:.4f}×{ce} + {wd:.4f}×{cd}×{1-tax:.2f} = {wacc:.4f} ({wacc*100:.2f}%). "
                f"NOPAT = net_revenue × (1−T). Capital charge = IC × WACC/12 (monthly)."
            ),
            "points": points,
        }
    finally:
        conn.close()


@router.get("/reporting/vpmf-demo")
def reporting_vpmf_demo(
    table: str = Query("data_reel"),
    group_by: str = Query("month", pattern="^(month|partner|channel)$")
):
    """
    Volume–Price–Mix–FX (VPMF) growth decomposition.

    Decomposes period-over-period nominal changes into:
    - Price effect: how much of the change is due to inflation
    - Volume effect: the residual real change

    Uses independent queries (no JOINs) to avoid fan-out.
    """
    conn = connect()
    try:
        real_name = f"{table}_real"
        real_col = _find_real_amount_column(conn, real_name) if real_name in set(list_user_tables(conn)) else None

        if not real_col:
            return {"demo": "VPMF Growth Decomposition", "points": []}

        rtq = quote_ident(real_name)
        rcq = quote_ident(real_col)

        if group_by == "month":
            gb = "strftime('%Y-%m', date)"
        elif group_by == "partner":
            gb = "partner"
        else:
            gb = "channel"

        # Query nominal from base table
        tq = quote_ident(table)
        nom_sql = f"""
            SELECT {gb} AS grp, SUM(amount) AS nominal
            FROM {tq}
            WHERE date IS NOT NULL
            GROUP BY grp
            ORDER BY grp
        """
        nom_rows = {r["grp"]: float(r["nominal"] or 0) for r in conn.execute(nom_sql)}

        # Query real from _real table
        real_sql = f"""
            SELECT {gb} AS grp, SUM({rcq}) AS real_value
            FROM {rtq}
            WHERE date IS NOT NULL
            GROUP BY grp
            ORDER BY grp
        """
        real_rows = {r["grp"]: float(r["real_value"] or 0) for r in conn.execute(real_sql)}

        # Combine and compute decomposition
        all_periods = sorted(set(nom_rows.keys()) | set(real_rows.keys()))
        points = []
        prev_nominal = None
        prev_real = None

        for period in all_periods:
            nominal = nom_rows.get(period, 0.0)
            real_val = real_rows.get(period, 0.0)

            if prev_nominal is not None:
                delta = nominal - prev_nominal
                # Price effect = change in nominal minus change in real
                # (real strips out price changes, so the difference is the price component)
                delta_real = real_val - prev_real
                price_effect = delta - delta_real
                volume_effect = delta_real
            else:
                delta = 0.0
                price_effect = 0.0
                volume_effect = 0.0

            points.append({
                "period": period,
                "nominal": nominal,
                "real": real_val,
                "delta": delta,
                "price_effect": price_effect,
                "volume_effect": volume_effect,
            })

            prev_nominal = nominal
            prev_real = real_val

        return {
            "demo": "VPMF Growth Decomposition",
            "methodology": (
                "Price effect = Δnominal − Δreal (inflation-driven portion of the change). "
                "Volume effect = Δreal (real growth in constant prices)."
            ),
            "points": points,
        }
    finally:
        conn.close()


@router.get("/reporting/top-dimensions")
def reporting_top_dimensions(
    table: str = Query("data_reel"),
    dim: str = Query("partner", pattern="^(partner|channel)$"),
    limit: int = Query(8, ge=1, le=50),
):
    """Ranked nominal vs real totals per partner or channel (independent queries)."""
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

        # Independent queries to avoid join fan-out
        nom_sql = f"""
            SELECT {dmq} AS dim_value, SUM(amount) AS nominal
            FROM {tq}
            WHERE date IS NOT NULL
            GROUP BY {dmq}
            ORDER BY nominal DESC
            LIMIT ?
        """
        nom_map = {}
        for r in conn.execute(nom_sql, (limit,)):
            nom_map[r["dim_value"]] = float(r["nominal"] or 0)

        real_sql = f"""
            SELECT {dmq} AS dim_value, SUM({rcq}) AS real_value
            FROM {rtq}
            WHERE date IS NOT NULL AND {dmq} IN ({','.join('?' for _ in nom_map)})
            GROUP BY {dmq}
        """
        real_map = {}
        for r in conn.execute(real_sql, list(nom_map.keys())):
            real_map[r["dim_value"]] = float(r["real_value"] or 0)

        rows = []
        for dv, nominal in nom_map.items():
            rows.append({
                "dim": dim,
                "value": dv,
                "nominal": nominal,
                "real": real_map.get(dv),
            })

        return {"table": table, "dim": dim, "limit": limit, "rows": rows}
    finally:
        conn.close()
