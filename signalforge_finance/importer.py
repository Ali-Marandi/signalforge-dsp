"""Finance-focused importer utilities for SignalForge.

This module provides a small, dependency-driven CSV importer that converts
common market data files (OHLC or single-column price series) into the
SignalData dataclass used by the desktop app. It aims to be permissive and
helpful for exploratory analysis from local CSVs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from signalforge_studio.models import SignalData

PREFERRED_PRICE_COLUMNS = ("close", "adj_close", "adjusted_close", "price", "last")
MAX_IMPORT_BYTES = 16 * 1024 * 1024


def _choose_price_column(df: pd.DataFrame) -> str:
    lower = {c.lower(): c for c in df.columns}
    for candidate in PREFERRED_PRICE_COLUMNS:
        if candidate in lower:
            return lower[candidate]
    # fallback: if exactly one numeric column (besides index) pick it
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) == 1:
        return numeric_cols[0]
    raise ValueError("Could not determine a numeric price column (expected 'close' etc.).")


def import_market_csv(path: str | Path, *, datetime_column: Optional[str] = None, tz: Optional[str] = None, resample_rule: Optional[str] = None) -> SignalData:
    """
    Read a market CSV and return a SignalData containing the selected price series.

    - path: path to CSV (parsed with pandas.read_csv)
    - datetime_column: explicit column name for timestamps; if None, autodetect common names.
    - tz: optional timezone to localize timestamps (pytz/zoneinfo string)
    - resample_rule: pandas resample rule (e.g., '1D', '1H') to up/down-sample the series.

    The returned SignalData.samples are the price values (tuple[float,...]).
    sample_rate is set to 1.0 / median_delta_seconds (Hz). For daily data sample_rate ~ 1/86400.
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        raise ValueError("The selected file cannot be read.")

    # guard file size to prevent memory blowups in the desktop app
    try:
        size = path.stat().st_size
    except OSError:
        raise ValueError("The selected file cannot be read.")
    if size > MAX_IMPORT_BYTES:
        raise ValueError("Import file exceeds the 16 MiB size limit.")

    # Let pandas attempt to parse datetimes lazily; we'll coerce/locate below
    df = pd.read_csv(path)

    dt_col = None
    possible_dt_names = ["date", "datetime", "timestamp", "time", "ts"]
    if datetime_column:
        if datetime_column not in df.columns:
            raise ValueError(f"datetime_column '{datetime_column}' not found in CSV")
        dt_col = datetime_column
    else:
        for name in possible_dt_names:
            if name in df.columns:
                dt_col = name
                break
        if dt_col is None and df.columns.size >= 1:
            first = df.columns[0]
            # try to parse first column as datetimes
            parsed = pd.to_datetime(df[first], errors="coerce", infer_datetime_format=True)
            if parsed.notna().sum() >= max(2, len(parsed) // 4):
                dt_col = first
                df[first] = parsed

    if dt_col is None:
        raise ValueError("Could not find a timestamp column. Provide datetime_column explicitly.")

    df[dt_col] = pd.to_datetime(df[dt_col], errors="raise", infer_datetime_format=True)
    if tz:
        df[dt_col] = df[dt_col].dt.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward")
    df = df.set_index(dt_col).sort_index()

    price_col = _choose_price_column(df)
    series = df[price_col].astype(float).dropna()

    if series.size < 2:
        raise ValueError("Not enough numeric price samples found.")

    if resample_rule:
        # use last price in the resample period (like market close)
        series = series.resample(resample_rule).last().ffill().dropna()

    # Compute sample_rate as 1 / median(delta_seconds)
    # pandas datetime index values are ns since epoch as int64
    deltas = np.diff(series.index.astype("int64")) / 1e9  # ns -> seconds
    median_delta = float(np.median(deltas))
    if median_delta <= 0:
        raise ValueError("Invalid timestamp spacing in input data.")
    sample_rate = 1.0 / median_delta

    samples = tuple(map(float, series.values))
    label = f"{path.stem} ({price_col})"
    return SignalData(samples=samples, sample_rate=float(sample_rate), label=label)


def import_market_csv_df(path: str | Path, *, datetime_column: Optional[str] = None, tz: Optional[str] = None, resample_rule: Optional[str] = None) -> pd.DataFrame:
    """
    Read a market CSV and return a pandas Series or DataFrame indexed by timestamp.

    This helper is intended for callers that need OHLC information for plotting
    (candlesticks) or more advanced processing. It will parse datetimes, set
    the index, optionally resample, and return the DataFrame with the original
    columns (including parsed numeric columns).
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        raise ValueError("The selected file cannot be read.")

    try:
        size = path.stat().st_size
    except OSError:
        raise ValueError("The selected file cannot be read.")
    if size > MAX_IMPORT_BYTES:
        raise ValueError("Import file exceeds the 16 MiB size limit.")

    df = pd.read_csv(path)
    dt_col = None
    possible_dt_names = ["date", "datetime", "timestamp", "time", "ts"]
    if datetime_column:
        if datetime_column not in df.columns:
            raise ValueError(f"datetime_column '{datetime_column}' not found in CSV")
        dt_col = datetime_column
    else:
        for name in possible_dt_names:
            if name in df.columns:
                dt_col = name
                break
        if dt_col is None and df.columns.size >= 1:
            first = df.columns[0]
            parsed = pd.to_datetime(df[first], errors="coerce", infer_datetime_format=True)
            if parsed.notna().sum() >= max(2, len(parsed) // 4):
                dt_col = first
                df[first] = parsed

    if dt_col is None:
        raise ValueError("Could not find a timestamp column. Provide datetime_column explicitly.")

    df[dt_col] = pd.to_datetime(df[dt_col], errors="raise", infer_datetime_format=True)
    if tz:
        df[dt_col] = df[dt_col].dt.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward")
    df = df.set_index(dt_col).sort_index()

    if resample_rule:
        # for OHLC-like data prefer aggregate for ohlc
        if {"open", "high", "low", "close"}.issubset({c.lower() for c in df.columns}):
            # normalize column names casing
            cols = {c.lower(): c for c in df.columns}
            df_res = df.resample(resample_rule).agg({
                cols.get("open"): "first",
                cols.get("high"): "max",
                cols.get("low"): "min",
                cols.get("close"): "last",
            })
        else:
            df_res = df.resample(resample_rule).last()
        df = df_res.ffill().dropna()

    return df
