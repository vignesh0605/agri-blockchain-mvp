"""SARIMA-based time-series anomaly detection for price data"""

import numpy as np
from typing import List, Optional


def compute_sarima_residual(price_history: List[float], seasonal_period: int = 12) -> float:
    """
    Returns latest residual from SARIMA fit, or 0 if insufficient data.
    Residual = actual - predicted. Large residuals indicate anomalies.
    """
    if len(price_history) < 20:
        return 0.0

    try:
        # Try to import statsmodels
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        return 0.0

    try:
        model = SARIMAX(
            price_history,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, seasonal_period),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        result = model.fit(disp=False, maxiter=50)
        residual = float(result.resid[-1]) if len(result.resid) > 0 else 0.0
        return residual
    except Exception:
        return 0.0


def compute_price_forecast(price_history: List[float], steps: int = 1, seasonal_period: int = 12) -> List[float]:
    """Compute price forecast using SARIMA"""
    if len(price_history) < 20:
        return [price_history[-1]] * steps if price_history else [0.0] * steps

    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        return [price_history[-1]] * steps if price_history else [0.0] * steps

    try:
        model = SARIMAX(
            price_history,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, seasonal_period),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        result = model.fit(disp=False, maxiter=50)
        forecast = result.forecast(steps=steps)
        return forecast.tolist()
    except Exception:
        return [price_history[-1]] * steps if price_history else [0.0] * steps


def get_price_anomaly_score(price_history: List[float], current_price: float) -> float:
    """
    Compute anomaly score based on SARIMA residual.
    Returns 0-100 score where higher = more anomalous.
    """
    if len(price_history) < 10:
        return 0.0

    residual = compute_sarima_residual(price_history)
    if residual == 0.0:
        return 0.0

    # Normalize residual by historical volatility
    price_std = np.std(price_history) if len(price_history) > 1 else 1.0
    normalized_residual = abs(residual) / (price_std + 1e-6)

    # Convert to 0-100 scale (roughly: 1 sigma = 15, 2 sigma = 35, 3 sigma = 60, 4+ sigma = 80+)
    score = min(100, int(normalized_residual * 15 + 10))
    return float(score)