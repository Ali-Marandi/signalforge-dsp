"""Regression tests for the SignalForge Studio desktop application services."""

from __future__ import annotations

import csv
import math
import tempfile
import unittest
from pathlib import Path

from signalforge import dft_magnitudes, fft_magnitudes, frequency_bins, next_power_of_two
from signalforge_studio import __version__
from signalforge_studio.models import ExportBundle
from signalforge_studio.services import analyse_signal, export_csv, export_summary, generate_signal, import_signal


class FastSpectrumTests(unittest.TestCase):
    def test_fft_matches_direct_dft_for_small_signal(self) -> None:
        samples = [0.2, -0.8, 0.5, 0.1, -0.2, 0.4, 0.0, -0.1]
        expected = dft_magnitudes(samples)
        actual = fft_magnitudes(samples)
        self.assertEqual(len(actual), len(expected))
        for actual_value, expected_value in zip(actual, expected):
            self.assertAlmostEqual(actual_value, expected_value, places=10)

    def test_fft_identifies_sine_bin(self) -> None:
        samples = [math.sin(2 * math.pi * 64 * index / 1024) for index in range(1024)]
        spectrum = fft_magnitudes(samples)
        self.assertAlmostEqual(spectrum[64], 0.5, places=10)
        self.assertEqual(max(range(1, len(spectrum)), key=spectrum.__getitem__), 64)

    def test_fft_and_frequency_helpers_validate_inputs(self) -> None:
        self.assertEqual(next_power_of_two(9), 16)
        self.assertEqual(frequency_bins(8000, 8), [0.0, 1000.0, 2000.0, 3000.0, 4000.0])
        with self.assertRaises(ValueError):
            fft_magnitudes([1.0, 2.0], 3)
        with self.assertRaises(ValueError):
            frequency_bins(0, 8)


class StudioServiceTests(unittest.TestCase):
    def test_generated_sine_analysis_exposes_dominant_frequency(self) -> None:
        signal = generate_signal(
            "Sine",
            sample_rate=4096,
            duration_seconds=1.0,
            amplitude=2.0,
            frequency=256.0,
            noise_amount=0.0,
        )
        analysis = analyse_signal(signal, smoothing_window=8)
        self.assertEqual(len(signal.samples), 4096)
        self.assertTrue(analysis.processed)
        self.assertAlmostEqual(analysis.dominant_frequency, 256.0, places=8)
        self.assertGreater(analysis.rms, 0.8)
        self.assertLess(analysis.rms, math.sqrt(2.0))

    def test_import_and_export_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            source = folder / "input.csv"
            source.write_text("time,amplitude\n0,0\n1,1\n2,-1\n", encoding="utf-8")
            signal = import_signal(source, sample_rate=1000)
            self.assertEqual(signal.samples, (0.0, 1.0, -1.0))
            analysis = analyse_signal(signal)
            bundle = ExportBundle(analysis, __version__)
            csv_path = export_csv(bundle, folder / "visible.csv")
            json_path = export_summary(bundle, folder / "summary.json")
            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0], ["time_seconds", "amplitude", "source", "sample_rate_hz"])
            self.assertEqual(len(rows), 4)
            self.assertIn('"application": "SignalForge Studio"', json_path.read_text(encoding="utf-8"))

    def test_rejects_aliasing_and_oversized_smoothing_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "Nyquist"):
            generate_signal(
                "Sine",
                sample_rate=1000,
                duration_seconds=0.5,
                amplitude=1,
                frequency=500,
            )
        signal = generate_signal(
            "Impulse",
            sample_rate=1000,
            duration_seconds=0.01,
            amplitude=1,
            frequency=0,
        )
        with self.assertRaises(ValueError):
            analyse_signal(signal, smoothing_window=100)


if __name__ == "__main__":
    unittest.main()
