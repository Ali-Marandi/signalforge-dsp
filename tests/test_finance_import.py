import tempfile
from pathlib import Path
import pandas as pd

from signalforge_finance.importer import import_market_csv


def test_import_simple_close_csv():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=5, freq="D"),
        "open": [100, 101, 102, 101, 103],
        "high": [101, 102, 103, 102, 104],
        "low": [99, 100, 101, 100, 102],
        "close": [100.5, 101.5, 102.0, 101.0, 103.5],
    })
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample.csv"
        df.to_csv(path, index=False)
        sd = import_market_csv(path)
        assert len(sd.samples) == 5
        assert sd.label.startswith("sample")
        assert sd.sample_rate > 0
