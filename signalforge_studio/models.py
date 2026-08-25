"""Typed, immutable data models for the SignalForge Studio desktop app."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class SignalData:
    """A single sampled signal with its source label and sample rate."""

    samples: tuple[float, ...]
    sample_rate: float
    label: str = "Untitled signal"

    def __post_init__(self) -> None:
        if len(self.samples) < 2:
            raise ValueError("A signal needs at least two samples.")
        if self.sample_rate <= 0 or not isfinite(self.sample_rate):
            raise ValueError("The sample rate must be a positive finite number.")
        if not all(isfinite(sample) for sample in self.samples):
            raise ValueError("Signal samples must be finite numbers.")

    @property
    def duration_seconds(self) -> float:
        """Return the represented duration in seconds."""
        return len(self.samples) / self.sample_rate


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Ready-to-display time and frequency domain analysis for one signal."""

    source: SignalData
    displayed_samples: tuple[float, ...]
    frequencies: tuple[float, ...]
    magnitudes: tuple[float, ...]
    rms: float
    mean: float
    peak: float
    dominant_frequency: float
    fft_size: int
    smoothing_window: int | None = None

    @property
    def nyquist_frequency(self) -> float:
        """Return the highest representable frequency."""
        return self.source.sample_rate / 2

    @property
    def display_sample_rate(self) -> float:
        """Return the time-axis rate after a moving average operation."""
        return self.source.sample_rate

    @property
    def processed(self) -> bool:
        """Return whether a non-destructive smoothing operation is active."""
        return self.smoothing_window is not None


@dataclass(frozen=True, slots=True)
class ExportBundle:
    """The data used by export services without depending on UI widgets."""

    analysis: AnalysisResult
    application_version: str
