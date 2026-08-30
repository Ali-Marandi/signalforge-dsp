"""Simple backtesting utilities for SignalForge finance features.

Provides a tiny SMA-crossover backtester as an example of how to turn
indicator signals into trade simulation results and performance metrics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, List

import numpy as np


@dataclass
class Trade:
    entry_index: int
    exit_index: int
    entry_price: float
    exit_price: float
    profit: float


def sma_crossover_backtest(prices: Sequence[float], short_window: int = 10, long_window: int = 50):
    """Run a simple SMA crossover backtest on price series.

    Trading rules (example):
    - Go long when short SMA crosses above long SMA
    - Exit when short SMA crosses below long SMA
    - No leverage, no transaction costs, fully invested on signal

    Returns a dict with trades list and summary metrics.
    """
    prices_arr = np.asarray(prices, dtype=float)
    n = len(prices_arr)
    if n < max(short_window, long_window) + 2:
        raise ValueError("Price series too short for requested SMA windows")

    short_sma = np.convolve(prices_arr, np.ones(short_window) / short_window, mode="valid")
    long_sma = np.convolve(prices_arr, np.ones(long_window) / long_window, mode="valid")
    # align indices: short_sma starts at index short_window-1
    offset = long_window - short_window
    if offset < 0:
        # short window longer than long window: swap
        short_sma, long_sma = long_sma, short_sma
        offset = -offset
    # we'll iterate over the overlapping region
    start = long_window - 1
    trades: List[Trade] = []
    position = False
    entry_price = 0.0
    entry_index = 0
    for t in range(start + 1, n):
        i_short = t - (short_window - 1)
        i_long = t - (long_window - 1)
        if i_short <= 0 or i_long <= 0 or i_short >= len(short_sma) or i_long >= len(long_sma):
            continue
        s = short_sma[i_short]
        l = long_sma[i_long]
        prev_s = short_sma[i_short - 1]
        prev_l = long_sma[i_long - 1]
        # crossover up
        if not position and prev_s <= prev_l and s > l:
            position = True
            entry_price = prices_arr[t]
            entry_index = t
        # crossover down -> exit
        elif position and prev_s >= prev_l and s < l:
            exit_price = prices_arr[t]
            trades.append(Trade(entry_index=entry_index, exit_index=t, entry_price=entry_price, exit_price=exit_price, profit=exit_price - entry_price))
            position = False
    # close any open position at last price
    if position:
        exit_price = float(prices_arr[-1])
        trades.append(Trade(entry_index=entry_index, exit_index=n - 1, entry_price=entry_price, exit_price=exit_price, profit=exit_price - entry_price))

    total_profit = sum(t.profit for t in trades)
    return {"trades": trades, "total_profit": total_profit, "num_trades": len(trades)}
