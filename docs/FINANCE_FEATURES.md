## Financial features and how to use them

This document describes the optional finance-focused extensions in the
feature/finance-importer branch. They are local-only utilities that enable
importing market CSV files, computing common technical indicators, and
visualizing OHLC candlesticks alongside the existing waveform and spectrum
views.

Important: These features are optional and require extra dependencies. See
`requirements-finance.txt` for installation instructions.

### Importing market data

- Use `File → Import market CSV…` to open a CSV containing timestamped market
  data. The importer will attempt to detect a timestamp column (`date`,
  `datetime`, `timestamp`, `time`, `ts`) or fall back to the first column if it
  parses as datetimes.
- Common OHLC column names are supported (`open`, `high`, `low`, `close`). If
  present, the app will show a candlestick view and also use the `close`
  series for numeric analysis and FFT.
- If no OHLC columns are found but a numeric column such as `close` exists,
  the import will treat it as a price series and show the waveform view.
- The importer enforces a 16 MiB size limit to avoid unbounded memory use when
  importing large data files.

### Indicators

- The UI exposes checkboxes and window selectors for SMA, EMA and RSI in the
  left control pane under an "Indicators" group.
- Enabling SMA/EMA overlays the chosen moving-average lines on the waveform.
- Enabling RSI computes and displays the RSI as part of the analysis (a small
  subplot is planned in future iterations).

### Developer notes

- `signalforge_finance.importer` provides `import_market_csv` (returns
  `SignalData`) and `import_market_csv_df` (returns `pandas.DataFrame` for OHLC
  rendering).
- `signalforge_finance.indicators` provides `sma`, `ema`, `rsi`, `macd`.
- To run tests for finance features: `pip install -r requirements-finance.txt` and
  `pytest tests/test_finance_import.py tests/test_indicators.py`.

