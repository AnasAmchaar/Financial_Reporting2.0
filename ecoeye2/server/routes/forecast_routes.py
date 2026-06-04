"""Forecast API routes – ML predictions for future financial periods."""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/forecast/predict")
def forecast_predict(
    table: str = Query("data_reel", description="Base (nominal) SQLite table name"),
    horizon: int = Query(12, ge=3, le=36, description="Months to forecast"),
    group_by: str = Query("overall", pattern="^(overall|partner|channel)$"),
):
    """
    Train an ML model on the historical data and predict the next
    ``horizon`` months.  Returns historical series, predictions with
    confidence intervals, model metrics, and feature importances.
    """
    try:
        from ecoeye2.server.ml.forecaster import train_and_predict

        result = train_and_predict(
            table=table,
            horizon=horizon,
            group_by=group_by,
        )
        return asdict(result)
    except Exception as e:
        logger.error("Forecast failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(e)}")


@router.get("/forecast/models")
def forecast_model_info():
    """Return information about the forecasting models used."""
    return {
        "models": [
            {
                "name": "GradientBoostingRegressor",
                "library": "scikit-learn",
                "role": "Primary predictor (70% weight)",
                "description": (
                    "Ensemble of 300 decision trees trained with gradient boosting. "
                    "Captures non-linear relationships between time features, "
                    "macroeconomic indicators (CPI, PPI, policy rate), and financial amounts."
                ),
                "hyperparameters": {
                    "n_estimators": 300,
                    "max_depth": 4,
                    "learning_rate": 0.05,
                    "subsample": 0.8,
                },
            },
            {
                "name": "Holt-Winters Exponential Smoothing",
                "library": "statsmodels",
                "role": "Secondary predictor (30% weight)",
                "description": (
                    "Additive trend and seasonal decomposition model. "
                    "Captures monthly seasonality patterns in the univariate time series."
                ),
                "hyperparameters": {
                    "trend": "additive",
                    "seasonal": "additive",
                    "seasonal_periods": 12,
                },
            },
        ],
        "ensemble": "Weighted average: 70% GBR + 30% Holt-Winters",
        "confidence_intervals": "Quantile regression (10th and 90th percentile) via GBR",
        "features_used": [
            "month_num", "year", "quarter", "trend",
            "sin_month (seasonal)", "cos_month (seasonal)",
            "CPI (Consumer Price Index)",
            "PPI (Producer Price Index)",
            "CPI YoY (Year-over-Year inflation)",
            "Policy Rate (Bank Al-Maghrib)",
        ],
    }
