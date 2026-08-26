from __future__ import annotations

import unittest

import numpy as np

from signalforge_finance.diagnostics import (
    DiagnosticValidationError,
    GarchConfig,
    GarchVolatilityEngine,
    PcaConfig,
    PcaRegimeEngine,
)


class GarchVolatilityEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(20260826)
        # Deterministic test fixture only; not market data or an investment model.
        self.returns = rng.standard_t(df=7, size=520) * 0.012

    def test_fit_returns_positive_forward_volatility_and_metadata(self) -> None:
        engine = GarchVolatilityEngine(
            GarchConfig(horizon=3, min_observations=500, distribution="student_t")
        )
        result = engine.fit_forecast(self.returns)
        self.assertEqual(result.observations_used, 520)
        self.assertEqual(len(result.forecast_volatility), 3)
        self.assertTrue(all(value > 0 for value in result.forecast_volatility))
        self.assertEqual(result.convergence_flag, 0)
        self.assertIn("alpha[1]", dict(result.parameter_estimates))

    def test_short_series_is_blocked(self) -> None:
        engine = GarchVolatilityEngine(GarchConfig(min_observations=500))
        with self.assertRaises(DiagnosticValidationError):
            engine.fit_forecast(self.returns[:100])


class PcaRegimeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(20260827)
        shared_factor = rng.normal(0.0, 0.01, 150)
        idiosyncratic = rng.normal(0.0, 0.003, (150, 4))
        self.matrix = np.column_stack(
            [
                shared_factor + idiosyncratic[:, 0],
                0.8 * shared_factor + idiosyncratic[:, 1],
                -0.6 * shared_factor + idiosyncratic[:, 2],
                0.4 * shared_factor + idiosyncratic[:, 3],
            ]
        )
        # Create a deterministic out-of-window cross-sectional shift for diagnostics.
        self.matrix[-1] += np.array([0.09, -0.08, 0.07, -0.06])
        self.names = ("A", "B", "C", "D")
        self.timestamps = tuple(f"T{i:03d}" for i in range(self.matrix.shape[0]))

    def test_fit_returns_loadings_and_variance(self) -> None:
        engine = PcaRegimeEngine(PcaConfig(n_components=2, min_observations=100))
        result = engine.fit(self.matrix[:120], self.names)
        self.assertEqual(len(result.components), 2)
        self.assertEqual(len(result.components[0]), 4)
        self.assertEqual(len(result.explained_variance_ratio), 2)
        self.assertGreater(sum(result.explained_variance_ratio), 0.0)
        self.assertGreaterEqual(result.reconstruction_rmse, 0.0)

    def test_fit_scores_are_consistent_with_sign_aligned_components(self) -> None:
        engine = PcaRegimeEngine(PcaConfig(n_components=2, min_observations=100))
        result = engine.fit(self.matrix[:120], self.names)
        raw = self.matrix[:120]
        standardized = (raw - np.asarray(result.scaler_center)) / np.asarray(result.scaler_scale)
        expected_scores = standardized @ np.asarray(result.components).T
        np.testing.assert_allclose(np.asarray(result.component_scores), expected_scores, rtol=1e-10, atol=1e-10)

    def test_regime_detection_has_no_lookahead_output_shape(self) -> None:
        engine = PcaRegimeEngine(
            PcaConfig(n_components=2, min_observations=100, regime_z_threshold=2.0)
        )
        result = engine.detect_regimes(
            self.matrix,
            self.timestamps,
            self.names,
            rolling_window=100,
        )
        self.assertEqual(len(result), 50)
        self.assertEqual(result[0].timestamp, "T100")
        self.assertTrue(result[-1].regime_shift)

    def test_ratio_components_require_full_solver(self) -> None:
        with self.assertRaisesRegex(DiagnosticValidationError, "requires solver='full'"):
            PcaConfig(n_components=0.80, solver="randomized")

    def test_component_count_above_matrix_rank_limit_is_blocked(self) -> None:
        engine = PcaRegimeEngine(PcaConfig(n_components=5, min_observations=100))
        with self.assertRaisesRegex(DiagnosticValidationError, "cannot exceed"):
            engine.fit(self.matrix[:120], self.names)

    def test_non_unique_features_are_blocked(self) -> None:
        engine = PcaRegimeEngine(PcaConfig(n_components=2, min_observations=100))
        with self.assertRaises(DiagnosticValidationError):
            engine.fit(self.matrix[:120], ("A", "A", "C", "D"))


if __name__ == "__main__":
    unittest.main()
