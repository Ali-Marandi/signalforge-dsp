"""Dependency-light digital signal processing primitives for SignalForge.

The module preserves simple, readable implementations for teaching while also
providing an iterative radix-2 FFT for responsive desktop analysis.
"""

from __future__ import annotations

from cmath import exp
from collections.abc import Sequence
from math import isfinite, pi, sqrt


NumberSequence = Sequence[float]


def _validated_samples(samples: NumberSequence, *, minimum: int = 1) -> list[float]:
    """Return finite float samples or raise a clear ``ValueError``."""
    values = [float(value) for value in samples]
    if len(values) < minimum:
        plural = "s" if minimum != 1 else ""
        raise ValueError(f"at least {minimum} sample{plural} are required")
    if not all(isfinite(value) for value in values):
        raise ValueError("samples must contain only finite values")
    return values


def rms(samples: NumberSequence) -> float:
    """Calculate the root-mean-square level of a non-empty signal."""
    values = _validated_samples(samples)
    return sqrt(sum(value * value for value in values) / len(values))


def mean(samples: NumberSequence) -> float:
    """Calculate the arithmetic mean of a non-empty signal."""
    values = _validated_samples(samples)
    return sum(values) / len(values)


def peak(samples: NumberSequence) -> float:
    """Calculate the absolute peak level of a non-empty signal."""
    values = _validated_samples(samples)
    return max(abs(value) for value in values)


def moving_average(samples: NumberSequence, window: int) -> list[float]:
    """Return a trailing moving average in O(n) time.

    The result has ``len(samples) - window + 1`` values. It is intentionally
    not padded so the operation remains mathematically transparent.
    """
    values = _validated_samples(samples)
    if not isinstance(window, int) or isinstance(window, bool):
        raise ValueError("window must be an integer")
    if not 1 <= window <= len(values):
        raise ValueError("window must fit the signal")

    total = sum(values[:window])
    result = [total / window]
    for index in range(window, len(values)):
        total += values[index] - values[index - window]
        result.append(total / window)
    return result


def dft_magnitudes(samples: NumberSequence) -> list[float]:
    """Return one-sided, normalized direct DFT magnitudes.

    This O(n²) implementation is kept for education and verification. Use
    :func:`fft_magnitudes` for desktop-sized signal analysis.
    """
    values = _validated_samples(samples)
    n = len(values)
    return [
        abs(sum(value * exp(-2j * pi * k * index / n) for index, value in enumerate(values))) / n
        for k in range(n // 2 + 1)
    ]


def is_power_of_two(value: int) -> bool:
    """Return whether ``value`` is a positive power of two."""
    return value > 0 and value & (value - 1) == 0


def next_power_of_two(value: int) -> int:
    """Return the smallest power of two that is at least ``value``."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("value must be a positive integer")
    return 1 << (value - 1).bit_length()


def fft_magnitudes(samples: NumberSequence, n_fft: int | None = None) -> list[float]:
    """Return one-sided normalized FFT magnitudes using a radix-2 algorithm.

    When ``n_fft`` is omitted, the input is zero-padded to its next power of
    two. The output remains normalized against the original sample count, so a
    zero-padded sine wave keeps the same magnitude as its unpadded equivalent.
    """
    values = _validated_samples(samples, minimum=2)
    original_count = len(values)
    size = next_power_of_two(original_count) if n_fft is None else n_fft
    if not isinstance(size, int) or isinstance(size, bool) or not is_power_of_two(size):
        raise ValueError("n_fft must be a power of two")
    if size < original_count:
        raise ValueError("n_fft cannot be smaller than the signal length")

    transformed = [complex(value, 0.0) for value in values]
    transformed.extend([0j] * (size - original_count))

    # In-place bit-reversal permutation.
    reverse_index = 0
    for index in range(1, size):
        bit = size >> 1
        while reverse_index & bit:
            reverse_index ^= bit
            bit >>= 1
        reverse_index ^= bit
        if index < reverse_index:
            transformed[index], transformed[reverse_index] = transformed[reverse_index], transformed[index]

    stage_size = 2
    while stage_size <= size:
        phase_step = exp(-2j * pi / stage_size)
        half = stage_size // 2
        for start in range(0, size, stage_size):
            twiddle = 1 + 0j
            for offset in range(half):
                even = transformed[start + offset]
                odd = twiddle * transformed[start + offset + half]
                transformed[start + offset] = even + odd
                transformed[start + offset + half] = even - odd
                twiddle *= phase_step
        stage_size *= 2

    return [abs(transformed[index]) / original_count for index in range(size // 2 + 1)]


def frequency_bins(sample_rate: float, n_fft: int) -> list[float]:
    """Return one-sided frequency labels for an FFT of ``n_fft`` samples."""
    if not isfinite(float(sample_rate)) or float(sample_rate) <= 0:
        raise ValueError("sample_rate must be a positive finite number")
    if not isinstance(n_fft, int) or isinstance(n_fft, bool) or not is_power_of_two(n_fft):
        raise ValueError("n_fft must be a power of two")
    return [index * float(sample_rate) / n_fft for index in range(n_fft // 2 + 1)]
