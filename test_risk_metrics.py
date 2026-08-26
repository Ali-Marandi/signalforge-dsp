from __future__ import annotations

import unittest

import numpy as np

from signalforge_finance import DiagnosticValidationError, LocalRiskEngine, RiskConfig


class LocalRiskEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = RiskConfig(
            confidence_level=0.90,
            min_observations=30,
            simulation_count=5_000,
            random_seed=20260826,
        )
        # Deterministic decimal-return fixture; not market data or investment guidance.
        self.returns = tuple(-index / 100 for index in range(30))

    def test_historical_estimate_matches_observed_loss_tail(self) -> None:
        result = LocalRiskEngine(self.config).historical(self.returns)
        self.assertEqual(result.method, "historical")
        self.assertEqual(result.observations_used, 30)
        self.assertAlmostEqual(result.value_at_risk, 0.27, places=12)
        self.assertAlmostEqual(result.expected_shortfall, 0.28, places=12)
        self.assertGreaterEqual(result.expected_shortfall, result.value_at_risk)
        self.assertEqual(result.quantile_method, "higher_observed_loss")
        self.assertIn("Sample has fewer than 250 observations; tail estimates may be unstable.", result.warning_messages)

    def test_parametric_estimate_is_tail_consistent(self) -> None:
        result = LocalRiskEngine(self.config).normal_parametric(self.returns)
        self.assertEqual(result.method, "normal_parametric")
        self.assertGreater(result.expected_shortfall, result.value_at_risk)
        self.assertEqual(result.quantile_method, "normal_closed_form")
        self.assertIn(
            "Normal distribution assumption selected; compare with historical loss tails before use.",
            result.warning_messages,
        )

    def test_monte_carlo_is_stable_for_same_seed_and_input(self) -> None:
        engine = LocalRiskEngine(self.config)
        first = engine.normal_monte_carlo(self.returns)
        second = engine.normal_monte_carlo(self.returns)
        self.assertEqual(first, second)
        self.assertEqual(first.simulation_count, 5_000)
        self.assertEqual(first.random_seed, 20260826)
        self.assertGreaterEqual(first.expected_shortfall, first.value_at_risk)

    def test_monte_carlo_changes_with_seed_without_changing_source_statistics(self) -> None:
        first = LocalRiskEngine(self.config).normal_monte_carlo(self.returns)
        second_config = RiskConfig(
            confidence_level=0.90,
            min_observations=30,
            simulation_count=5_000,
            random_seed=7,
        )
        second = LocalRiskEngine(second_config).normal_monte_carlo(self.returns)
        self.assertNotEqual(first.value_at_risk, second.value_at_risk)
        self.assertAlmostEqual(first.return_mean, second.return_mean, places=15)
        self.assertAlmostEqual(first.return_std, second.return_std, places=15)

    def test_invalid_inputs_are_blocked(self) -> None:
        engine = LocalRiskEngine(self.config)
        with self.assertRaises(DiagnosticValidationError):
            engine.historical(self.returns[:29])
        with self.assertRaises(DiagnosticValidationError):
            engine.historical(tuple(float("nan") for _ in range(30)))
        with self.assertRaises(DiagnosticValidationError):
            engine.historical(np.zeros((30, 1)))
        with self.assertRaises(DiagnosticValidationError):
            RiskConfig(confidence_level=1.0)
        with self.assertRaises(DiagnosticValidationError):
            RiskConfig(simulation_count=999)
        with self.assertRaises(DiagnosticValidationError):
            RiskConfig(min_observations=30.5)
        with self.assertRaises(DiagnosticValidationError):
            RiskConfig(simulation_count=1_000.0)
        with self.assertRaises(DiagnosticValidationError):
            RiskConfig(confidence_level="0.90")

    def test_normal_methods_block_zero_dispersion(self) -> None:
        constant_returns = tuple(0.01 for _ in range(30))
        engine = LocalRiskEngine(self.config)
        with self.assertRaisesRegex(DiagnosticValidationError, "non-zero return standard deviation"):
            engine.normal_parametric(constant_returns)
        with self.assertRaisesRegex(DiagnosticValidationError, "non-zero return standard deviation"):
            engine.normal_monte_carlo(constant_returns)


if __name__ == "__main__":
    unittest.main()
