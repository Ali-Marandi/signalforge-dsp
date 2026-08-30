"""Technical indicators for financial series used by SignalForge.

Simple, dependency-on-pandas implementations of common indicators so the
desktop UI can compute and display them without external services.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def sma(values: Sequence[float], window: int) -> list[float]:
    s = pd.Series(values)
    return list(s.rolling(window=window, min_periods=1).mean().to_numpy())


def ema(values: Sequence[float], window: int) -> list[float]:
    s = pd.Series(values)
    return list(s.ewm(span=window, adjust=False).mean().to_numpy())


def rsi(values: Sequence[float], window: int = 14) -> list[float]:
    s = pd.Series(values)
    delta = s.diff()
    up = delta.clip(lower=0).fillna(0)
    down = -delta.clip(upper=0).fillna(0)
    ma_up = up.ewm(alpha=1/window, adjust=False).mean()
    ma_down = down.ewm(alpha=1/window, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    return list(rsi_series.fillna(50).to_numpy())


def macd(values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9):
    s = pd.Series(values)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return list(macd_line.to_numpy()), list(signal_line.to_numpy()), list(histogram.to_numpy())
