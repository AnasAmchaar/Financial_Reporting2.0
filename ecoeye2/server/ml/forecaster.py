"""
ML Forecasting Engine for EcoEye2.

Trains on historical financial data (nominal + real) enriched with
macroeconomic indicators (CPI, PPI, policy_rate) and predicts N months
into the future.  Two models are ensembled:

  1. GradientBoostingRegressor  (scikit-learn) – captures non-linear
     interactions between features and target.
  2. Holt-Winters Exponential Smoothing (statsmodels) – captures trend
     and seasonality in the univariate series.

The final prediction is a weighted average of both (70 % GB, 30 % HW).
Confidence intervals come from quantile regression on the GB side.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from config.settings import DB_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ForecastResult:
    """Serialisable output of a forecast run."""

    historical: list[dict[str, Any]]
    predictions: list[dict[str, Any]]
    metrics: dict[str, float]
    feature_importances: list[dict[str, Any]]
    model_info: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _load_monthly_series(
    conn: sqlite3.Connection,
    table: str = "data_reel",
    group_by: str = "overall",
) -> pd.DataFrame:
    """Aggregate ``table`` into a monthly time-series.

    Returns a DataFrame indexed by ``period`` (datetime, month-start) with at
    least an ``amount`` column.  If the ``_real`` companion table exists the
    real amount is joined in as ``amount_real``.
    """
    # Nominal
    if group_by == "overall":
        sql_nom = f"""
            SELECT strftime('%Y-%m', date) AS period,
                   SUM(amount)             AS amount
            FROM   "{table}"
            WHERE  date IS NOT NULL
            GROUP  BY period
            ORDER  BY period
        """
    else:
        dim = "partner" if group_by == "partner" else "channel"
        sql_nom = f"""
            SELECT strftime('%Y-%m', date) AS period,
                   "{dim}",
                   SUM(amount) AS amount
            FROM   "{table}"
            WHERE  date IS NOT NULL
            GROUP  BY period, "{dim}"
            ORDER  BY period, "{dim}"
        """

    df = pd.read_sql(sql_nom, conn)
    if df.empty:
        return df

    # Period to datetime
    df["period"] = pd.to_datetime(df["period"] + "-01")

    # Try real table
    real_table = f"{table}_real"
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (real_table,),
        )
        if cur.fetchone():
            # Find real amount column
            cur2 = conn.execute(f'PRAGMA table_info("{real_table}")')
            real_col = None
            for row in cur2.fetchall():
                if str(row[1]).startswith("amount_real_"):
                    real_col = row[1]
                    break
            if real_col and group_by == "overall":
                sql_real = f"""
                    SELECT strftime('%Y-%m', date) AS period,
                           SUM("{real_col}")       AS amount_real
                    FROM   "{real_table}"
                    WHERE  date IS NOT NULL
                    GROUP  BY period
                    ORDER  BY period
                """
                df_real = pd.read_sql(sql_real, conn)
                df_real["period"] = pd.to_datetime(df_real["period"] + "-01")
                df = df.merge(df_real, on="period", how="left")
    except Exception:
        pass  # real table optional

    return df


def _load_econ_indicators(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load economic indicators pivoted wide by month."""
    try:
        ind = pd.read_sql("SELECT * FROM econ_indicators", conn)
    except Exception:
        return pd.DataFrame()

    if ind.empty:
        return pd.DataFrame()

    ind["date"] = pd.to_datetime(ind["date"], errors="coerce")
    ind = ind.dropna(subset=["date"])
    ind["period"] = ind["date"].dt.to_period("M").dt.to_timestamp()

    # Pivot: one column per indicator_code
    pivot = ind.pivot_table(
        index="period", columns="indicator_code", values="value", aggfunc="mean"
    )
    pivot = pivot.sort_index()
    return pivot.reset_index()


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer calendar / trend features from ``period``."""
    df = df.copy()
    df["month_num"] = df["period"].dt.month
    df["year"] = df["period"].dt.year
    df["quarter"] = df["period"].dt.quarter
    # Ordinal trend
    df["trend"] = np.arange(len(df))
    # Sine / cosine seasonality
    df["sin_month"] = np.sin(2 * np.pi * df["month_num"] / 12)
    df["cos_month"] = np.cos(2 * np.pi * df["month_num"] / 12)
    return df


def _extrapolate_econ(econ_pivot: pd.DataFrame, n_months: int) -> pd.DataFrame:
    """Linearly extrapolate economic indicators for future months."""
    if econ_pivot.empty:
        return econ_pivot

    last_date = econ_pivot["period"].max()
    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1), periods=n_months, freq="MS"
    )

    rows: list[dict] = []
    for d in future_dates:
        row: dict[str, Any] = {"period": d}
        for col in econ_pivot.columns:
            if col == "period":
                continue
            series = econ_pivot[col].dropna()
            if len(series) >= 2:
                # Linear slope from last 12 points (or all)
                tail = series.tail(min(12, len(series)))
                x = np.arange(len(tail), dtype=float)
                y = tail.values.astype(float)
                slope = np.polyfit(x, y, 1)[0]
                row[col] = float(y[-1] + slope * (1 + len(tail)))
            elif len(series) == 1:
                row[col] = float(series.iloc[0])
            else:
                row[col] = np.nan
        rows.append(row)

    return pd.concat([econ_pivot, pd.DataFrame(rows)], ignore_index=True)


# ---------------------------------------------------------------------------
# Core forecaster
# ---------------------------------------------------------------------------

def train_and_predict(
    table: str = "data_reel",
    horizon: int = 12,
    group_by: str = "overall",
    db_path: Path | None = None,
) -> ForecastResult:
    """Train on historical data and predict ``horizon`` months ahead."""

    conn = _connect(db_path)
    try:
        # 1. Load data -------------------------------------------------------
        df = _load_monthly_series(conn, table, group_by)
        if df.empty or len(df) < 6:
            return ForecastResult(
                historical=[],
                predictions=[],
                metrics={"error": -1},
                feature_importances=[],
                model_info={"status": "insufficient_data"},
            )

        # For non-overall groupings, aggregate to overall for the forecast
        if group_by != "overall" and "partner" in df.columns:
            dim = "partner" if group_by == "partner" else "channel"
            # Return per-dimension historical, but forecast only overall
            df = df.groupby("period", as_index=False).agg({"amount": "sum"})

        econ_pivot = _load_econ_indicators(conn)
    finally:
        conn.close()

    # 2. Merge econ indicators ------------------------------------------------
    if not econ_pivot.empty:
        df = df.merge(econ_pivot, on="period", how="left")
        # Forward-fill econ indicators (annual data interpolated)
        econ_cols = [c for c in econ_pivot.columns if c != "period"]
        for c in econ_cols:
            df[c] = df[c].interpolate(method="linear").ffill().bfill()
    else:
        econ_cols = []

    # 3. Feature engineering ---------------------------------------------------
    df = _add_time_features(df)
    df = df.sort_values("period").reset_index(drop=True)

    feature_cols = ["month_num", "year", "quarter", "trend", "sin_month", "cos_month"]
    feature_cols += [c for c in econ_cols if c in df.columns]

    target = "amount"
    df[target] = pd.to_numeric(df[target], errors="coerce")
    df = df.dropna(subset=[target])

    X = df[feature_cols].values.astype(float)
    y = df[target].values.astype(float)

    # Replace any remaining NaN in features with 0
    X = np.nan_to_num(X, nan=0.0)

    # 4. Train GB model --------------------------------------------------------
    gb = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
        loss="squared_error",
    )

    # Quantile models for confidence intervals
    gb_lower = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
        loss="quantile",
        alpha=0.1,
    )
    gb_upper = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
        loss="quantile",
        alpha=0.9,
    )

    gb.fit(X, y)
    gb_lower.fit(X, y)
    gb_upper.fit(X, y)

    # 5. Train Holt-Winters (univariate) --------------------------------------
    hw_pred = np.zeros(horizon)
    try:
        seasonal_periods = min(12, len(y) // 2)
        if seasonal_periods >= 2 and len(y) >= 2 * seasonal_periods:
            hw = ExponentialSmoothing(
                y,
                trend="add",
                seasonal="add",
                seasonal_periods=seasonal_periods,
            ).fit(optimized=True)
            hw_pred = hw.forecast(horizon)
        else:
            # Fallback: simple exponential smoothing
            hw = ExponentialSmoothing(y, trend="add", seasonal=None).fit(
                optimized=True
            )
            hw_pred = hw.forecast(horizon)
    except Exception as exc:
        logger.warning("Holt-Winters fit failed, using GB only: %s", exc)
        hw_pred = np.zeros(horizon)

    # 6. CV metrics (time-series split) ----------------------------------------
    tscv = TimeSeriesSplit(n_splits=min(3, len(y) // 3))
    cv_mae, cv_rmse, cv_r2 = [], [], []
    cv_folds = []
    cv_predictions = []
    periods = df["period"].dt.strftime("%Y-%m").tolist()

    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        gb_cv = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42
        )
        gb_cv.fit(X_tr, y_tr)
        preds = gb_cv.predict(X_te)
        
        mae_val = mean_absolute_error(y_te, preds)
        rmse_val = float(np.sqrt(mean_squared_error(y_te, preds)))
        r2_val = r2_score(y_te, preds)
        
        cv_mae.append(mae_val)
        cv_rmse.append(rmse_val)
        cv_r2.append(r2_val)
        
        cv_folds.append({
            "fold": fold_idx + 1,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "mae": float(mae_val),
            "rmse": float(rmse_val),
            "r2": float(r2_val),
        })
        
        for k, idx in enumerate(test_idx):
            cv_predictions.append({
                "fold": fold_idx + 1,
                "period": periods[idx],
                "actual": float(y_te[k]),
                "predicted": float(preds[k]),
                "residual": float(y_te[k] - preds[k]),
            })

    metrics = {
        "mae": float(np.mean(cv_mae)) if cv_mae else 0.0,
        "rmse": float(np.mean(cv_rmse)) if cv_rmse else 0.0,
        "r2": float(np.mean(cv_r2)) if cv_r2 else 0.0,
        "n_train": int(len(y)),
        "horizon": horizon,
        "cv_folds": cv_folds,
        "cv_predictions": cv_predictions,
    }

    # 7. Feature importances ---------------------------------------------------
    importances = gb.feature_importances_
    feat_imp = sorted(
        [
            {"feature": feature_cols[i], "importance": float(importances[i])}
            for i in range(len(feature_cols))
        ],
        key=lambda x: x["importance"],
        reverse=True,
    )

    # 8. Build future feature matrix -------------------------------------------
    last_period = df["period"].max()
    future_periods = pd.date_range(
        start=last_period + pd.DateOffset(months=1), periods=horizon, freq="MS"
    )

    # Extrapolate econ for future
    if not econ_pivot.empty:
        econ_ext = _extrapolate_econ(econ_pivot, horizon)
    else:
        econ_ext = pd.DataFrame()

    future_rows = []
    for i, fp in enumerate(future_periods):
        row: dict[str, Any] = {
            "period": fp,
            "month_num": fp.month,
            "year": fp.year,
            "quarter": fp.quarter,
            "trend": len(df) + i,
            "sin_month": float(np.sin(2 * np.pi * fp.month / 12)),
            "cos_month": float(np.cos(2 * np.pi * fp.month / 12)),
        }
        # Merge econ
        if not econ_ext.empty:
            econ_row = econ_ext[econ_ext["period"] == fp]
            for c in econ_cols:
                if not econ_row.empty and c in econ_row.columns:
                    row[c] = float(econ_row[c].iloc[0]) if pd.notna(econ_row[c].iloc[0]) else 0.0
                else:
                    row[c] = 0.0
        future_rows.append(row)

    future_df = pd.DataFrame(future_rows)
    X_future = future_df[feature_cols].values.astype(float)
    X_future = np.nan_to_num(X_future, nan=0.0)

    # 9. Predict ---------------------------------------------------------------
    gb_preds = gb.predict(X_future)
    lower_preds = gb_lower.predict(X_future)
    upper_preds = gb_upper.predict(X_future)

    # Ensemble: 70% GB + 30% HW
    if hw_pred is not None and len(hw_pred) == horizon:
        ensemble_preds = 0.7 * gb_preds + 0.3 * hw_pred
    else:
        ensemble_preds = gb_preds

    # 10. Build historical output -----------------------------------------------
    historical = []
    for _, row in df.iterrows():
        entry: dict[str, Any] = {
            "period": row["period"].strftime("%Y-%m"),
            "amount": float(row["amount"]),
        }
        if "amount_real" in df.columns and pd.notna(row.get("amount_real")):
            entry["amount_real"] = float(row["amount_real"])
        historical.append(entry)

    # 11. Build prediction output -----------------------------------------------
    predictions = []
    for i, fp in enumerate(future_periods):
        pred_val = float(max(0, ensemble_preds[i]))  # floor at 0
        lower_val = float(max(0, lower_preds[i]))
        upper_val = float(max(0, upper_preds[i]))

        # Estimate real value by applying last known CPI deflator ratio
        real_ratio = 1.0
        if "amount_real" in df.columns:
            last_known = df.dropna(subset=["amount_real"]).tail(6)
            if not last_known.empty:
                nom = last_known["amount"].sum()
                real = last_known["amount_real"].sum()
                if nom > 0:
                    real_ratio = real / nom

        predictions.append(
            {
                "period": fp.strftime("%Y-%m"),
                "predicted_nominal": round(pred_val, 2),
                "predicted_real": round(pred_val * real_ratio, 2),
                "confidence_lower": round(lower_val, 2),
                "confidence_upper": round(upper_val, 2),
            }
        )

    return ForecastResult(
        historical=historical,
        predictions=predictions,
        metrics=metrics,
        feature_importances=feat_imp,
        model_info={
            "primary": "GradientBoostingRegressor (300 trees, depth=4)",
            "secondary": "Holt-Winters Exponential Smoothing",
            "ensemble": "70% GBR + 30% HW",
            "confidence": "Quantile regression (10th / 90th percentile)",
        },
    )
