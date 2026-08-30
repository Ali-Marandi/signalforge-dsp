"""Time-series modeling wrappers for SignalForge finance features.

This module provides small, well-documented wrappers around commonly-used
packages to fit ARIMA forecasts and estimate conditional volatility with a
GARCH(1,1) model. They keep dependency surface minimal and present simple
inputs/outputs for the desktop app.

Note: The functions here are thin wrappers around statsmodels and arch and
assume the caller has installed the optional finance requirements.
"""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np

try:
    from statsmodels.tsa.arima.model import ARIMA
except Exception:  # pragma: no cover - imported in runtime when available
    ARIMA = None

try:
    from arch import arch_model
except Exception:  # pragma: no cover - imported in runtime when available
    arch_model = None


def arima_forecast(values: Sequence[float], order: Tuple[int, int, int] = (1, 0, 0), steps: int = 1):
    """Fit a small ARIMA model and return the out-of-sample forecast.

    Args:
        values: numeric time series (list/tuple/ndarray)
        order: the (p,d,q) ARIMA order
        steps: number of steps to forecast

    Returns:
        Tuple(forecasts, conf_int): forecasts is a list of length `steps`,
        conf_int is an array-like of shape (steps, 2) with lower/upper bounds.

    Raises:
        RuntimeError: if statsmodels is not installed.
    """
    if ARIMA is None:
        raise RuntimeError("statsmodels is required for ARIMA forecasting")
    series = np.asarray(values, dtype=float)
    if series.size < max(3, sum(order)):
        raise ValueError("Series is too short for ARIMA fitting with requested order")
    model = ARIMA(series, order=order)
    fitted = model.fit()
    forecast_res = fitted.get_forecast(steps=steps)
    return list(forecast_res.predicted_mean.tolist()), forecast_res.conf_int().to_numpy()


def garch_volatility(values: Sequence[float]):
    """Estimate conditional volatility using a GARCH(1,1) model.

    Returns a dict with keys: 'conditional_vol', 'params'.
    - conditional_vol: numpy array with the estimated conditional volatility
    - params: fitted parameter series (mapping)

    Raises:
        RuntimeError: if arch is not installed.
    """
    if arch_model is None:
        raise RuntimeError("arch is required for GARCH volatility estimation")
    series = np.asarray(values, dtype=float)
    if series.size < 10:
        raise ValueError("Series is too short for GARCH estimation")
    # use zero-mean returns assumption; fit to series (assumed returns)
    model = arch_model(series, vol="Garch", p=1, q=1, dist="normal")
    res = model.fit(disp="off")
    cond_vol = res.conditional_volatility
    return {"conditional_vol": cond_vol, "params": res.params.to_dict()}
