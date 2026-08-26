"""Local risk-research workflow services for the SignalForge desktop UI.

This module adapts explicit local return-file input into the public
``signalforge_finance`` API. It contains no network, broker, market-data, or
telemetry behavior. It does not infer a return unit, recommend a method, or
turn an estimate into an investment action.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from typing import Literal

import numpy as np
import scipy

from signalforge_finance import DiagnosticValidationError, LocalRiskEngine, RiskConfig, RiskEstimate


MAX_RISK_IMPORT_BYTES = 16 * 1024 * 1024
RiskMethodName = Literal["historical", "normal_parametric", "normal_monte_carlo"]
ReturnUnit = Literal["decimal", "percent"]


@dataclass(frozen=True, slots=True)
class ReturnFilePreview:
    """Ephemeral local preview of a user-selected return file.

    ``data_rows`` remains in memory only to support an explicit column choice.
    It is never included in the default export manifest.
    """

    source_name: str
    source_sha256: str
    source_size_bytes: int
    headers: tuple[str, ...]
    data_rows: tuple[tuple[str, ...], ...]
    dialect_delimiter: str


@dataclass(frozen=True, slots=True)
class RiskResearchRequest:
    """A user-visible, reproducible request for one local risk estimate."""

    method: RiskMethodName
    confidence_level: float
    min_observations: int
    simulation_count: int
    random_seed: int
    return_column: str
    return_unit: ReturnUnit

    def config(self) -> RiskConfig:
        return RiskConfig(
            confidence_level=self.confidence_level,
            min_observations=self.min_observations,
            simulation_count=self.simulation_count,
            random_seed=self.random_seed,
        )


@dataclass(frozen=True, slots=True)
class RiskResearchRun:
    """Local result plus only the provenance needed for a manifest export."""

    source_name: str
    source_sha256: str
    source_size_bytes: int
    source_row_count: int
    delimiter: str
    request: RiskResearchRequest
    estimate: RiskEstimate
    research_use_acknowledged: bool


def _read_local_text(path: str | Path) -> tuple[Path, bytes, str]:
    file_path = Path(path)
    try:
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("The selected return file cannot be read.")
        source_bytes = file_path.read_bytes()
    except OSError as error:
        raise ValueError("The selected return file cannot be read.") from error
    if len(source_bytes) > MAX_RISK_IMPORT_BYTES:
        raise ValueError("Return import file exceeds the 16 MiB size limit.")
    try:
        return file_path, source_bytes, source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Return import files must be UTF-8 encoded text.") from error


def _parse_rows(text: str) -> tuple[list[list[str]], str]:
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        delimiter = dialect.delimiter
        rows = list(csv.reader(text.splitlines(), dialect))
    except csv.Error:
        delimiter = ","
        rows = [[line] for line in text.splitlines()]
    clean_rows = [row for row in rows if row and any(cell.strip() for cell in row)]
    if not clean_rows:
        raise ValueError("The selected return file contains no data rows.")
    return clean_rows, delimiter


def _is_numeric_row(row: list[str]) -> bool:
    nonempty = [cell.strip() for cell in row if cell.strip()]
    if not nonempty:
        return False
    try:
        for cell in nonempty:
            float(cell)
    except ValueError:
        return False
    return True


def preview_return_file(path: str | Path) -> ReturnFilePreview:
    """Read an UTF-8 local table and expose an explicit column-selection preview."""
    file_path, source_bytes, text = _read_local_text(path)
    rows, delimiter = _parse_rows(text)
    widest_row = max(len(row) for row in rows)
    if _is_numeric_row(rows[0]):
        headers = [f"column_{index + 1}" for index in range(widest_row)]
        data_rows = rows
    else:
        headers = [cell.strip() or f"column_{index + 1}" for index, cell in enumerate(rows[0])]
        headers.extend(f"column_{index + 1}" for index in range(len(headers), widest_row))
        data_rows = rows[1:]
    if not data_rows:
        raise ValueError("The selected return file contains a header but no data rows.")
    normalized_rows = tuple(
        tuple(row[index].strip() if index < len(row) else "" for index in range(widest_row)) for row in data_rows
    )
    return ReturnFilePreview(
        source_name=file_path.name,
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_size_bytes=len(source_bytes),
        headers=tuple(headers),
        data_rows=normalized_rows,
        dialect_delimiter=delimiter,
    )


def extract_decimal_returns(preview: ReturnFilePreview, *, column: str, unit: ReturnUnit) -> tuple[float, ...]:
    """Return a selected column as decimal returns without guessing its unit."""
    if column not in preview.headers:
        raise ValueError("Select a return column from the imported file.")
    if unit not in {"decimal", "percent"}:
        raise ValueError("Choose either decimal or percent return units explicitly.")
    column_index = preview.headers.index(column)
    multiplier = 0.01 if unit == "percent" else 1.0
    values: list[float] = []
    for row_number, row in enumerate(preview.data_rows, start=2):
        raw_value = row[column_index] if column_index < len(row) else ""
        if not raw_value:
            raise ValueError(f"Return column contains a missing value at data row {row_number}.")
        try:
            value = float(raw_value) * multiplier
        except ValueError as error:
            raise ValueError(f"Return column contains a non-numeric value at data row {row_number}.") from error
        if not isfinite(value):
            raise ValueError(f"Return column contains a non-finite value at data row {row_number}.")
        values.append(value)
    return tuple(values)


def calculate_risk(
    preview: ReturnFilePreview,
    request: RiskResearchRequest,
    *,
    research_use_acknowledged: bool,
) -> RiskResearchRun:
    """Execute exactly one selected method through the public local risk API."""
    if not research_use_acknowledged:
        raise ValueError("Acknowledge research-only use before calculating a risk estimate.")
    returns = extract_decimal_returns(preview, column=request.return_column, unit=request.return_unit)
    engine = LocalRiskEngine(request.config())
    try:
        if request.method == "historical":
            estimate = engine.historical(returns)
        elif request.method == "normal_parametric":
            estimate = engine.normal_parametric(returns)
        elif request.method == "normal_monte_carlo":
            estimate = engine.normal_monte_carlo(returns)
        else:  # Defensive guard for callers outside the Qt control set.
            raise ValueError("Select a supported local risk method.")
    except DiagnosticValidationError as error:
        raise ValueError(str(error)) from error
    return RiskResearchRun(
        source_name=preview.source_name,
        source_sha256=preview.source_sha256,
        source_size_bytes=preview.source_size_bytes,
        source_row_count=len(preview.data_rows),
        delimiter=preview.dialect_delimiter,
        request=request,
        estimate=estimate,
        research_use_acknowledged=research_use_acknowledged,
    )


def export_risk_manifest(run: RiskResearchRun, path: str | Path, *, application_version: str) -> Path:
    """Write a local JSON manifest without raw return values by default."""
    destination = Path(path)
    payload = {
        "application": "SignalForge Studio",
        "application_version": application_version,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "purpose": "Local research estimate; not a regulatory capital calculation, forecast, recommendation, or order instruction.",
        "source": {
            "name": run.source_name,
            "sha256": run.source_sha256,
            "size_bytes": run.source_size_bytes,
            "data_row_count": run.source_row_count,
            "delimiter": run.delimiter,
            "return_column": run.request.return_column,
            "return_unit": run.request.return_unit,
            "unit_transform": "divide_by_100" if run.request.return_unit == "percent" else "identity",
        },
        "configuration": {
            "method": run.request.method,
            "confidence_level": run.request.confidence_level,
            "min_observations": run.request.min_observations,
            "simulation_count": run.request.simulation_count,
            "random_seed": run.request.random_seed,
            "quantile_method": run.estimate.quantile_method,
        },
        "result": asdict(run.estimate),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "governance": {
            "research_use_acknowledged": run.research_use_acknowledged,
            "raw_return_values_included": False,
        },
    }
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination
