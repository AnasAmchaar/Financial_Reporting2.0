"""Outlier detection and management routes."""

from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ecoeye2.server.dbutil import connect, is_editable_table, list_user_tables, quote_ident, table_columns

router = APIRouter()


class DetectRequest(BaseModel):
    table: str
    column: str = "amount"
    method: Literal["iqr", "zscore"] = "iqr"
    sensitivity: float = Field(1.5, ge=0.5, le=5.0, description="IQR multiplier or Z-score threshold")


class ActionRequest(BaseModel):
    table: str
    column: str
    rowids: list[int]
    action: Literal["drop", "replace_median", "replace_mean", "replace_custom"]
    custom_value: float | None = None


@router.post("/outliers/detect")
def detect_outliers(req: DetectRequest):
    conn = connect()
    try:
        names = set(list_user_tables(conn))
        if req.table not in names:
            raise HTTPException(404, f"Unknown table: {req.table}")

        cols = table_columns(conn, req.table)
        if req.column not in cols:
            raise HTTPException(400, f"Column '{req.column}' not found in table '{req.table}'")

        tq = quote_ident(req.table)
        cq = quote_ident(req.column)

        # Fetch all numeric values with rowids
        cur = conn.execute(
            f"SELECT rowid, {cq} FROM {tq} WHERE {cq} IS NOT NULL AND typeof({cq}) IN ('integer', 'real')"
        )
        raw_rows = cur.fetchall()

        if len(raw_rows) < 4:
            return {
                "table": req.table,
                "column": req.column,
                "method": req.method,
                "stats": {},
                "outliers": [],
                "total_rows": len(raw_rows),
                "outlier_count": 0,
                "message": "Not enough numeric data points (need at least 4).",
            }

        values = [float(r[1]) for r in raw_rows]
        rowids = [int(r[0]) for r in raw_rows]

        # Stats
        n = len(values)
        mean_val = sum(values) / n
        sorted_vals = sorted(values)
        median_val = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        variance = sum((v - mean_val) ** 2 for v in values) / n
        std_val = math.sqrt(variance) if variance > 0 else 0.0

        # Quartiles
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1

        outlier_indices: list[int] = []

        if req.method == "iqr":
            lower = q1 - req.sensitivity * iqr
            upper = q3 + req.sensitivity * iqr
            for i, v in enumerate(values):
                if v < lower or v > upper:
                    outlier_indices.append(i)
        else:  # zscore
            threshold = req.sensitivity
            for i, v in enumerate(values):
                z = abs((v - mean_val) / std_val) if std_val > 0 else 0
                if z > threshold:
                    outlier_indices.append(i)

        # Build preview data for outlier rows
        # Fetch full row data for the outlier rowids
        outlier_rowids = [rowids[i] for i in outlier_indices]
        outliers_out = []

        if outlier_rowids:
            placeholders = ",".join("?" * len(outlier_rowids))
            full_cur = conn.execute(
                f"SELECT rowid AS _rowid, * FROM {tq} WHERE rowid IN ({placeholders})",
                outlier_rowids,
            )
            full_rows = [dict(r) for r in full_cur.fetchall()]

            # Map by rowid for quick lookup
            full_map = {r["_rowid"]: r for r in full_rows}

            for i in outlier_indices:
                rid = rowids[i]
                v = values[i]
                z = abs((v - mean_val) / std_val) if std_val > 0 else 0
                row_data = full_map.get(rid, {})
                # Remove _rowid from preview
                preview = {k: v for k, v in row_data.items() if k != "_rowid"}

                outliers_out.append({
                    "rowid": rid,
                    "value": v,
                    "z_score": round(z, 2),
                    "deviation": round(abs(v - median_val), 2),
                    "row_preview": preview,
                })

            # Sort by z_score descending (most extreme first)
            outliers_out.sort(key=lambda x: x["z_score"], reverse=True)

        lower_bound = q1 - req.sensitivity * iqr if req.method == "iqr" else mean_val - req.sensitivity * std_val
        upper_bound = q3 + req.sensitivity * iqr if req.method == "iqr" else mean_val + req.sensitivity * std_val

        return {
            "table": req.table,
            "column": req.column,
            "method": req.method,
            "sensitivity": req.sensitivity,
            "stats": {
                "mean": round(mean_val, 2),
                "median": round(median_val, 2),
                "std": round(std_val, 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(iqr, 2),
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "total_rows": n,
            },
            "outliers": outliers_out,
            "total_rows": n,
            "outlier_count": len(outliers_out),
        }
    finally:
        conn.close()


@router.post("/outliers/action")
def apply_outlier_action(req: ActionRequest):
    if not is_editable_table(req.table):
        raise HTTPException(403, f"Table '{req.table}' is read-only.")

    if not req.rowids:
        raise HTTPException(400, "No rows specified.")

    if req.action == "replace_custom" and req.custom_value is None:
        raise HTTPException(400, "custom_value is required for replace_custom action.")

    conn = connect()
    try:
        names = set(list_user_tables(conn))
        if req.table not in names:
            raise HTTPException(404, f"Unknown table: {req.table}")

        cols = table_columns(conn, req.table)
        if req.column not in cols:
            raise HTTPException(400, f"Column '{req.column}' not found.")

        tq = quote_ident(req.table)
        cq = quote_ident(req.column)

        conn.execute("BEGIN")
        try:
            if req.action == "drop":
                placeholders = ",".join("?" * len(req.rowids))
                conn.execute(f"DELETE FROM {tq} WHERE rowid IN ({placeholders})", req.rowids)
                detail = f"Dropped {len(req.rowids)} row(s)."

            elif req.action in ("replace_median", "replace_mean", "replace_custom"):
                if req.action == "replace_custom":
                    replacement = req.custom_value
                else:
                    # Calculate median or mean from non-outlier rows
                    placeholders = ",".join("?" * len(req.rowids))
                    cur = conn.execute(
                        f"SELECT {cq} FROM {tq} WHERE {cq} IS NOT NULL AND typeof({cq}) IN ('integer', 'real') AND rowid NOT IN ({placeholders})",
                        req.rowids,
                    )
                    clean_vals = sorted(float(r[0]) for r in cur.fetchall())

                    if not clean_vals:
                        raise HTTPException(400, "No clean values remaining to compute replacement.")

                    if req.action == "replace_median":
                        n = len(clean_vals)
                        replacement = clean_vals[n // 2] if n % 2 else (clean_vals[n // 2 - 1] + clean_vals[n // 2]) / 2
                    else:
                        replacement = sum(clean_vals) / len(clean_vals)

                for rid in req.rowids:
                    conn.execute(f"UPDATE {tq} SET {cq} = ? WHERE rowid = ?", (replacement, rid))

                detail = f"Replaced {len(req.rowids)} value(s) with {replacement:,.2f}."
            else:
                raise HTTPException(400, f"Unknown action: {req.action}")

            conn.execute("COMMIT")
        except HTTPException:
            conn.execute("ROLLBACK")
            raise
        except Exception as e:
            conn.execute("ROLLBACK")
            raise HTTPException(500, str(e)) from e

        return {"ok": True, "detail": detail, "affected_rows": len(req.rowids)}
    finally:
        conn.close()
