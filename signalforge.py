"""Small dependency-free digital signal processing primitives."""

from cmath import exp
from math import pi, sqrt


def rms(samples: list[float]) -> float:
    if not samples:
        raise ValueError("samples cannot be empty")
    return sqrt(sum(x * x for x in samples) / len(samples))


def moving_average(samples: list[float], window: int) -> list[float]:
    if not 1 <= window <= len(samples):
        raise ValueError("window must fit the signal")
    total = sum(samples[:window])
    result = [total / window]
    for index in range(window, len(samples)):
        total += samples[index] - samples[index - window]
        result.append(total / window)
    return result


def dft_magnitudes(samples: list[float]) -> list[float]:
    if not samples:
        raise ValueError("samples cannot be empty")
    n = len(samples)
    return [
        abs(sum(value * exp(-2j * pi * k * index / n) for index, value in enumerate(samples))) / n
        for k in range(n // 2 + 1)
    ]
