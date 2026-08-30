import tempfile
from pathlib import Path
import pandas as pd
from signalforge_finance.importer import import_market_csv, MAX_IMPORT_BYTES


def test_import_file_size_limit():
    # create a temporary file larger than MAX_IMPORT_BYTES and assert import fails
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "big.csv"
        # write slightly larger than limit
        with path.open("wb") as f:
            f.write(b"0" * (MAX_IMPORT_BYTES + 1024))
        try:
            import_market_csv(path)
            assert False, "Expected import_market_csv to raise for large file"
        except ValueError as e:
            assert "16 MiB" in str(e)
