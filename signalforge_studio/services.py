"""Signal-generation, import, analysis, and export services for SignalForge Studio."""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Iterable
from math import pi, sin
from pathlib import Path

from signalforge import fft_magnitudes, frequency_bins, mean, moving_average, next_power_of_two, peak, rms

from .models import AnalysisResult, ExportBundle, SignalData


MAX_SAMPLES = 131_072


def _validate_generation_inputs(
    sample_rate: float, duration_seconds: float, amplitude: float, frequency: float
) -> int:
    if sample_rate <= 0:
        raise ValueError("Sample rate must be greater than zero.")
    if duration_seconds <= 0:
        raise ValueError("Duration must be greater than zero.")
    if amplitude < 0:
        raise ValueError("Amplitude cannot be negative.")
    if frequency < 0:
        raise ValueError("Frequency cannot be negative.")
    count = int(round(sample_rate * duration_seconds))
    if count < 2:
        raise ValueError("Increase duration or sample rate to generate at least two samples.")
    if count > MAX_SAMPLES:
        raise ValueError(f"Generated signal is limited to {MAX_SAMPLES:,} samples for responsive analysis.")
    return count


def generate_signal(
    kind: str,
    *,
    sample_rate: float,
    duration_seconds: float,
    amplitude: float,
    frequency: float,
    noise_amount: float = 0.0,
    seed: int | None = None,
) -> SignalData:
    """Create a deterministic-on-demand synthetic sampled signal."""
    count = _validate_generation_inputs(sample_rate, duration_seconds, amplitude, frequency)
    if noise_amount < 0 or noise_amount > 1:
        raise ValueError("Noise amount must be between 0 and 1.")
    nyquist = sample_rate / 2
    if kind not in {"Sine", "Square", "Impulse", "Noise", "Chirp"}:
        raise ValueError(f"Unsupported signal source: {kind}")
    if kind not in {"Impulse", "Noise"} and frequency >= nyquist:
        raise ValueError("Frequency must be below the Nyquist frequency.")

    generator = random.Random(seed)
    samples: list[float] = []
    chirp_end = min(nyquist * 0.9, max(frequency * 4, frequency + 50.0))
    sweep_rate = (chirp_end - frequency) / duration_seconds
    for index in range(count):
        time_seconds = index / sample_rate
        if kind == "Sine":
            value = amplitude * sin(2 * pi * frequency * time_seconds)
        elif kind == "Square":
            value = amplitude if sin(2 * pi * frequency * time_seconds) >= 0 else -amplitude
        elif kind == "Impulse":
            value = amplitude if index == 0 else 0.0
        elif kind == "Noise":
            value = amplitude * generator.uniform(-1.0, 1.0)
        else:  # Chirp
            phase = 2 * pi * (frequency * time_seconds + 0.5 * sweep_rate * time_seconds**2)
            value = amplitude * sin(phase)
        if noise_amount and kind != "Noise":
            value += amplitude * noise_amount * generator.uniform(-1.0, 1.0)
        samples.append(value)

    return SignalData(tuple(samples), float(sample_rate), f"{kind} generator")


def _numeric_values_from_rows(rows: Iterable[list[str]]) -> list[float]:
    """Return a sensible numeric signal column while tolerating a CSV header.

    A common two-column file begins with a time/index column and an amplitude
    column. When a header explicitly names a time-like first column, the
    corresponding numeric amplitude column is preferred.
    """
    raw_rows = [row for row in rows if row and any(cell.strip() for cell in row)]
    parsed_rows: list[list[float | None]] = []
    for row in raw_rows:
        parsed: list[float | None] = []
        for cell in row:
            try:
                parsed.append(float(cell.strip()))
            except ValueError:
                parsed.append(None)
        parsed_rows.append(parsed)

    if not parsed_rows:
        raise ValueError("The selected file does not contain numeric samples.")
    width = max(len(row) for row in parsed_rows)
    header = raw_rows[0] if parsed_rows[0] and all(value is None for value in parsed_rows[0]) else []
    start_index = 1 if header else 0
    columns = list(range(width))
    time_names = {"time", "timestamp", "seconds", "second", "sample", "index", "x"}
    if header and header[0].strip().casefold() in time_names and width > 1:
        columns = list(range(1, width)) + [0]
    for column in columns:
        values = [row[column] for row in parsed_rows[start_index:] if column < len(row) and row[column] is not None]
        if len(values) >= 2:
            return [value for value in values if value is not None]
    raise ValueError("No numeric signal column with at least two samples was found.")


def import_signal(path: str | Path, *, sample_rate: float) -> SignalData:
    """Load the first numeric column of a UTF-8 CSV or text file."""
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ValueError("The selected file cannot be read.")
    if sample_rate <= 0:
        raise ValueError("Sample rate must be greater than zero.")

    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Import files must be UTF-8 encoded text.") from error

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        rows = list(csv.reader(text.splitlines(), dialect))
    except csv.Error:
        rows = [[line] for line in text.splitlines()]
    values = _numeric_values_from_rows(rows)
    if len(values) > MAX_SAMPLES:
        raise ValueError(f"Imported signal exceeds the {MAX_SAMPLES:,}-sample analysis limit.")
    return SignalData(tuple(values), float(sample_rate), file_path.stem)


def analyse_signal(signal: SignalData, *, smoothing_window: int | None = None) -> AnalysisResult:
    """Produce a non-destructive time/frequency analysis for a source signal."""
    displayed = list(signal.samples)
    window: int | None = None
    if smoothing_window is not None:
        window = int(smoothing_window)
        if window > 1:
            displayed = moving_average(displayed, window)
        else:
            window = None

    fft_size = next_power_of_two(len(displayed))
    magnitudes = fft_magnitudes(displayed, fft_size)
    frequencies = frequency_bins(signal.sample_rate, fft_size)
    if len(magnitudes) > 1:
        dominant_index = max(range(1, len(magnitudes)), key=magnitudes.__getitem__)
    else:
        dominant_index = 0

    return AnalysisResult(
        source=signal,
        displayed_samples=tuple(displayed),
        frequencies=tuple(frequencies),
        magnitudes=tuple(magnitudes),
        rms=rms(displayed),
        mean=mean(displayed),
        peak=peak(displayed),
        dominant_frequency=frequencies[dominant_index],
        fft_size=fft_size,
        smoothing_window=window,
    )


def export_csv(bundle: ExportBundle, path: str | Path) -> Path:
    """Write the visible time-domain data as a portable CSV file."""
    destination = Path(path)
    analysis = bundle.analysis
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["time_seconds", "amplitude", "source", "sample_rate_hz"])
        for index, value in enumerate(analysis.displayed_samples):
            writer.writerow(
                [
                    f"{index / analysis.source.sample_rate:.12g}",
                    f"{value:.12g}",
                    analysis.source.label,
                    f"{analysis.source.sample_rate:.12g}",
                ]
            )
    return destination


def export_summary(bundle: ExportBundle, path: str | Path) -> Path:
    """Write repeatable analysis metadata as a human-readable JSON summary."""
    destination = Path(path)
    analysis = bundle.analysis
    payload = {
        "application": "SignalForge Studio",
        "version": bundle.application_version,
        "source": analysis.source.label,
        "sample_rate_hz": analysis.source.sample_rate,
        "sample_count": len(analysis.source.samples),
        "displayed_sample_count": len(analysis.displayed_samples),
        "duration_seconds": analysis.source.duration_seconds,
        "smoothing_window": analysis.smoothing_window,
        "fft_size": analysis.fft_size,
        "rms": analysis.rms,
        "mean": analysis.mean,
        "peak": analysis.peak,
        "dominant_frequency_hz": analysis.dominant_frequency,
        "nyquist_frequency_hz": analysis.nyquist_frequency,
    }
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return destination
